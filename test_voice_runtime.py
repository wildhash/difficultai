"""Credential-free checks against the installed, pinned LiveKit SDK."""

import os
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from livekit.agents import AgentSession
from livekit.agents.llm import ChatMessage
from livekit.agents.voice.events import CloseEvent, CloseReason, ConversationItemAddedEvent
from apps.livekit_agent.agent import DifficultAIAgent
from difficultai.observability.opik_tracing import is_opik_enabled


class TestOptionalTracing(unittest.TestCase):
    def test_missing_configuration_does_not_enable_interactive_setup(self):
        with patch.dict(os.environ, {"OPIK_DISABLED": "", "OPIK_API_KEY": "", "OPIK_URL_OVERRIDE": ""}):
            self.assertFalse(is_opik_enabled())

    def test_explicit_disable_overrides_a_configured_destination(self):
        with patch.dict(os.environ, {"OPIK_DISABLED": "1", "OPIK_API_KEY": "fixture", "OPIK_URL_OVERRIDE": ""}):
            self.assertFalse(is_opik_enabled())


class TestVoiceConstruction(unittest.IsolatedAsyncioTestCase):
    async def test_realtime_factory_uses_supported_sdk(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-not-a-real-key", "OPIK_DISABLED": "1"}):
            with patch("apps.livekit_agent.agent.get_tracer", return_value=Mock(enabled=False)):
                worker = DifficultAIAgent(SimpleNamespace())
                session = await worker._create_realtime_assistant()
                self.assertIsInstance(session, AgentSession)
                await session.aclose()
                await session.llm.aclose()

    async def test_pipeline_factory_uses_supported_sdk(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-not-a-real-key", "DEEPGRAM_API_KEY": "", "OPIK_DISABLED": "1"}):
            with patch("apps.livekit_agent.agent.get_tracer", return_value=Mock(enabled=False)):
                worker = DifficultAIAgent(SimpleNamespace())
                session = await worker._create_fallback_assistant()
                self.assertIsInstance(session, AgentSession)
                await session.aclose()
                for provider in (session.stt, session.llm, session.tts):
                    await provider.aclose()


SCENARIO = {
    "persona_type": "ELITE_INTERVIEWER", "company": "Pilot", "role": "Engineer",
    "stakes": "Practice", "user_goal": "Give a concrete answer", "difficulty": 0.5,
}


class TestVoiceLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {
            "OPIK_DISABLED": "1", "VOICE_MODE": "realtime", "SCORECARD_DIR": self.directory.name,
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.tracer = patch("apps.livekit_agent.agent.get_tracer", return_value=Mock(enabled=False))
        self.tracer.start()
        self.addCleanup(self.tracer.stop)

    def make_context(self, metadata=None):
        return SimpleNamespace(
            connect=AsyncMock(),
            job=SimpleNamespace(id="fixture-job", metadata=metadata or json.dumps(SCENARIO)),
            room=SimpleNamespace(
                name="../../same-room", metadata="", local_participant=SimpleNamespace(publish_data=AsyncMock()),
            ),
            wait_for_participant=AsyncMock(return_value=SimpleNamespace(identity="pilot")),
            add_shutdown_callback=Mock(),
            shutdown=Mock(),
        )

    def fake_transport(self, error=None):
        # Use the installed SDK's real event emitter and event types, replacing only I/O.
        session = AgentSession()
        session.start = AsyncMock(side_effect=error)

        async def reply(**kwargs):
            for role, content in [("assistant", "Hello"), ("user", "I will deliver by Friday")]:
                session.emit("conversation_item_added", ConversationItemAddedEvent(
                    item=ChatMessage(role=role, content=[content]),
                ))
            session.emit("close", CloseEvent(reason=CloseReason.PARTICIPANT_DISCONNECTED))

        session.generate_reply = AsyncMock(side_effect=reply)
        return session

    async def test_current_sdk_events_forward_transcripts_and_save_once(self):
        ctx = self.make_context()
        worker = DifficultAIAgent(ctx)
        transport = self.fake_transport()
        with patch.object(worker, "_create_realtime_assistant", AsyncMock(return_value=transport)):
            await worker.entrypoint()
        self.assertEqual([t["role"] for t in worker.session.transcript], ["assistant", "user"])
        payloads = [json.loads(call.args[0]) for call in ctx.room.local_participant.publish_data.call_args_list]
        self.assertEqual([p["text"] for p in payloads], ["Hello", "I will deliver by Friday"])
        self.assertTrue(all(p["type"] == "transcript" for p in payloads))
        options = transport.start.call_args.kwargs
        self.assertEqual(options["room_options"].participant_identity, "pilot")
        self.assertFalse(options["record"])
        ctx.shutdown.assert_called_once()
        files = list(Path(self.directory.name).glob("*.json"))
        self.assertEqual(len(files), 1)
        payload = json.loads(files[0].read_text())
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["room"], "../../same-room")
        self.assertEqual(len(payload["transcript"]), 2)
        original = files[0].read_bytes()
        # Job shutdown can race normal session completion; it must not write twice.
        with patch.object(worker, "_generate_scorecard", AsyncMock()) as save:
            await ctx.add_shutdown_callback.call_args.args[0]()
            save.assert_not_awaited()
        self.assertEqual(files[0].read_bytes(), original)

    async def test_start_failure_is_recorded_as_failed_and_reraised(self):
        ctx = self.make_context()
        worker = DifficultAIAgent(ctx)
        transport = self.fake_transport(RuntimeError("Provider unavailable"))
        with patch.object(worker, "_create_realtime_assistant", AsyncMock(return_value=transport)):
            with self.assertRaisesRegex(RuntimeError, "Provider unavailable"):
                await worker.entrypoint()
        payload = json.loads(next(Path(self.directory.name).glob("*.json")).read_text())
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "Provider unavailable")
        self.assertEqual(payload["transcript"], [])

    async def test_repeated_room_names_do_not_overwrite_sessions(self):
        for _ in range(2):
            worker = DifficultAIAgent(self.make_context())
            with patch.object(worker, "_create_realtime_assistant", AsyncMock(return_value=self.fake_transport())):
                await worker.entrypoint()
        files = list(Path(self.directory.name).glob("*.json"))
        self.assertEqual(len(files), 2)
        self.assertNotEqual(json.loads(files[0].read_text())["session_id"], json.loads(files[1].read_text())["session_id"])
        self.assertFalse(list(Path(self.directory.name).glob("*.tmp")))

    async def test_room_metadata_is_used_when_dispatch_metadata_is_empty(self):
        ctx = self.make_context()
        ctx.job.metadata = ""
        ctx.room.metadata = json.dumps(SCENARIO)
        worker = DifficultAIAgent(ctx)
        await worker._load_scenario_from_metadata()
        self.assertEqual(worker.session.scenario, SCENARIO)
        self.assertFalse(worker.session.collecting_metadata)

    async def test_metadata_completion_updates_live_agent_instructions(self):
        ctx = self.make_context()
        worker = DifficultAIAgent(ctx)
        worker.session.scenario = {k: v for k, v in SCENARIO.items() if k != "user_goal"}
        worker.session.collecting_metadata = True
        worker.session.current_question_field = "user_goal"
        worker._voice_agent = SimpleNamespace(update_instructions=AsyncMock())
        await worker._forward_conversation_item("user", "Give a concrete answer")
        self.assertFalse(worker.session.collecting_metadata)
        instructions = worker._voice_agent.update_instructions.call_args.args[0]
        self.assertIn("ELITE_INTERVIEWER", instructions)
        self.assertIn("Give a concrete answer", instructions)


if __name__ == "__main__":
    unittest.main()

"""Exercise the credentialed owner-session bootstrap without provider I/O."""

import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
import jwt
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from livekit import api

MODULE_PATH = Path(__file__).parent / "apps" / "livekit_agent" / "create_owner_session.py"
SPEC = importlib.util.spec_from_file_location("create_owner_session", MODULE_PATH)
owner_session = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(owner_session)

ENVIRONMENT = {
    "LIVEKIT_URL": "wss://fixture.livekit.cloud",
    "LIVEKIT_API_KEY": "fixture-key",
    "LIVEKIT_API_SECRET": "fixture-secret-that-is-at-least-32-bytes",
}
SCENARIO = {
    "persona_type": "ELITE_INTERVIEWER",
    "company": "TestCorp",
    "role": "Software Engineer",
    "stakes": "Owner acceptance",
    "user_goal": "Verify a configured session",
    "difficulty": 0.6,
}


class TestOwnerSession(unittest.IsolatedAsyncioTestCase):
    async def test_creates_room_metadata_and_scoped_short_lived_token(self):
        room_service = SimpleNamespace(create_room=AsyncMock(
            return_value=SimpleNamespace(
                name="owner-room",
                metadata=json.dumps(SCENARIO, separators=(",", ":"), sort_keys=True),
            ),
        ))
        client = SimpleNamespace(room=room_service)
        manager = Mock(__aenter__=AsyncMock(return_value=client),
                       __aexit__=AsyncMock(return_value=False))
        with patch.object(api, "LiveKitAPI", return_value=manager):
            result = await owner_session.create_session(
                scenario=SCENARIO,
                room_name="owner-room",
                identity="owner-user",
                ttl_minutes=30,
                environ=ENVIRONMENT,
            )

        manager.__aexit__.assert_awaited_once()
        request = room_service.create_room.await_args.args[0]
        self.assertEqual(request.name, "owner-room")
        self.assertEqual(json.loads(request.metadata), SCENARIO)
        claims = api.TokenVerifier(
            "fixture-key", "fixture-secret-that-is-at-least-32-bytes"
        ).verify(result["access_token"])
        self.assertEqual(claims.identity, "owner-user")
        self.assertEqual(claims.video.room, "owner-room")
        self.assertTrue(claims.video.room_join)
        raw_claims = jwt.decode(
            result["access_token"],
            "fixture-secret-that-is-at-least-32-bytes",
            algorithms=["HS256"],
        )
        self.assertLessEqual(raw_claims["exp"] - raw_claims["nbf"], 30 * 60)

    async def test_invalid_configuration_stops_before_provider_io(self):
        with patch.object(api, "LiveKitAPI") as livekit:
            with self.assertRaisesRegex(ValueError, "LIVEKIT_API_SECRET"):
                await owner_session.create_session(
                    scenario=SCENARIO,
                    room_name="owner-room",
                    identity="owner-user",
                    ttl_minutes=30,
                    environ={"LIVEKIT_URL": "https://wrong", "LIVEKIT_API_KEY": "key"},
                )
        livekit.assert_not_called()

    async def test_rejects_remote_plaintext_transport(self):
        with patch.object(api, "LiveKitAPI") as livekit:
            with self.assertRaisesRegex(ValueError, "LIVEKIT_URL"):
                await owner_session.create_session(
                    scenario=SCENARIO,
                    room_name="owner-room",
                    identity="owner-user",
                    ttl_minutes=30,
                    environ={**ENVIRONMENT, "LIVEKIT_URL": "ws://remote.example"},
                )
        livekit.assert_not_called()

    async def test_token_failure_does_not_create_room(self):
        with patch.object(api, "AccessToken", side_effect=RuntimeError("local failure")):
            with patch.object(api, "LiveKitAPI") as livekit:
                with self.assertRaisesRegex(RuntimeError, "local failure"):
                    await owner_session.create_session(
                        scenario=SCENARIO,
                        room_name="owner-room",
                        identity="owner-user",
                        ttl_minutes=30,
                        environ=ENVIRONMENT,
                    )
        livekit.assert_not_called()

    async def test_rejects_reused_room_with_different_metadata(self):
        room_service = SimpleNamespace(create_room=AsyncMock(
            return_value=SimpleNamespace(name="owner-room", metadata='{"company":"Old"}'),
        ))
        manager = Mock(
            __aenter__=AsyncMock(return_value=SimpleNamespace(room=room_service)),
            __aexit__=AsyncMock(return_value=False),
        )
        with patch.object(api, "LiveKitAPI", return_value=manager):
            with self.assertRaisesRegex(ValueError, "different metadata"):
                await owner_session.create_session(
                    scenario=SCENARIO,
                    room_name="owner-room",
                    identity="owner-user",
                    ttl_minutes=30,
                    environ=ENVIRONMENT,
                )
        manager.__aexit__.assert_awaited_once()

    async def test_room_creation_timeout_cancels_provider_context(self):
        async def never_returns(_request):
            await asyncio.Event().wait()

        room_service = SimpleNamespace(
            create_room=AsyncMock(side_effect=never_returns)
        )
        manager = Mock(
            __aenter__=AsyncMock(
                return_value=SimpleNamespace(room=room_service)
            ),
            __aexit__=AsyncMock(return_value=False),
        )
        with patch.object(api, "LiveKitAPI", return_value=manager):
            with patch.object(owner_session, "SESSION_BOOTSTRAP_TIMEOUT_SECONDS", 0.01):
                with self.assertRaisesRegex(ValueError, "Session bootstrap timed out"):
                    await owner_session.create_session(
                        scenario=SCENARIO,
                        room_name="owner-room",
                        identity="owner-user",
                        ttl_minutes=30,
                        environ=ENVIRONMENT,
                    )

        manager.__aexit__.assert_awaited_once()
        room_service.create_room.assert_awaited_once()

    async def test_rejects_unsafe_names_and_long_tokens(self):
        for room, identity, ttl in (("../room", "owner", 30), ("room", "owner/name", 30), ("room", "owner", 121)):
            with self.subTest(room=room, identity=identity, ttl=ttl):
                with self.assertRaises(ValueError):
                    await owner_session.create_session(
                        scenario=SCENARIO,
                        room_name=room,
                        identity=identity,
                        ttl_minutes=ttl,
                        environ=ENVIRONMENT,
                    )

    def test_load_scenario_rejects_non_object_or_incomplete_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                owner_session.load_scenario(path)
            path.write_text('{"company":"TestCorp"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "failed validation"):
                owner_session.load_scenario(path)


class TestOwnerSessionCLI(unittest.TestCase):
    def test_project_env_is_loaded_without_exporting_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "scenario.json"
            path.write_text(json.dumps(SCENARIO), encoding="utf-8")
            (root / ".env").write_text(
                "LIVEKIT_URL=wss://file.livekit.cloud\n"
                "LIVEKIT_API_KEY=file-key\n"
                "LIVEKIT_API_SECRET=file-secret\n",
                encoding="utf-8",
            )
            created = {
                "schema_version": 1,
                "livekit_url": "wss://file.livekit.cloud",
                "room_name": "owner-room",
                "participant_identity": "owner-user",
                "access_token": "short-lived-token",
                "expires_in_minutes": 30,
                "next_action": "start",
                "sensitive": "do not share",
            }
            with patch.object(
                owner_session, "create_session", new=AsyncMock(return_value=created)
            ) as create:
                output = io.StringIO()
                with redirect_stdout(output):
                    code = owner_session.main(
                        ["--scenario-file", str(path)], root=root, environ={}
                    )

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "created")
        configured = create.await_args.kwargs["environ"]
        self.assertEqual(configured["LIVEKIT_URL"], "wss://file.livekit.cloud")
        self.assertEqual(configured["LIVEKIT_API_KEY"], "file-key")
        self.assertEqual(configured["LIVEKIT_API_SECRET"], "file-secret")

    def test_exported_configuration_overrides_project_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "LIVEKIT_URL=wss://file.livekit.cloud\nLIVEKIT_API_KEY=file-key\n",
                encoding="utf-8",
            )
            configured = owner_session.load_configuration(
                root,
                {
                    "LIVEKIT_URL": "wss://exported.livekit.cloud",
                    "LIVEKIT_API_KEY": "exported-key",
                },
            )
        self.assertEqual(configured["LIVEKIT_URL"], "wss://exported.livekit.cloud")
        self.assertEqual(configured["LIVEKIT_API_KEY"], "exported-key")

    def test_provider_failure_does_not_print_credentials_or_provider_detail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            path.write_text(json.dumps(SCENARIO), encoding="utf-8")
            output = io.StringIO()
            with patch.dict("os.environ", ENVIRONMENT, clear=True):
                with patch.object(
                    owner_session,
                    "create_session",
                    new=AsyncMock(side_effect=RuntimeError("fixture-secret private-url")),
                ):
                    with redirect_stdout(output):
                        code = owner_session.main(["--scenario-file", str(path)])
        self.assertEqual(code, 1)
        self.assertNotIn("fixture-secret", output.getvalue())
        self.assertNotIn("private-url", output.getvalue())
        self.assertIn("RuntimeError", output.getvalue())


if __name__ == "__main__":
    unittest.main()

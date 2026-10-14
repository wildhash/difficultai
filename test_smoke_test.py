"""Exercise the preflight's SDK contract, failure handling, and evidence boundary."""

import asyncio
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from apps.livekit_agent import smoke_test

ENVIRONMENT = {
    "LIVEKIT_URL": "wss://fixture.livekit.cloud",
    "LIVEKIT_API_KEY": "fixture-key",
    "LIVEKIT_API_SECRET": "fixture-secret",
    "OPENAI_API_KEY": "fixture-openai-key",
    "PYTHON_DOTENV_DISABLED": "1",
}


class TestPreflight(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {
            **ENVIRONMENT, "SCORECARD_DIR": self.directory.name,
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    async def test_real_sdk_client_uses_awaited_room_call_and_closes(self):
        from livekit import api
        from livekit.api.room_service import RoomService

        # Retain the installed SDK's constructor/context manager and replace only I/O.
        clients = []
        original_client = api.LiveKitAPI

        def capture(*args, **kwargs):
            client = original_client(*args, **kwargs)
            clients.append(client)
            return client

        with patch.object(api, "LiveKitAPI", side_effect=capture):
            with patch.object(RoomService, "list_rooms", new_callable=AsyncMock) as listing:
                await smoke_test.check_livekit(os.environ)
                listing.assert_awaited_once()
                self.assertIsInstance(listing.call_args.args[0], api.ListRoomsRequest)
        self.assertEqual(len(clients), 1)
        self.assertTrue(clients[0]._session.closed)

    async def test_failed_request_closes_client_and_does_not_leak_provider_detail(self):
        from livekit import api
        client = SimpleNamespace(room=SimpleNamespace(list_rooms=AsyncMock(
            side_effect=RuntimeError("fixture-secret fixture-openai-key"),
        )))
        manager = Mock(__aenter__=AsyncMock(return_value=client), __aexit__=AsyncMock(return_value=False))
        with patch.object(api, "LiveKitAPI", return_value=manager):
            report = await smoke_test.run_checks()
        manager.__aexit__.assert_awaited_once()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "livekit_connectivity")
        self.assertNotIn("fixture-secret", json.dumps(report))
        self.assertNotIn("fixture-openai-key", json.dumps(report))
        self.assertIn("LiveKit credentials", report["next_action"])

    async def test_timeout_cancels_request_and_closes_client(self):
        from livekit import api
        cancelled = asyncio.Event()

        async def hang(_):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        client = SimpleNamespace(room=SimpleNamespace(list_rooms=AsyncMock(side_effect=hang)))
        manager = Mock(__aenter__=AsyncMock(return_value=client), __aexit__=AsyncMock(return_value=False))
        with patch.object(api, "LiveKitAPI", return_value=manager):
            with self.assertRaises(asyncio.TimeoutError):
                await smoke_test.check_livekit(os.environ, timeout=0.01)
        self.assertTrue(cancelled.is_set())
        manager.__aexit__.assert_awaited_once()

    async def test_example_credentials_fail_before_service_io(self):
        with patch.dict(os.environ, {
            "LIVEKIT_URL": "wss://your-livekit-server.com",
            "LIVEKIT_API_KEY": "your_livekit_api_key",
            "LIVEKIT_API_SECRET": "your_livekit_api_secret",
            "OPENAI_API_KEY": "your_api_key_here",
        }):
            with patch.object(smoke_test, "check_livekit", new_callable=AsyncMock) as connect:
                report = await smoke_test.run_checks()
                connect.assert_not_awaited()
        self.assertEqual(report["status"], "failed")
        config = next(c for c in report["checks"] if c["name"] == "configuration")
        for variable in smoke_test.REQUIRED_VARS:
            self.assertIn(variable, config["detail"])

    async def test_offline_checks_need_no_credentials_and_preserve_acceptance_boundary(self):
        with patch.dict(os.environ, {"SCORECARD_DIR": self.directory.name}, clear=True):
            with patch.object(smoke_test, "check_livekit", new_callable=AsyncMock) as connect:
                report = await smoke_test.run_checks(offline=True)
                connect.assert_not_awaited()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["mode"], "offline")
        self.assertEqual(report["checks"][-1]["status"], "not_run")
        self.assertIn("Web deployment and owner acceptance", report["not_verified"])
        self.assertFalse(list(Path(self.directory.name).iterdir()))

    async def test_connectivity_success_does_not_claim_voice_acceptance(self):
        with patch.object(smoke_test, "check_livekit", new_callable=AsyncMock) as connect:
            report = await smoke_test.run_checks()
            connect.assert_awaited_once()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["mode"], "connectivity")
        self.assertIn("OpenAI provider access", report["not_verified"])
        self.assertIn("owner voice session", report["next_action"])

    async def test_storage_failure_is_not_hidden_by_connectivity_success(self):
        with patch.object(smoke_test, "check_storage", side_effect=PermissionError("private-path")):
            with patch.object(smoke_test, "check_livekit", new_callable=AsyncMock):
                report = await smoke_test.run_checks()
        self.assertEqual(report["status"], "failed")
        self.assertIn("SCORECARD_DIR", report["next_action"])
        self.assertNotIn("private-path", json.dumps(report))

    async def test_each_run_retains_a_distinct_readable_report(self):
        directory = Path(self.directory.name)
        reports = [await smoke_test.run_checks(offline=True) for _ in range(2)]
        paths = [smoke_test.save_report(report, directory) for report in reports]
        self.assertNotEqual(paths[0], paths[1])
        for path, report in zip(paths, reports):
            self.assertEqual(json.loads(path.read_text()), report)
        self.assertFalse(list(directory.glob("*.tmp")))


class TestPreflightCLI(unittest.TestCase):
    def test_invalid_urls_are_rejected_without_echoing_secrets(self):
        for url in ("https://fixture.livekit.cloud", "wss://", "wss://key:secret@host", "wss://host?token=secret"):
            with self.subTest(url=url):
                self.assertEqual(smoke_test.environment_issues({**ENVIRONMENT, "LIVEKIT_URL": url}), ["LIVEKIT_URL"])

    def test_report_failure_returns_nonzero_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"SCORECARD_DIR": directory, "PYTHON_DOTENV_DISABLED": "1"}, clear=True):
                with patch.object(smoke_test, "save_report", side_effect=PermissionError("private-path")):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        code = smoke_test.main(["--offline"])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "report_storage")
        self.assertNotIn("private-path", output.getvalue())

    def test_missing_credentials_exit_nonzero_and_retain_diagnosis(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"SCORECARD_DIR": directory, "PYTHON_DOTENV_DISABLED": "1"}, clear=True):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = smoke_test.main([])
            self.assertEqual(code, 1)
            report = json.loads(output.getvalue())
            saved = next((Path(directory) / "preflight").glob("preflight_*.json"))
            self.assertEqual(json.loads(saved.read_text()), report)

    @unittest.skipUnless(shutil.which("make"), "make is unavailable")
    def test_clean_preserves_session_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "scorecard_owner-session.json"
            evidence.write_text('{"status": "completed"}')
            result = subprocess.run(
                ["make", "-f", str(Path(__file__).parent / "Makefile"), "clean"],
                cwd=root, capture_output=True, text=True, check=True,
            )
            self.assertEqual(evidence.read_text(), '{"status": "completed"}', result.stdout)


if __name__ == "__main__":
    unittest.main()

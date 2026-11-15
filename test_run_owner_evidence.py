"""Regression coverage for bounded isolated evidence commands."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock


MODULE_PATH = Path(__file__).parent / "apps" / "livekit_agent" / "run_owner_evidence.py"
SPEC = importlib.util.spec_from_file_location("run_owner_evidence", MODULE_PATH)
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class OwnerEvidenceRunnerTests(unittest.TestCase):
    def test_runs_allowed_module_in_isolated_service_with_deadline(self):
        runner = Mock(return_value=SimpleNamespace(
            returncode=0, stdout='{"status":"incomplete"}\n', stderr=""
        ))
        with tempfile.TemporaryDirectory() as directory:
            result = evidence.run_evidence(
                "owner_pilot_status", ["--latest"],
                root=Path(directory), runner=runner,
            )
        self.assertEqual(result.returncode, 0)
        command = runner.call_args.args[0]
        self.assertEqual(command[:6], [
            "docker", "compose", "--env-file", "/dev/null",
            "--file", "compose.owner-evidence.yml",
        ])
        self.assertIn("--no-deps", command)
        self.assertIn("evidence", command)
        self.assertEqual(command[-4:], [
            "python", "-m", "apps.livekit_agent.owner_pilot_status", "--latest"
        ])
        self.assertEqual(
            runner.call_args.kwargs["timeout"], evidence.COMMAND_TIMEOUT_SECONDS
        )

    def test_timeout_is_sanitized(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(
            ["docker", "private-detail"], 1, stderr="secret"
        ))
        output = io.StringIO()
        with redirect_stderr(output):
            code = evidence.main(["owner_pilot_status", "--latest"], runner=runner)
        self.assertEqual(code, 1)
        self.assertIn("timed out", output.getvalue())
        self.assertNotIn("private-detail", output.getvalue())
        self.assertNotIn("secret", output.getvalue())

    def test_failed_module_preserves_only_its_sanitized_stdout(self):
        runner = Mock(return_value=SimpleNamespace(
            returncode=1,
            stdout='{"status":"blocked","next_action":"retry"}\n',
            stderr="private docker detail",
        ))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = evidence.main(["verify_scorecard", "a" * 32], runner=runner)
        self.assertEqual(code, 1)
        self.assertIn('"status":"blocked"', stdout.getvalue())
        self.assertNotIn("private docker detail", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

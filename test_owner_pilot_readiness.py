"""Regression tests for the read-only owner-pilot readiness gate."""

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from apps.livekit_agent.check_owner_pilot_readiness import check_readiness


REVISION = "1" * 40
CONFIGURATION = """\
LIVEKIT_URL=wss://fixture.livekit.cloud
LIVEKIT_API_KEY=fixture-key
LIVEKIT_API_SECRET=fixture-secret
OPENAI_API_KEY=fixture-openai
"""


class RecordingRunner:
    def __init__(self, *, docker=True, compose=True):
        self.docker = docker
        self.compose = compose
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        if command[:2] == ["docker", "compose"] and command[-1] == "version":
            success = self.docker
        elif command[:2] == ["docker", "info"]:
            success = self.docker
        else:
            success = self.compose
        return SimpleNamespace(returncode=0 if success else 1, stdout="private", stderr="private")


class RecordingGit:
    def __init__(self, *, dirty=False):
        self.dirty = dirty

    def __call__(self, command, **kwargs):
        stdout = REVISION + "\n" if "rev-parse" in command else (" M private.py\n" if self.dirty else "")
        return SimpleNamespace(returncode=0, stdout=stdout)


class OwnerPilotReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def configure(self, contents=CONFIGURATION):
        (self.root / ".env").write_text(contents, encoding="utf-8")

    def test_reports_all_host_blockers_without_starting_or_building(self):
        runner = RecordingRunner(docker=False)
        report = check_readiness(
            root=self.root, runner=runner, git_runner=RecordingGit(), environ={},
        )
        self.assertFalse(report["ready"])
        self.assertEqual(report["checks"][1]["detail"], "Missing or invalid: .env")
        self.assertEqual(report["checks"][2]["status"], "failed")
        commands = [call[0] for call in runner.calls]
        self.assertTrue(all("build" not in command and "up" not in command for command in commands))
        self.assertEqual(report["checks"][3]["status"], "not_run")

    def test_lists_only_missing_names_and_never_values(self):
        self.configure(CONFIGURATION.replace("OPENAI_API_KEY=fixture-openai\n", ""))
        report = check_readiness(
            root=self.root, runner=RecordingRunner(), git_runner=RecordingGit(), environ={},
        )
        rendered = str(report)
        self.assertIn("OPENAI_API_KEY", rendered)
        for private in ("fixture-key", "fixture-secret"):
            self.assertNotIn(private, rendered)

    def test_dirty_checkout_blocks_compose_validation(self):
        self.configure()
        runner = RecordingRunner()
        report = check_readiness(
            root=self.root, runner=runner, git_runner=RecordingGit(dirty=True), environ={},
        )
        self.assertFalse(report["ready"])
        self.assertEqual(report["checks"][0]["status"], "failed")
        self.assertEqual(report["checks"][3]["status"], "not_run")

    def test_ready_requires_clean_source_credentials_docker_and_compose(self):
        self.configure()
        runner = RecordingRunner()
        report = check_readiness(
            root=self.root, runner=runner, git_runner=RecordingGit(), environ={},
        )
        self.assertTrue(report["ready"])
        self.assertTrue(all(item["status"] == "passed" for item in report["checks"]))
        self.assertEqual(report["next_action"], "Run make owner-pilot-deploy.")
        self.assertIn("Worker image build or deployment", report["not_verified"])

    def test_invalid_compose_is_a_specific_terminal_blocker(self):
        self.configure()
        report = check_readiness(
            root=self.root, runner=RecordingRunner(compose=False),
            git_runner=RecordingGit(), environ={},
        )
        self.assertFalse(report["ready"])
        self.assertEqual(report["checks"][-1]["status"], "failed")
        self.assertIn("Compose", report["next_action"])


if __name__ == "__main__":
    unittest.main()

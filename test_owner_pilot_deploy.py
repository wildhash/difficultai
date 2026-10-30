"""Regression tests for the fail-closed owner-pilot deployment gate."""

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from apps.livekit_agent.deploy_owner_pilot import COMPOSE, DeploymentError, deploy


REVISION = "1" * 40


class RecordingRunner:
    def __init__(self, *, fail_marker=None, status="worker\n"):
        self.calls = []
        self.fail_marker = fail_marker
        self.status = status

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        failed = self.fail_marker and any(self.fail_marker in part for part in command)
        stdout = self.status if command[-4:] == ["ps", "--status", "running", "--services"] else ""
        return SimpleNamespace(returncode=1 if failed else 0, stdout=stdout)


class RecordingGit:
    def __init__(self, *, revision=REVISION, dirty=False, error=False):
        self.revision = revision
        self.dirty = dirty
        self.error = error
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        if self.error:
            raise FileNotFoundError("private host path")
        stdout = self.revision + "\n" if "rev-parse" in command else (" M private.py\n" if self.dirty else "")
        return SimpleNamespace(returncode=0, stdout=stdout)


class OwnerPilotDeployTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def configure(self):
        (self.root / ".env").write_text("private values stay local\n", encoding="utf-8")

    def test_missing_env_stops_before_docker(self):
        runner = RecordingRunner()
        with self.assertRaisesRegex(DeploymentError, "credentials"):
            deploy(root=self.root, runner=runner, git_runner=RecordingGit())
        self.assertEqual(runner.calls, [])

    def test_connectivity_failure_never_starts_worker(self):
        self.configure()
        runner = RecordingRunner(fail_marker="apps.livekit_agent.smoke_test")
        with self.assertRaisesRegex(DeploymentError, "connectivity"):
            deploy(root=self.root, runner=runner, git_runner=RecordingGit())
        arguments = [call[0][len(COMPOSE):] for call in runner.calls]
        self.assertNotIn(("up", "-d", "--no-build", "worker"), arguments)

    def test_success_orders_gate_before_start_and_checks_status(self):
        self.configure()
        runner = RecordingRunner()
        deploy(root=self.root, runner=runner, git_runner=RecordingGit())
        arguments = [call[0][len(COMPOSE):] for call in runner.calls]
        self.assertEqual(arguments, [
            ("config", "--quiet"),
            ("build", "worker"),
            ("run", "--rm", "--no-deps", "worker", "python", "-m",
             "apps.livekit_agent.smoke_test"),
            ("up", "-d", "--no-build", "worker"),
            ("ps", "--status", "running", "--services"),
            ("exec", "-T", "worker", "python", "-c",
             "import os,sys; sys.exit(os.getenv('DIFFICULTAI_BUILD_SHA') != sys.argv[1])",
             REVISION),
        ])
        self.assertTrue(all(call[1]["env"]["DIFFICULTAI_BUILD_SHA"] == REVISION for call in runner.calls))

    def test_dirty_checkout_stops_before_docker(self):
        self.configure()
        runner = RecordingRunner()
        with self.assertRaisesRegex(DeploymentError, "uncommitted"):
            deploy(root=self.root, runner=runner, git_runner=RecordingGit(dirty=True))
        self.assertEqual(runner.calls, [])

    def test_missing_git_is_reported_without_raw_host_error(self):
        self.configure()
        runner = RecordingRunner()
        with self.assertRaisesRegex(DeploymentError, "source revision") as caught:
            deploy(root=self.root, runner=runner, git_runner=RecordingGit(error=True))
        self.assertNotIn("private host path", str(caught.exception))
        self.assertEqual(runner.calls, [])

    def test_revision_mismatch_stops_worker_with_specific_diagnosis(self):
        self.configure()
        runner = RecordingRunner(fail_marker="import os,sys")
        with self.assertRaisesRegex(DeploymentError, "revision did not match"):
            deploy(root=self.root, runner=runner, git_runner=RecordingGit())
        self.assertEqual(runner.calls[-1][0], (*COMPOSE, "stop", "worker"))

    def test_non_running_worker_is_stopped_without_volume_removal(self):
        self.configure()
        runner = RecordingRunner(status="")
        with self.assertRaisesRegex(DeploymentError, "scorecard storage was preserved"):
            deploy(root=self.root, runner=runner, git_runner=RecordingGit())
        commands = [call[0] for call in runner.calls]
        self.assertEqual(commands[-1], (*COMPOSE, "stop", "worker"))
        self.assertTrue(all("down" not in command and "--volumes" not in command for command in commands))

    def test_uncertain_start_is_stopped_without_volume_removal(self):
        self.configure()
        runner = RecordingRunner(fail_marker="up")
        with self.assertRaisesRegex(DeploymentError, "scorecard storage was preserved"):
            deploy(root=self.root, runner=runner, git_runner=RecordingGit())
        commands = [call[0] for call in runner.calls]
        self.assertEqual(commands[-1], (*COMPOSE, "stop", "worker"))
        self.assertTrue(all("down" not in command and "--volumes" not in command for command in commands))


if __name__ == "__main__":
    unittest.main()

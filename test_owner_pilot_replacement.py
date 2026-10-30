"""Regression tests for privacy-safe owner-pilot replacement verification."""

from types import SimpleNamespace
import unittest

from apps.livekit_agent.replace_owner_pilot import COMPOSE, ReplacementError, replace_and_verify


SESSION_ID = "a" * 32
DIGEST_A = "1" * 64
DIGEST_B = "2" * 64


class QueueRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        return self.results.pop(0)


def result(returncode=0, stdout=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout)


def success_results(after=DIGEST_A):
    return [
        result(stdout="worker\n"), result(), result(stdout=DIGEST_A + "\n"),
        result(), result(stdout="worker\n"), result(), result(stdout=after + "\n"),
    ]


class OwnerPilotReplacementTests(unittest.TestCase):
    def test_invalid_session_id_stops_before_docker(self):
        runner = QueueRunner([])
        with self.assertRaisesRegex(ReplacementError, "session ID"):
            replace_and_verify("../private", runner=runner)
        self.assertEqual(runner.calls, [])

    def test_failed_precheck_never_replaces_worker(self):
        runner = QueueRunner([result(stdout="worker\n"), result(returncode=1)])
        with self.assertRaisesRegex(ReplacementError, "Pre-replacement"):
            replace_and_verify(SESSION_ID, runner=runner)
        self.assertFalse(any("--force-recreate" in call[0] for call in runner.calls))

    def test_replaces_once_and_verifies_same_private_file(self):
        runner = QueueRunner(success_results())
        replace_and_verify(SESSION_ID, runner=runner)
        commands = [call[0][len(COMPOSE):] for call in runner.calls]
        self.assertEqual(commands[3],
                         ("up", "-d", "--no-deps", "--no-build", "--force-recreate", "worker"))
        self.assertEqual(sum("--force-recreate" in command for command in commands), 1)
        self.assertEqual(sum("apps.livekit_agent.verify_scorecard" in command for command in commands), 2)
        self.assertTrue(all("--volumes" not in command and "down" not in command for command in commands))

    def test_changed_private_file_fails_without_printing_digest(self):
        runner = QueueRunner(success_results(after=DIGEST_B))
        with self.assertRaisesRegex(ReplacementError, "changed across") as caught:
            replace_and_verify(SESSION_ID, runner=runner)
        message = str(caught.exception)
        self.assertNotIn(DIGEST_A, message)
        self.assertNotIn(DIGEST_B, message)

    def test_post_replacement_worker_must_be_running(self):
        responses = success_results()
        responses[4] = result(stdout="")
        runner = QueueRunner(responses[:5])
        with self.assertRaisesRegex(ReplacementError, "not running"):
            replace_and_verify(SESSION_ID, runner=runner)


if __name__ == "__main__":
    unittest.main()

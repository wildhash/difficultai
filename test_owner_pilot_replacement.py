"""Regression tests for privacy-safe owner-pilot replacement verification."""

from types import SimpleNamespace
import subprocess
import unittest

from apps.livekit_agent.replace_owner_pilot import COMPOSE, ReplacementError, replace_and_verify


SESSION_ID = "a" * 32
DIGEST_A = "1" * 64
DIGEST_B = "2" * 64
REVISION_A = "a" * 40
REVISION_B = "b" * 40


class QueueRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        return self.results.pop(0)


class TimeoutRunner:
    def __call__(self, command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))


def result(returncode=0, stdout=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout)


def verification(revision=REVISION_A):
    return '{"status":"passed","source_revision":"' + revision + '"}\n'


def success_results(after=DIGEST_A, post_revision=REVISION_A):
    return [
        result(stdout="worker\n"), result(stdout=verification()), result(stdout=REVISION_A + "\n"),
        result(stdout=DIGEST_A + "\n"), result(), result(stdout="worker\n"),
        result(stdout=verification()), result(stdout=post_revision + "\n"),
        result(stdout=after + "\n"),
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

    def test_malformed_verification_output_fails_safely_before_replacement(self):
        runner = QueueRunner([result(stdout="worker\n"), result(stdout="private malformed output")])
        with self.assertRaisesRegex(ReplacementError, "verification output was invalid") as caught:
            replace_and_verify(SESSION_ID, runner=runner)
        self.assertNotIn("private malformed output", str(caught.exception))
        self.assertFalse(any("--force-recreate" in call[0] for call in runner.calls))

    def test_sanitized_json_can_be_extracted_from_wrapper_output(self):
        responses = success_results()
        responses[1].stdout = "diagnostic without private content\n" + verification() + "done\n"
        runner = QueueRunner(responses)
        replace_and_verify(SESSION_ID, runner=runner, sleeper=lambda _: None)

    def test_missing_worker_revision_output_is_sanitized(self):
        runner = QueueRunner([
            result(stdout="worker\n"), result(stdout=verification()), result(stdout=None),
        ])
        with self.assertRaisesRegex(ReplacementError, "revision did not match"):
            replace_and_verify(SESSION_ID, runner=runner)

    def test_missing_scorecard_revision_fails_before_replacement(self):
        runner = QueueRunner([
            result(stdout="worker\n"),
            result(stdout='{"status":"passed","source_revision":null}\n'),
        ])
        with self.assertRaisesRegex(ReplacementError, "source revision was invalid"):
            replace_and_verify(SESSION_ID, runner=runner)
        self.assertFalse(any("--force-recreate" in call[0] for call in runner.calls))

    def test_replaces_once_and_verifies_same_private_file(self):
        runner = QueueRunner(success_results())
        replace_and_verify(SESSION_ID, runner=runner, sleeper=lambda _: None)
        commands = [call[0][len(COMPOSE):] for call in runner.calls]
        self.assertEqual(commands[4],
                         ("up", "-d", "--no-deps", "--no-build", "--force-recreate", "worker"))
        self.assertEqual(sum("--force-recreate" in command for command in commands), 1)
        self.assertEqual(sum("apps.livekit_agent.verify_scorecard" in command for command in commands), 2)
        self.assertEqual(sum("DIFFICULTAI_BUILD_SHA" in " ".join(command) for command in commands), 2)
        self.assertTrue(all("--volumes" not in command and "down" not in command for command in commands))

    def test_pre_replacement_worker_must_match_scorecard_revision(self):
        responses = [
            result(stdout="worker\n"), result(stdout=verification()),
            result(stdout=REVISION_B + "\n"),
        ]
        runner = QueueRunner(responses)
        with self.assertRaisesRegex(ReplacementError, "revision did not match") as caught:
            replace_and_verify(SESSION_ID, runner=runner, sleeper=lambda _: None)
        self.assertNotIn(REVISION_A, str(caught.exception))
        self.assertNotIn(REVISION_B, str(caught.exception))
        self.assertFalse(any("--force-recreate" in call[0] for call in runner.calls))

    def test_post_replacement_worker_must_match_scorecard_revision(self):
        runner = QueueRunner(success_results(post_revision=REVISION_B))
        with self.assertRaisesRegex(ReplacementError, "revision did not match") as caught:
            replace_and_verify(SESSION_ID, runner=runner, sleeper=lambda _: None)
        self.assertNotIn(REVISION_A, str(caught.exception))
        self.assertNotIn(REVISION_B, str(caught.exception))

    def test_changed_private_file_fails_without_printing_digest(self):
        runner = QueueRunner(success_results(after=DIGEST_B))
        with self.assertRaisesRegex(ReplacementError, "changed across") as caught:
            replace_and_verify(SESSION_ID, runner=runner, sleeper=lambda _: None)
        message = str(caught.exception)
        self.assertNotIn(DIGEST_A, message)
        self.assertNotIn(DIGEST_B, message)

    def test_post_replacement_worker_must_be_running(self):
        responses = success_results()[:5] + [result(stdout="")] * 5
        runner = QueueRunner(responses)
        with self.assertRaisesRegex(ReplacementError, "bounded retry"):
            replace_and_verify(SESSION_ID, runner=runner, sleeper=lambda _: None)

    def test_compose_timeout_is_sanitized_and_bounded(self):
        with self.assertRaisesRegex(ReplacementError, "timed out") as caught:
            replace_and_verify(SESSION_ID, runner=TimeoutRunner(), sleeper=lambda _: None)
        self.assertNotIn("docker", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

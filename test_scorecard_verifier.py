"""Regression coverage for privacy-safe retained scorecard verification."""

import io
import importlib.util
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from difficultai.scorecard import SCORECARD_DIMENSIONS

MODULE_PATH = Path(__file__).parent / "apps" / "livekit_agent" / "verify_scorecard.py"
SPEC = importlib.util.spec_from_file_location("verify_scorecard", MODULE_PATH)
verify_scorecard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_scorecard)


class TestScorecardVerifier(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.session_id = "a" * 32
        self.payload = {
            "session_id": self.session_id,
            "room": "private-room",
            "job_id": "private-job",
            "status": "completed",
            "error": None,
            "scenario": {"company": "Private Company"},
            "transcript": [
                {"role": "assistant", "content": "Private question", "timestamp": 1.0},
                {"role": "user", "content": "Private answer", "timestamp": 2.0},
            ],
            "evaluation": {
                "scores": {name: 7 for name in SCORECARD_DIMENSIONS},
                "feedback": {"coaching_points": ["one", "two", "three"]},
            },
        }

    def write(self, payload=None):
        path = self.directory / f"scorecard_{self.session_id}.json"
        path.write_text(json.dumps(payload or self.payload), encoding="utf-8")

    def test_valid_retained_scorecard_passes_without_private_content(self):
        self.write()
        report = verify_scorecard.verify_scorecard(self.directory, self.session_id)
        serialized = json.dumps(report)
        self.assertEqual(report["status"], "passed")
        for private in ("private-room", "private-job", "Private Company", "Private question", "Private answer"):
            self.assertNotIn(private, serialized)

    def test_missing_scorecard_fails_safely(self):
        report = verify_scorecard.verify_scorecard(self.directory, self.session_id)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "scorecard_file")
        self.assertNotIn(str(self.directory), json.dumps(report))

    def test_one_way_or_failed_session_is_not_accepted(self):
        self.payload["status"] = "failed"
        self.payload["error"] = "private provider detail"
        self.payload["transcript"] = [{"role": "assistant", "content": "Only one side"}]
        self.write()
        report = verify_scorecard.verify_scorecard(self.directory, self.session_id)
        self.assertEqual(report["status"], "failed")
        self.assertNotIn("private provider detail", json.dumps(report))
        failed = {check["name"] for check in report["checks"] if check["status"] == "failed"}
        self.assertEqual(failed, {"completion", "two_way_transcript"})

    def test_non_object_root_returns_sanitized_failure(self):
        self.write(["private malformed content"])
        report = verify_scorecard.verify_scorecard(self.directory, self.session_id)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "scorecard_schema")
        self.assertNotIn("private malformed content", json.dumps(report))

    def test_null_feedback_returns_sanitized_failure(self):
        self.payload["evaluation"]["feedback"] = None
        self.write()
        report = verify_scorecard.verify_scorecard(self.directory, self.session_id)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "evaluation")

    def test_invalid_id_does_not_read_arbitrary_path(self):
        report = verify_scorecard.verify_scorecard(self.directory, "../private")
        self.assertEqual(report["status"], "failed")
        self.assertIsNone(report["session_id"])
        self.assertEqual(len(report["checks"]), 1)

    def test_cli_emits_only_sanitized_json(self):
        self.write()
        output = io.StringIO()
        with redirect_stdout(output):
            code = verify_scorecard.main([self.session_id, "--scorecard-dir", str(self.directory)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "passed")
        self.assertNotIn("Private answer", output.getvalue())


if __name__ == "__main__":
    unittest.main()

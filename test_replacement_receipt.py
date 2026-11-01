import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.livekit_agent.replacement_receipt import (
    main, record_replacement, verify_replacement,
)
from difficultai.scorecard import SCORECARD_DIMENSIONS


SESSION_ID = "a" * 32
REVISION = "1" * 40


def valid_scorecard():
    return {
        "session_id": SESSION_ID,
        "source_revision": REVISION,
        "status": "completed",
        "error": None,
        "scenario": {"private": "not copied"},
        "transcript": [
            {"role": "user", "content": "private user turn"},
            {"role": "assistant", "content": "private assistant turn"},
        ],
        "evaluation": {
            "scores": {name: 8 for name in SCORECARD_DIMENSIONS},
            "feedback": {"coaching_points": ["one", "two", "three"]},
        },
    }


class ReplacementReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.scorecard = self.directory / f"scorecard_{SESSION_ID}.json"
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_records_private_immutable_receipt(self):
        stamp = datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc)
        record = record_replacement(self.directory, SESSION_ID, REVISION, now=stamp)
        destination = self.directory / "replacement" / f"worker_replacement_{SESSION_ID}.json"
        self.assertEqual(json.loads(destination.read_text()), record)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("private user turn", destination.read_text())
        with self.assertRaises(FileExistsError):
            record_replacement(self.directory, SESSION_ID, REVISION)

    def test_verifier_binds_receipt_to_current_scorecard(self):
        record_replacement(self.directory, SESSION_ID, REVISION)
        report = verify_replacement(self.directory, SESSION_ID, REVISION)
        self.assertEqual(report["status"], "passed")
        payload = valid_scorecard()
        payload["evaluation"]["scores"]["clarity"] = 9
        self.scorecard.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after worker replacement"):
            verify_replacement(self.directory, SESSION_ID, REVISION)

    def test_rejects_revision_mismatch(self):
        with self.assertRaisesRegex(ValueError, "did not match"):
            record_replacement(self.directory, SESSION_ID, "2" * 40)

    def test_exclusive_fallback_supports_volumes_without_hard_links(self):
        with patch("apps.livekit_agent.replacement_receipt.os.link",
                   side_effect=OSError("unsupported")):
            record = record_replacement(self.directory, SESSION_ID, REVISION)
        destination = self.directory / "replacement" / f"worker_replacement_{SESSION_ID}.json"
        self.assertEqual(json.loads(destination.read_text()), record)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_cli_output_hides_scorecard_and_fingerprint(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([
                SESSION_ID, "--source-revision", REVISION,
                "--scorecard-dir", str(self.directory),
            ])
        self.assertEqual(status, 0)
        rendered = output.getvalue()
        self.assertNotIn("private user turn", rendered)
        self.assertNotIn(str(self.directory), rendered)
        self.assertNotIn("scorecard_sha256", rendered)
        self.assertEqual(json.loads(rendered)["status"], "recorded")


if __name__ == "__main__":
    unittest.main()

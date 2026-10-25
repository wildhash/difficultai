import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.livekit_agent.record_owner_acceptance import main, record_acceptance
from difficultai.scorecard import SCORECARD_DIMENSIONS


SESSION_ID = "a" * 32


def valid_scorecard(session_id=SESSION_ID):
    return {
        "session_id": session_id,
        "status": "completed",
        "error": None,
        "scenario": {"private": "omitted from acceptance"},
        "transcript": [
            {"role": "user", "content": "private user turn"},
            {"role": "assistant", "content": "private assistant turn"},
        ],
        "evaluation": {
            "scores": {name: 8 for name in SCORECARD_DIMENSIONS},
            "feedback": {"coaching_points": ["one", "two", "three"]},
        },
    }


class OwnerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        (self.directory / f"scorecard_{SESSION_ID}.json").write_text(
            json.dumps(valid_scorecard()), encoding="utf-8"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_records_minimal_immutable_owner_attestation(self):
        stamp = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        record = record_acceptance(
            self.directory, SESSION_ID, "accepted", "acceptable", now=stamp
        )
        destination = self.directory / "acceptance" / f"owner_acceptance_{SESSION_ID}.json"
        self.assertEqual(json.loads(destination.read_text()), record)
        self.assertEqual(record["evidence_type"], "owner_self_attestation")
        self.assertTrue(record["retained_scorecard_verified"])
        self.assertNotIn("transcript", destination.read_text())
        self.assertNotIn("scenario", destination.read_text())
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            record_acceptance(self.directory, SESSION_ID, "accepted", "acceptable")

    def test_rejects_unverified_scorecard(self):
        payload = valid_scorecard()
        payload["status"] = "failed"
        (self.directory / f"scorecard_{SESSION_ID}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "verification must pass"):
            record_acceptance(self.directory, SESSION_ID, "rejected", "unacceptable")

    def test_acceptance_requires_acceptable_live_audio(self):
        with self.assertRaisesRegex(ValueError, "acceptable live audio"):
            record_acceptance(self.directory, SESSION_ID, "accepted", "unacceptable")

    def test_rejection_can_record_audio_judgment(self):
        result = record_acceptance(
            self.directory, SESSION_ID, "rejected", "unacceptable"
        )
        self.assertEqual(result["decision"], "rejected")

    def test_rejects_naive_timestamp(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            record_acceptance(
                self.directory, SESSION_ID, "accepted", "acceptable",
                now=datetime(2026, 10, 25, 15, 0),
            )

    def test_exclusive_fallback_supports_volumes_without_hard_links(self):
        with patch("apps.livekit_agent.record_owner_acceptance.os.link",
                   side_effect=OSError("unsupported")):
            result = record_acceptance(
                self.directory, SESSION_ID, "accepted", "acceptable"
            )
        destination = self.directory / "acceptance" / f"owner_acceptance_{SESSION_ID}.json"
        self.assertEqual(json.loads(destination.read_text()), result)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_cli_output_is_sanitized(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([
                SESSION_ID, "--decision", "accepted", "--audio-quality", "acceptable",
                "--scorecard-dir", str(self.directory),
            ])
        self.assertEqual(status, 0)
        rendered = output.getvalue()
        self.assertNotIn("private user turn", rendered)
        self.assertNotIn(str(self.directory), rendered)
        self.assertEqual(json.loads(rendered)["status"], "recorded")


if __name__ == "__main__":
    unittest.main()

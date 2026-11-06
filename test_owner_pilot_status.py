import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.livekit_agent.owner_pilot_status import main, owner_pilot_status
from apps.livekit_agent.record_owner_acceptance import record_acceptance
from apps.livekit_agent.replacement_receipt import record_replacement
from difficultai.scorecard import SCORECARD_DIMENSIONS


SESSION_ID = "a" * 32
REVISION = "1" * 40


def valid_scorecard():
    return {
        "session_id": SESSION_ID,
        "source_revision": REVISION,
        "status": "completed",
        "error": None,
        "scenario": {"private": "not returned"},
        "transcript": [
            {"role": "user", "content": "private user turn"},
            {"role": "assistant", "content": "private assistant turn"},
        ],
        "evaluation": {
            "scores": {name: 8 for name in SCORECARD_DIMENSIONS},
            "feedback": {"coaching_points": ["one", "two", "three"]},
        },
    }


class OwnerPilotStatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.scorecard = self.directory / f"scorecard_{SESSION_ID}.json"

    def tearDown(self):
        self.temporary.cleanup()

    def test_invalid_id_stops_before_paths(self):
        report = owner_pilot_status(self.directory, "../private")
        self.assertEqual(report["stage"], "invalid_session")
        self.assertEqual(report["status"], "blocked")
        self.assertIsNone(report["session_id"])

    def test_missing_session_reports_first_step(self):
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "session_pending")
        self.assertEqual(report["checks"], [{"name": "scorecard", "status": "not_recorded"}])

    def test_verified_scorecard_reports_replacement_command(self):
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "scorecard_verified")
        self.assertIn(f"SESSION_ID={SESSION_ID}", report["next_action"])
        self.assertEqual(report["source_revision"], REVISION)

    def test_replacement_reports_owner_judgment_step(self):
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        record_replacement(
            self.directory, SESSION_ID, REVISION,
            now=datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc),
        )
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "replacement_verified")
        self.assertIn("record-owner-acceptance", report["next_action"])

    def test_complete_chain_reports_verified_decision(self):
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        record_replacement(
            self.directory, SESSION_ID, REVISION,
            now=datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc),
        )
        record_acceptance(
            self.directory, SESSION_ID, "accepted", "acceptable",
            now=datetime(2026, 11, 6, 15, 1, tzinfo=timezone.utc),
        )
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "acceptance_verified")
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["decision"], "accepted")

    def test_existing_invalid_evidence_blocks_without_private_content(self):
        payload = valid_scorecard()
        payload["transcript"] = [{"role": "user", "content": "private only"}]
        self.scorecard.write_text(json.dumps(payload), encoding="utf-8")
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "evidence_invalid")
        rendered = json.dumps(report)
        self.assertNotIn("private only", rendered)
        self.assertNotIn(str(self.directory), rendered)

    def test_inaccessible_evidence_is_not_reported_as_missing(self):
        with patch.object(Path, "stat", side_effect=PermissionError("private path")):
            report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "evidence_unavailable")
        self.assertEqual(report["status"], "blocked")
        self.assertNotIn("private path", json.dumps(report))

    def test_cli_output_is_sanitized(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([SESSION_ID, "--scorecard-dir", str(self.directory)])
        self.assertEqual(status, 0)
        self.assertNotIn(str(self.directory), output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["stage"], "session_pending")


if __name__ == "__main__":
    unittest.main()

import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.livekit_agent.owner_pilot_status import (
    latest_owner_pilot_status,
    main,
    owner_pilot_status,
)
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

    def test_malformed_scorecard_blocks_without_leaking_private_path(self):
        self.scorecard.write_text("{private broken json", encoding="utf-8")
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "evidence_invalid")
        self.assertEqual(report["status"], "blocked")
        self.assertNotIn(str(self.directory), json.dumps(report))

    def test_malformed_acceptance_blocks_without_leaking_private_path(self):
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        record_replacement(
            self.directory, SESSION_ID, REVISION,
            now=datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc),
        )
        acceptance = (
            self.directory / "acceptance" / f"owner_acceptance_{SESSION_ID}.json"
        )
        acceptance.parent.mkdir(parents=True)
        acceptance.write_text("{private broken json", encoding="utf-8")
        report = owner_pilot_status(self.directory, SESSION_ID)
        self.assertEqual(report["stage"], "evidence_invalid")
        self.assertEqual(report["status"], "blocked")
        self.assertNotIn(str(self.directory), json.dumps(report))

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

    def test_latest_reports_no_sessions_without_requiring_an_id(self):
        report = latest_owner_pilot_status(self.directory)
        self.assertEqual(report["stage"], "no_sessions")
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["session_id"])

    def test_latest_selects_newest_retained_scorecard_and_reports_next_step(self):
        older_id = "b" * 32
        older = self.directory / f"scorecard_{older_id}.json"
        older_payload = valid_scorecard()
        older_payload["session_id"] = older_id
        older.write_text(json.dumps(older_payload), encoding="utf-8")
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        older_time = older.stat().st_mtime_ns
        newer_time = older_time + 1_000_000
        os.utime(self.scorecard, ns=(newer_time, newer_time))

        report = latest_owner_pilot_status(self.directory)
        self.assertEqual(report["session_id"], SESSION_ID)
        self.assertEqual(report["stage"], "scorecard_verified")
        self.assertIn(f"SESSION_ID={SESSION_ID}", report["next_action"])

    def test_latest_ignores_unrelated_and_symlinked_files(self):
        private = self.directory / "private.json"
        private.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        self.scorecard.symlink_to(private)
        (self.directory / "scorecard_not-a-session.json").write_text(
            "private", encoding="utf-8"
        )
        report = latest_owner_pilot_status(self.directory)
        self.assertEqual(report["stage"], "no_sessions")
        self.assertNotIn("private", json.dumps(report))

    def test_latest_sanitizes_inaccessible_volume(self):
        with patch.object(Path, "iterdir", side_effect=PermissionError("private path")):
            report = latest_owner_pilot_status(self.directory)
        self.assertEqual(report["stage"], "evidence_unavailable")
        self.assertEqual(report["status"], "blocked")
        self.assertNotIn("private path", json.dumps(report))

    def test_latest_cli_outputs_only_privacy_safe_status(self):
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["--latest", "--scorecard-dir", str(self.directory)])
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["session_id"], SESSION_ID)
        self.assertNotIn("private user turn", output.getvalue())
        self.assertNotIn(str(self.directory), output.getvalue())


if __name__ == "__main__":
    unittest.main()

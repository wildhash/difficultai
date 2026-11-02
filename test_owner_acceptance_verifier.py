import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest

from apps.livekit_agent.record_owner_acceptance import record_acceptance
from apps.livekit_agent.replacement_receipt import record_replacement
from apps.livekit_agent.verify_owner_acceptance import main, verify_owner_acceptance
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


class OwnerAcceptanceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.scorecard = self.directory / f"scorecard_{SESSION_ID}.json"
        self.scorecard.write_text(json.dumps(valid_scorecard()), encoding="utf-8")
        record_replacement(
            self.directory, SESSION_ID, REVISION,
            now=datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc),
        )
        record_acceptance(
            self.directory, SESSION_ID, "accepted", "acceptable",
            now=datetime(2026, 11, 2, 15, 1, tzinfo=timezone.utc),
        )
        self.acceptance = (
            self.directory / "acceptance" / f"owner_acceptance_{SESSION_ID}.json"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_complete_retained_chain_passes(self):
        report = verify_owner_acceptance(self.directory, SESSION_ID)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["decision"], "accepted")
        self.assertEqual(report["source_revision"], REVISION)

    def test_missing_acceptance_fails_safely(self):
        self.acceptance.unlink()
        report = verify_owner_acceptance(self.directory, SESSION_ID)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "acceptance_file")
        self.assertNotIn(str(self.directory), json.dumps(report))

    def test_tampered_judgment_and_chronology_fail(self):
        payload = json.loads(self.acceptance.read_text())
        payload["live_audio_quality"] = "unacceptable"
        payload["replacement_verified_at"] = "2026-11-02T15:02:00Z"
        self.acceptance.write_text(json.dumps(payload), encoding="utf-8")
        report = verify_owner_acceptance(self.directory, SESSION_ID)
        failed = {check["name"] for check in report["checks"] if check["status"] == "failed"}
        self.assertEqual(failed, {"owner_judgment", "chronology"})

    def test_changed_private_scorecard_invalidates_chain_without_disclosure(self):
        payload = valid_scorecard()
        payload["transcript"][0]["content"] = "changed private content"
        self.scorecard.write_text(json.dumps(payload), encoding="utf-8")
        report = verify_owner_acceptance(self.directory, SESSION_ID)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["name"], "worker_replacement")
        self.assertNotIn("changed private content", json.dumps(report))

    def test_cli_output_is_sanitized(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([
                SESSION_ID, "--scorecard-dir", str(self.directory),
            ])
        self.assertEqual(status, 0)
        rendered = output.getvalue()
        self.assertNotIn("private user turn", rendered)
        self.assertNotIn(str(self.directory), rendered)
        self.assertEqual(json.loads(rendered)["status"], "passed")

    def test_invalid_session_id_stops_before_filesystem_paths(self):
        report = verify_owner_acceptance(self.directory, "../private")
        self.assertEqual(report["status"], "failed")
        self.assertIsNone(report["session_id"])
        self.assertEqual([check["name"] for check in report["checks"]], ["session_id"])


if __name__ == "__main__":
    unittest.main()

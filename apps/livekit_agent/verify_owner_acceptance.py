"""Verify retained owner acceptance without exposing private session content."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from apps.livekit_agent.replacement_receipt import verify_replacement
from apps.livekit_agent.verify_scorecard import SESSION_ID, verify_scorecard


def _timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None


def verify_owner_acceptance(directory: Path, session_id: str) -> dict:
    """Return sanitized structural evidence for one retained owner attestation."""
    checks = []

    def record(name, passed, detail):
        checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})

    if not SESSION_ID.fullmatch(session_id):
        record("session_id", False, "Expected a 32-character lowercase hexadecimal session ID.")
        return _report(session_id, checks)
    record("session_id", True, "Session ID format is valid.")

    scorecard = verify_scorecard(directory, session_id)
    scorecard_passed = scorecard["status"] == "passed"
    record("retained_scorecard", scorecard_passed,
           "Retained scorecard passes the privacy-safe structural verifier.")
    if not scorecard_passed:
        return _report(session_id, checks)

    try:
        replacement = verify_replacement(directory, session_id, scorecard["source_revision"])
    except (OSError, ValueError):
        record("worker_replacement", False,
               "Worker replacement receipt is missing, invalid, or stale.")
        return _report(session_id, checks)
    record("worker_replacement", True,
           "Worker replacement receipt remains bound to the retained scorecard.")

    source = directory / "acceptance" / f"owner_acceptance_{session_id}.json"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        record("acceptance_file", False,
               f"Owner acceptance could not be read ({type(error).__name__}).")
        return _report(session_id, checks)
    record("acceptance_file", True, "Owner acceptance JSON is readable.")
    if not isinstance(payload, dict):
        record("acceptance_schema", False, "Owner acceptance root must be a JSON object.")
        return _report(session_id, checks)

    identity_valid = (
        payload.get("schema_version") == 2
        and payload.get("evidence_type") == "owner_self_attestation"
        and payload.get("session_id") == session_id
        and payload.get("source_revision") == scorecard["source_revision"]
    )
    record("identity", identity_valid,
           "Owner acceptance matches the session and exact source revision.")

    decision = payload.get("decision")
    audio_quality = payload.get("live_audio_quality")
    judgment_valid = (
        decision in ("accepted", "rejected")
        and audio_quality in ("acceptable", "unacceptable")
        and (decision != "accepted" or audio_quality == "acceptable")
    )
    record("owner_judgment", judgment_valid,
           "Owner decision and live-audio judgment are internally consistent.")

    recorded_at = _timestamp(payload.get("recorded_at"))
    replacement_at = _timestamp(payload.get("replacement_verified_at"))
    expected_replacement_at = replacement["verified_at"]
    chronology_valid = (
        recorded_at is not None
        and replacement_at == expected_replacement_at
        and recorded_at >= replacement_at
    )
    record("chronology", chronology_valid,
           "Acceptance follows the matching worker replacement verification.")

    flags_valid = (
        payload.get("retained_scorecard_verified") is True
        and payload.get("worker_replacement_verified") is True
    )
    record("verification_flags", flags_valid,
           "Acceptance records both required evidence gates.")
    return _report(
        session_id, checks,
        source_revision=scorecard["source_revision"] if identity_valid else None,
        decision=decision if judgment_valid else None,
    )


def _report(session_id, checks, source_revision=None, decision=None):
    failed = any(check["status"] == "failed" for check in checks)
    return {
        "schema_version": 1,
        "session_id": session_id if SESSION_ID.fullmatch(session_id) else None,
        "source_revision": source_revision,
        "decision": decision,
        "status": "failed" if failed else "passed",
        "checks": checks,
        "limitations": [
            "This verifies locally retained evidence, not an independent audit.",
            "It does not establish customer acceptance, payment, or revenue.",
        ],
        "next_action": (
            "Repair the first failed check before making an owner-acceptance claim."
            if failed else
            "Preserve the private evidence according to the owner's retention policy."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Session ID emitted by the voice worker")
    parser.add_argument("--scorecard-dir", type=Path,
                        default=Path(os.getenv("SCORECARD_DIR", "scorecards")))
    args = parser.parse_args(argv)
    report = verify_owner_acceptance(args.scorecard_dir, args.session_id)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

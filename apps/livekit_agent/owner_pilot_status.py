"""Report the next safe owner-pilot step without exposing private evidence."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from apps.livekit_agent.replacement_receipt import verify_replacement
from apps.livekit_agent.verify_owner_acceptance import verify_owner_acceptance
from apps.livekit_agent.verify_scorecard import SESSION_ID, verify_scorecard


def owner_pilot_status(directory: Path, session_id: str) -> dict:
    """Return a privacy-safe stage and exact next action for one session."""
    if not SESSION_ID.fullmatch(session_id):
        return _report(
            None, "invalid_session", "blocked", [],
            "Use the 32-character lowercase hexadecimal session ID emitted by the worker.",
        )

    checks = []
    scorecard_path = directory / f"scorecard_{session_id}.json"
    try:
        scorecard_present = _artifact_present(scorecard_path)
    except OSError:
        return _unavailable(session_id, checks)
    if not scorecard_present:
        checks.append({"name": "scorecard", "status": "not_recorded"})
        return _report(
            session_id, "session_pending", "incomplete", checks,
            "Complete the live owner session, then rerun this status command.",
        )

    scorecard = verify_scorecard(directory, session_id)
    if scorecard["status"] != "passed":
        checks.append({"name": "scorecard", "status": "invalid"})
        return _report(
            session_id, "evidence_invalid", "blocked", checks,
            "Do not claim completion; repair the scorecard failure or repeat the owner session.",
        )
    checks.append({"name": "scorecard", "status": "verified"})
    revision = scorecard["source_revision"]

    replacement_path = (
        directory / "replacement" / f"worker_replacement_{session_id}.json"
    )
    try:
        replacement_present = _artifact_present(replacement_path)
    except OSError:
        return _unavailable(session_id, checks, revision)
    if not replacement_present:
        checks.append({"name": "worker_replacement", "status": "not_recorded"})
        return _report(
            session_id, "scorecard_verified", "incomplete", checks,
            f"Run make owner-pilot-replace SESSION_ID={session_id}.",
            source_revision=revision,
        )
    try:
        verify_replacement(directory, session_id, revision)
    except (OSError, ValueError, KeyError, TypeError):
        checks.append({"name": "worker_replacement", "status": "invalid"})
        return _report(
            session_id, "evidence_invalid", "blocked", checks,
            "Do not record acceptance; repeat the owner session and replacement workflow.",
            source_revision=revision,
        )
    checks.append({"name": "worker_replacement", "status": "verified"})

    acceptance_path = (
        directory / "acceptance" / f"owner_acceptance_{session_id}.json"
    )
    try:
        acceptance_present = _artifact_present(acceptance_path)
    except OSError:
        return _unavailable(session_id, checks, revision)
    if not acceptance_present:
        checks.append({"name": "owner_acceptance", "status": "not_recorded"})
        return _report(
            session_id, "replacement_verified", "incomplete", checks,
            "Record the owner's decision with make record-owner-acceptance using the observed live-audio quality.",
            source_revision=revision,
        )

    acceptance = verify_owner_acceptance(directory, session_id)
    if acceptance["status"] != "passed":
        checks.append({"name": "owner_acceptance", "status": "invalid"})
        return _report(
            session_id, "evidence_invalid", "blocked", checks,
            "Do not claim acceptance; inspect the private evidence and repeat the owner workflow.",
            source_revision=revision,
        )
    checks.append({"name": "owner_acceptance", "status": "verified"})
    return _report(
        session_id, "acceptance_verified", "verified", checks,
        "Preserve the private evidence according to the owner's retention policy.",
        source_revision=revision,
        decision=acceptance["decision"],
    )


def _artifact_present(path: Path) -> bool:
    """Distinguish a missing future artifact from inaccessible evidence."""
    try:
        path.stat()
    except FileNotFoundError:
        return False
    return True


def _unavailable(session_id, checks, source_revision=None):
    return _report(
        session_id, "evidence_unavailable", "blocked", checks,
        "Do not continue; restore access to the private evidence and rerun this status command.",
        source_revision=source_revision,
    )


def _report(session_id, stage, status, checks, next_action,
            source_revision=None, decision=None):
    return {
        "schema_version": 1,
        "session_id": session_id,
        "source_revision": source_revision,
        "decision": decision,
        "stage": stage,
        "status": status,
        "checks": checks,
        "limitations": [
            "This reports locally retained evidence, not an independent audit.",
            "It does not establish customer acceptance, payment, or revenue.",
        ],
        "next_action": next_action,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Session ID emitted by the voice worker")
    parser.add_argument(
        "--scorecard-dir", type=Path,
        default=Path(os.getenv("SCORECARD_DIR", "scorecards")),
    )
    args = parser.parse_args(argv)
    report = owner_pilot_status(args.scorecard_dir, args.session_id)
    print(json.dumps(report, indent=2))
    return 1 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())

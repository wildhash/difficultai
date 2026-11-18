"""Verify retained owner-session evidence without printing private content."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

# Preserve the documented direct-script entrypoint without shadowing installed modules.
ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from difficultai.scorecard import SCORECARD_DIMENSIONS

SESSION_ID = re.compile(r"[0-9a-f]{32}")
SOURCE_REVISION = re.compile(r"[0-9a-f]{40}")
MAX_SCORECARD_BYTES = 4 * 1024 * 1024


class RetainedEvidenceError(ValueError):
    """A sanitized retained-evidence file-policy failure."""


def read_bounded_regular_json(source: Path, max_bytes: int, label: str):
    """Read bounded JSON from one regular file without following a final symlink."""
    metadata = source.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise RetainedEvidenceError(f"{label} must be a regular file.")
    if metadata.st_size > max_bytes:
        raise RetainedEvidenceError(f"{label} exceeds the retained-evidence size limit.")

    descriptor = os.open(
        source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise RetainedEvidenceError(f"{label} must be a regular file.")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            contents = stream.read(max_bytes + 1)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(contents) > max_bytes:
        raise RetainedEvidenceError(f"{label} exceeds the retained-evidence size limit.")
    return json.loads(contents.decode("utf-8"))


def verify_scorecard(directory: Path, session_id: str) -> dict:
    """Return only structural evidence; never return transcript or scenario text."""
    checks = []

    def record(name, passed, detail):
        checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})

    if not SESSION_ID.fullmatch(session_id):
        record("session_id", False, "Expected a 32-character lowercase hexadecimal session ID.")
        return _report(session_id, checks)

    record("session_id", True, "Session ID format is valid.")
    source = directory / f"scorecard_{session_id}.json"
    try:
        payload = read_bounded_regular_json(
            source, MAX_SCORECARD_BYTES, "Scorecard"
        )
    except (OSError, ValueError) as error:
        record("scorecard_file", False, f"Scorecard could not be read ({type(error).__name__}).")
        return _report(session_id, checks)

    record("scorecard_file", True, "Scorecard JSON is readable after restart.")
    if not isinstance(payload, dict):
        record("scorecard_schema", False, "Scorecard root must be a JSON object.")
        return _report(session_id, checks)
    record("identity", payload.get("session_id") == session_id, "Stored session ID matches the requested session.")

    source_revision = payload.get("source_revision")
    revision_valid = isinstance(source_revision, str) and bool(SOURCE_REVISION.fullmatch(source_revision))
    record("source_revision", revision_valid, "Session evidence is bound to an exact Git revision.")

    completed = payload.get("status") == "completed" and payload.get("error") in (None, "")
    record("completion", completed, "Session completed without a recorded provider error.")

    transcript = payload.get("transcript")
    valid_turns = isinstance(transcript, list) and all(
        isinstance(turn, dict)
        and turn.get("role") in ("user", "assistant")
        and isinstance(turn.get("content"), str)
        and bool(turn["content"].strip())
        for turn in transcript
    )
    roles = {turn.get("role") for turn in transcript} if valid_turns else set()
    two_way = valid_turns and {"user", "assistant"}.issubset(roles)
    record("two_way_transcript", two_way, "Transcript contains non-empty user and assistant turns.")

    evaluation = payload.get("evaluation")
    scores = evaluation.get("scores") if isinstance(evaluation, dict) else None
    scores_valid = isinstance(scores, dict) and set(scores) == set(SCORECARD_DIMENSIONS) and all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and 1 <= value <= 10
        for value in scores.values()
    )
    feedback = evaluation.get("feedback") if isinstance(evaluation, dict) else None
    coaching = feedback.get("coaching_points") if isinstance(feedback, dict) else None
    evaluation_valid = scores_valid and isinstance(coaching, list) and len(coaching) == 3
    record("evaluation", evaluation_valid, "Evaluation has six 1-10 scores and three coaching points.")
    return _report(session_id, checks, source_revision if revision_valid else None)


def _report(session_id: str, checks: list[dict], source_revision=None) -> dict:
    failed = any(check["status"] == "failed" for check in checks)
    return {
        "schema_version": 2,
        "session_id": session_id if SESSION_ID.fullmatch(session_id) else None,
        "source_revision": source_revision,
        "status": "failed" if failed else "passed",
        "checks": checks,
        "limitations": [
            "Does not test live audio quality or provider access.",
            "Proves retention only when run after an actual worker or container replacement.",
            "Does not establish owner or customer acceptance.",
        ],
        "next_action": (
            "Repair the first failed check and repeat the owner session and replacement test."
            if failed else
            "Record owner acceptance separately; do not publish the private scorecard."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Session ID emitted by the voice worker")
    parser.add_argument("--scorecard-dir", type=Path,
                        default=Path(os.getenv("SCORECARD_DIR", "scorecards")))
    args = parser.parse_args(argv)
    report = verify_scorecard(args.scorecard_dir, args.session_id)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

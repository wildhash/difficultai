"""Verify the newest retained credentialed preflight without exposing details."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from apps.livekit_agent.verify_scorecard import (
    SOURCE_REVISION,
    read_bounded_regular_json,
)

PREFLIGHT_FILE = re.compile(r"preflight_([0-9a-f]{32})[.]json")
MAX_PREFLIGHT_BYTES = 64 * 1024
REQUIRED_CHECKS = {
    "components",
    "storage",
    "configuration",
    "livekit_connectivity",
    "openai_connectivity",
}


def verify_latest_preflight(directory: Path, revision: str) -> dict:
    revision_valid = isinstance(revision, str) and bool(SOURCE_REVISION.fullmatch(revision))
    if not revision_valid:
        return _report(None, "failed", "Use an exact 40-character source revision.")

    candidates = []
    try:
        for path in directory.iterdir():
            if not PREFLIGHT_FILE.fullmatch(path.name):
                continue
            metadata = path.lstat()
            if stat.S_ISREG(metadata.st_mode):
                candidates.append((metadata.st_mtime_ns, path))
    except OSError:
        return _report(revision, "failed", "Restore access to retained preflight evidence and redeploy.")
    if not candidates:
        return _report(revision, "failed", "Run make owner-pilot-deploy before creating a session.")

    _, latest = max(candidates)
    try:
        payload = read_bounded_regular_json(
            latest, MAX_PREFLIGHT_BYTES, "Preflight report"
        )
    except (OSError, ValueError):
        return _report(revision, "failed", "The newest preflight report is invalid; redeploy.")

    checks = payload.get("checks") if isinstance(payload, dict) else None
    passed_names = [
        check.get("name")
        for check in checks or []
        if isinstance(check, dict) and check.get("status") == "passed"
    ]
    valid = (
        isinstance(checks, list)
        and len(checks) == len(REQUIRED_CHECKS)
        and payload.get("mode") == "connectivity"
        and payload.get("status") == "passed"
        and payload.get("source_revision") == revision
        and set(passed_names) == REQUIRED_CHECKS
    )
    return _report(
        revision,
        "passed" if valid else "failed",
        (
            "Credentialed preflight passed for this source revision."
            if valid else
            "The newest preflight does not authorize this source revision; redeploy."
        ),
    )


def _report(revision, status, next_action):
    return {
        "schema_version": 1,
        "source_revision": revision,
        "status": status,
        "checks": [{
            "name": "credentialed_preflight",
            "status": status,
        }],
        "limitations": [
            "This verifies retained connectivity evidence, not current provider availability.",
            "It does not establish live audio quality, owner acceptance, payment, or revenue.",
        ],
        "next_action": next_action,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_revision")
    parser.add_argument(
        "--scorecard-dir", type=Path,
        default=Path(os.getenv("SCORECARD_DIR", "scorecards")),
    )
    args = parser.parse_args(argv)
    report = verify_latest_preflight(args.scorecard_dir / "preflight", args.source_revision)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

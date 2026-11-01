"""Persist and verify privacy-safe evidence of an owner-pilot worker replacement."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from apps.livekit_agent.verify_scorecard import SESSION_ID, SOURCE_REVISION, verify_scorecard


DIGEST = re.compile(r"[0-9a-f]{64}")


def _destination(directory: Path, session_id: str) -> Path:
    if not SESSION_ID.fullmatch(session_id):
        raise ValueError("Expected a 32-character lowercase hexadecimal session ID")
    return directory / "replacement" / f"worker_replacement_{session_id}.json"


def _publish_private_json(destination: Path, payload: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            raise
        except OSError:
            with open(temporary, "rb") as source:
                handle = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(handle, "wb") as target:
                    target.write(source.read())
                    target.flush()
                    os.fsync(target.fileno())
        os.unlink(temporary)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def record_replacement(directory: Path, session_id: str, source_revision: str,
                       now=None) -> dict:
    """Write one immutable receipt after the replacement verifier succeeds."""
    if not SOURCE_REVISION.fullmatch(source_revision):
        raise ValueError("Source revision was invalid")
    evidence = verify_scorecard(directory, session_id)
    if evidence["status"] != "passed":
        raise ValueError("Retained scorecard verification must pass before receipt creation")
    if evidence["source_revision"] != source_revision:
        raise ValueError("Replacement revision did not match retained scorecard evidence")
    scorecard = directory / f"scorecard_{session_id}.json"
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("Replacement timestamp must be timezone-aware")
    record = {
        "schema_version": 1,
        "evidence_type": "worker_replacement_verification",
        "session_id": session_id,
        "source_revision": source_revision,
        "scorecard_sha256": sha256(scorecard.read_bytes()).hexdigest(),
        "verified_at": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "This is locally recorded replacement evidence, not independent verification.",
            "It does not establish voice quality, owner acceptance, payment, or revenue.",
        ],
    }
    destination = _destination(directory, session_id)
    if destination.exists():
        raise FileExistsError("A worker replacement receipt already exists for this session")
    _publish_private_json(destination, record)
    return record


def verify_replacement(directory: Path, session_id: str, source_revision: str) -> dict:
    """Verify that an immutable receipt still binds the current private scorecard."""
    destination = _destination(directory, session_id)
    try:
        record = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("A valid worker replacement receipt is required before owner acceptance") from error
    expected = {
        "schema_version": 1,
        "evidence_type": "worker_replacement_verification",
        "session_id": session_id,
        "source_revision": source_revision,
    }
    if not isinstance(record, dict) or any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("Worker replacement receipt did not match the retained session evidence")
    digest = record.get("scorecard_sha256")
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ValueError("Worker replacement receipt fingerprint was invalid")
    scorecard = directory / f"scorecard_{session_id}.json"
    try:
        current = sha256(scorecard.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError("Retained scorecard was unavailable during replacement verification") from error
    if current != digest:
        raise ValueError("Retained scorecard changed after worker replacement verification")
    try:
        verified_at = datetime.fromisoformat(str(record.get("verified_at", "")).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Worker replacement receipt timestamp was invalid") from error
    if verified_at.tzinfo is None:
        raise ValueError("Worker replacement receipt timestamp was invalid")
    return {"status": "passed", "verified_at": verified_at.astimezone(timezone.utc)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--scorecard-dir", type=Path,
                        default=Path(os.getenv("SCORECARD_DIR", "scorecards")))
    args = parser.parse_args(argv)
    try:
        result = record_replacement(
            args.scorecard_dir, args.session_id, args.source_revision
        )
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    print(json.dumps({
        "status": "recorded",
        "session_id": result["session_id"],
        "source_revision": result["source_revision"],
        "evidence_type": result["evidence_type"],
        "limitations": result["limitations"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

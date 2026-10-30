"""Record a privacy-safe owner attestation for one verified voice session."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from apps.livekit_agent.verify_scorecard import verify_scorecard


def record_acceptance(directory: Path, session_id: str, decision: str,
                      audio_quality: str, now=None) -> dict:
    """Write one immutable self-attestation after structural evidence passes."""
    evidence = verify_scorecard(directory, session_id)
    if evidence["status"] != "passed":
        raise ValueError("Retained scorecard verification must pass before acceptance is recorded")
    if decision not in ("accepted", "rejected"):
        raise ValueError("Decision must be accepted or rejected")
    if audio_quality not in ("acceptable", "unacceptable"):
        raise ValueError("Audio quality must be acceptable or unacceptable")
    if decision == "accepted" and audio_quality != "acceptable":
        raise ValueError("An accepted session must have acceptable live audio")

    destination = directory / "acceptance" / f"owner_acceptance_{session_id}.json"
    if destination.exists():
        raise FileExistsError("An owner acceptance record already exists for this session")
    destination.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("Acceptance timestamp must be timezone-aware")
    timestamp = timestamp.astimezone(timezone.utc)
    record = {
        "schema_version": 2,
        "evidence_type": "owner_self_attestation",
        "session_id": session_id,
        "source_revision": evidence["source_revision"],
        "decision": decision,
        "live_audio_quality": audio_quality,
        "recorded_at": timestamp.isoformat().replace("+00:00", "Z"),
        "retained_scorecard_verified": True,
        "limitations": [
            "This is a manually recorded owner attestation, not independent verification.",
            "It does not establish customer acceptance, payment, or revenue.",
        ],
    }
    descriptor, temporary = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        # A hard link publishes the fully flushed file without overwriting a
        # decision that may have appeared after the existence check.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            raise
        except OSError:
            # Some persistent volumes do not support hard links. O_EXCL keeps
            # the fallback non-overwriting, though publication is not atomic.
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
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Session ID emitted by the voice worker")
    parser.add_argument("--decision", required=True, choices=("accepted", "rejected"))
    parser.add_argument("--audio-quality", required=True,
                        choices=("acceptable", "unacceptable"))
    parser.add_argument("--scorecard-dir", type=Path,
                        default=Path(os.getenv("SCORECARD_DIR", "scorecards")))
    args = parser.parse_args(argv)
    try:
        result = record_acceptance(
            args.scorecard_dir, args.session_id, args.decision, args.audio_quality
        )
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    print(json.dumps({
        "status": "recorded",
        "session_id": result["session_id"],
        "source_revision": result["source_revision"],
        "decision": result["decision"],
        "evidence_type": result["evidence_type"],
        "limitations": result["limitations"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

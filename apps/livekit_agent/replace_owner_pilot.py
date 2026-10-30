"""Replace the owner-pilot worker and verify retained evidence without exposing it."""

import argparse
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from apps.livekit_agent.verify_scorecard import SESSION_ID


COMPOSE = ("docker", "compose", "--file", "compose.owner-pilot.yml")
DIGEST = re.compile(r"[0-9a-f]{64}")
DIGEST_CODE = (
    "from hashlib import sha256; from pathlib import Path; import sys; "
    "p=Path('/data/scorecards') / f'scorecard_{sys.argv[1]}.json'; "
    "print(sha256(p.read_bytes()).hexdigest())"
)


class ReplacementError(RuntimeError):
    """A sanitized replacement-verification failure."""


def _run(stage, arguments, *, root, runner, capture_output=True):
    result = runner(
        [*COMPOSE, *arguments], cwd=root, check=False,
        capture_output=capture_output, text=capture_output,
    )
    if result.returncode != 0:
        raise ReplacementError(f"{stage} failed; inspect private service logs locally before retrying")
    return result


def _require_running(*, root, runner, stage):
    result = _run(
        stage, ("ps", "--status", "running", "--services"),
        root=root, runner=runner,
    )
    if "worker" not in result.stdout.splitlines():
        raise ReplacementError(f"{stage} failed; worker is not running")


def _verify_and_digest(session_id, *, root, runner, stage):
    _run(
        f"{stage} scorecard verification",
        ("exec", "-T", "worker", "python", "-m",
         "apps.livekit_agent.verify_scorecard", session_id),
        root=root, runner=runner,
    )
    result = _run(
        f"{stage} scorecard fingerprint",
        ("exec", "-T", "worker", "python", "-c", DIGEST_CODE, session_id),
        root=root, runner=runner,
    )
    digest = result.stdout.strip()
    if not DIGEST.fullmatch(digest):
        raise ReplacementError(f"{stage} scorecard fingerprint was invalid")
    return digest


def replace_and_verify(session_id, *, root=ROOT, runner=subprocess.run):
    if not SESSION_ID.fullmatch(session_id):
        raise ReplacementError("expected a 32-character lowercase hexadecimal session ID")

    root = Path(root)
    _require_running(root=root, runner=runner, stage="Pre-replacement status")
    before = _verify_and_digest(session_id, root=root, runner=runner, stage="Pre-replacement")
    _run(
        "Worker replacement",
        ("up", "-d", "--no-deps", "--no-build", "--force-recreate", "worker"),
        root=root, runner=runner, capture_output=False,
    )
    _require_running(root=root, runner=runner, stage="Post-replacement status")
    after = _verify_and_digest(session_id, root=root, runner=runner, stage="Post-replacement")
    if before != after:
        raise ReplacementError("retained scorecard changed across worker replacement")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Session ID emitted by the completed owner session")
    args = parser.parse_args(argv)
    try:
        replace_and_verify(args.session_id)
    except ReplacementError as error:
        print(f"Owner-pilot replacement verification failed: {error}", file=sys.stderr)
        return 1
    print("Owner-pilot worker was replaced and the same structurally valid scorecard remained available.")
    print("Private content and its fingerprint were not printed; owner acceptance remains separate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

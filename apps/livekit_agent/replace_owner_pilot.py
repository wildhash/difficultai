"""Replace the owner-pilot worker and verify retained evidence without exposing it."""

import argparse
import json
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from apps.livekit_agent.verify_scorecard import SESSION_ID, SOURCE_REVISION


COMPOSE = ("docker", "compose", "--file", "compose.owner-pilot.yml")
DIGEST = re.compile(r"[0-9a-f]{64}")
COMMAND_TIMEOUT_SECONDS = 16 * 60
DIGEST_CODE = (
    "from hashlib import sha256; from pathlib import Path; import os, sys; "
    "p=Path(os.environ['SCORECARD_DIR']) / f'scorecard_{sys.argv[1]}.json'; "
    "print(sha256(p.read_bytes()).hexdigest())"
)
REVISION_CODE = "import os; print(os.environ.get('DIFFICULTAI_BUILD_SHA', ''))"


class ReplacementError(RuntimeError):
    """A sanitized replacement-verification failure."""


def _run(stage, arguments, *, root, runner, capture_output=True):
    try:
        result = runner(
            [*COMPOSE, *arguments], cwd=root, check=False,
            capture_output=capture_output, text=capture_output,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise ReplacementError(
            f"{stage} timed out; inspect private service logs locally before retrying"
        ) from error
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
    verification = _run(
        f"{stage} scorecard verification",
        ("exec", "-T", "worker", "python", "-m",
         "apps.livekit_agent.verify_scorecard", session_id),
        root=root, runner=runner,
    )
    try:
        report = json.loads(verification.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise ReplacementError(f"{stage} scorecard verification output was invalid") from error
    source_revision = report.get("source_revision") if isinstance(report, dict) else None
    if not isinstance(source_revision, str) or not SOURCE_REVISION.fullmatch(source_revision):
        raise ReplacementError(f"{stage} scorecard source revision was invalid")
    worker = _run(
        f"{stage} worker revision",
        ("exec", "-T", "worker", "python", "-c", REVISION_CODE),
        root=root, runner=runner,
    )
    worker_revision = worker.stdout.strip()
    if not SOURCE_REVISION.fullmatch(worker_revision) or worker_revision != source_revision:
        raise ReplacementError(f"{stage} worker revision did not match scorecard evidence")
    result = _run(
        f"{stage} scorecard fingerprint",
        ("exec", "-T", "worker", "python", "-c", DIGEST_CODE, session_id),
        root=root, runner=runner,
    )
    digest = result.stdout.strip()
    if not DIGEST.fullmatch(digest):
        raise ReplacementError(f"{stage} scorecard fingerprint was invalid")
    return digest, source_revision


def replace_and_verify(session_id, *, root=ROOT, runner=subprocess.run,
                       sleeper=time.sleep, readiness_attempts=5):
    if not SESSION_ID.fullmatch(session_id):
        raise ReplacementError("expected a 32-character lowercase hexadecimal session ID")

    root = Path(root)
    _require_running(root=root, runner=runner, stage="Pre-replacement status")
    before, before_revision = _verify_and_digest(
        session_id, root=root, runner=runner, stage="Pre-replacement"
    )
    _run(
        "Worker replacement",
        ("up", "-d", "--no-deps", "--no-build", "--force-recreate", "worker"),
        root=root, runner=runner, capture_output=False,
    )
    last_error = None
    for attempt in range(readiness_attempts):
        try:
            _require_running(root=root, runner=runner, stage="Post-replacement status")
            after, after_revision = _verify_and_digest(
                session_id, root=root, runner=runner, stage="Post-replacement"
            )
            if before_revision != after_revision:
                raise ReplacementError("scorecard source revision changed across worker replacement")
            if before != after:
                raise ReplacementError("retained scorecard changed across worker replacement")
            return
        except ReplacementError as error:
            if "changed across" in str(error) or "revision did not match" in str(error):
                raise
            last_error = error
            if attempt + 1 < readiness_attempts:
                sleeper(2)
    raise ReplacementError(
        "post-replacement readiness checks did not pass within the bounded retry window"
    ) from last_error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Session ID emitted by the completed owner session")
    args = parser.parse_args(argv)
    try:
        replace_and_verify(args.session_id)
    except ReplacementError as error:
        print(f"Owner-pilot replacement verification failed: {error}", file=sys.stderr)
        return 1
    print("Owner-pilot worker was replaced; its revision matched the unchanged, structurally valid scorecard.")
    print("Private content and its fingerprint were not printed; owner acceptance remains separate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

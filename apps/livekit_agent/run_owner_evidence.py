"""Run one bounded owner-evidence command in the isolated Compose service."""

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (
    "docker", "compose", "--env-file", "/dev/null",
    "--file", "compose.owner-evidence.yml",
)
MODULES = (
    "owner_pilot_status",
    "verify_scorecard",
    "record_owner_acceptance",
    "verify_owner_acceptance",
)
COMMAND_TIMEOUT_SECONDS = 2 * 60


def run_evidence(module, arguments, *, root=ROOT, runner=subprocess.run):
    """Return a bounded result while keeping Docker errors out of public output."""
    command = [
        *COMPOSE, "run", "--rm", "--no-deps", "-T", "evidence",
        "python", "-m", f"apps.livekit_agent.{module}", *arguments,
    ]
    try:
        return runner(
            command,
            cwd=Path(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            "Evidence command timed out; inspect local Docker state before retrying"
        ) from error
    except OSError as error:
        raise RuntimeError(
            "Evidence command could not start; inspect local Docker state before retrying"
        ) from error


def main(argv=None, *, root=ROOT, runner=subprocess.run):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", choices=MODULES)
    args, module_args = parser.parse_known_args(argv)
    try:
        result = run_evidence(
            args.module, module_args, root=root, runner=runner
        )
    except RuntimeError as error:
        print(f"Owner evidence command blocked: {error}", file=sys.stderr)
        return 1

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.returncode != 0:
        print(
            "Owner evidence command failed; follow the privacy-safe report above, "
            "or inspect local Docker state if no report was produced.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

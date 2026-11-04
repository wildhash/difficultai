"""Read-only readiness gate for the owner-pilot Docker deployment."""

import json
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values

from apps.livekit_agent.deploy_owner_pilot import COMPOSE, DeploymentError, _source_revision
from apps.livekit_agent.smoke_test import environment_issues


ROOT = Path(__file__).resolve().parents[2]


def _check(name, status, detail, next_action=None):
    return {"name": name, "status": status, "detail": detail, "next_action": next_action}


def _run_quiet(command, *, root, runner, environment):
    try:
        result = runner(
            command, cwd=root, check=False, capture_output=True, text=True,
            env=environment, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def check_readiness(*, root=ROOT, runner=subprocess.run, git_runner=subprocess.run,
                    environ=None):
    """Return a sanitized report without building, starting, or contacting providers."""
    root = Path(root)
    checks = []

    revision = None
    try:
        revision = _source_revision(root, git_runner)
        checks.append(_check("source", "passed", "Checkout is clean and bound to a Git revision."))
    except (DeploymentError, OSError, subprocess.SubprocessError):
        checks.append(_check(
            "source", "failed", "Checkout is not a clean identifiable Git revision.",
            "Use a clean checkout of the intended commit.",
        ))

    env_path = root / ".env"
    configured = dict(environ if environ is not None else os.environ)
    if env_path.is_file():
        try:
            file_values = {key: value or "" for key, value in dotenv_values(env_path).items()}
            # Match Docker Compose: process values override the project .env file.
            configured = {**file_values, **configured}
            issues = environment_issues(configured)
        except (OSError, ValueError):
            issues = [".env"]
    else:
        issues = [".env"]

    if issues:
        checks.append(_check(
            "configuration", "failed", "Missing or invalid: " + ", ".join(issues),
            "Configure only the listed names in .env; do not commit credential values.",
        ))
    else:
        checks.append(_check(
            "configuration", "passed",
            "Required credential names and URL shape are present; values were not printed or tested.",
        ))

    process_environment = dict(environ if environ is not None else os.environ)
    if revision:
        process_environment["DIFFICULTAI_BUILD_SHA"] = revision
    compose_available = _run_quiet(
        ["docker", "compose", "version"], root=root, runner=runner,
        environment=process_environment,
    )
    daemon_available = compose_available and _run_quiet(
        ["docker", "info", "--format", "{{json .ServerVersion}}"], root=root,
        runner=runner, environment=process_environment,
    )
    if daemon_available:
        checks.append(_check("docker", "passed", "Docker Engine and Compose are reachable."))
    else:
        checks.append(_check(
            "docker", "failed", "Docker Engine or Compose is unavailable.",
            "Run this command on the intended host with a reachable Docker Engine and Compose plugin.",
        ))

    if revision and not issues and daemon_available:
        valid = _run_quiet(
            [*COMPOSE, "config", "--quiet"], root=root, runner=runner,
            environment=process_environment,
        )
        checks.append(_check(
            "compose", "passed" if valid else "failed",
            "Owner-pilot Compose configuration rendered successfully." if valid
            else "Owner-pilot Compose configuration did not render.",
            None if valid else "Correct the Compose configuration before deployment.",
        ))
    else:
        checks.append(_check(
            "compose", "not_run", "Source, configuration, and Docker must pass first."
        ))

    failed = [item for item in checks if item["status"] == "failed"]
    return {
        "schema_version": 1,
        "ready": not failed and all(item["status"] == "passed" for item in checks),
        "checks": checks,
        "not_verified": [
            "Credential validity or provider access",
            "Worker image build or deployment",
            "Live audio, retained real-session evidence, or owner acceptance",
        ],
        "next_action": failed[0]["next_action"] if failed else "Run make owner-pilot-deploy.",
    }


def main():
    report = check_readiness()
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())

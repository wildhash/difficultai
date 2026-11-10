"""Fail-closed deployment gate for the owner-pilot Compose worker."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ("docker", "compose", "--file", "compose.owner-pilot.yml")
REVISION = re.compile(r"[0-9a-f]{40}")
STAGE_TIMEOUTS = {
    "Compose validation": 30,
    "Worker image build": 20 * 60,
    "Credentialed provider preflight": 3 * 60,
    "Worker start": 2 * 60,
    "Worker status": 30,
    "Worker revision": 30,
    "Worker stop": 60,
}


class DeploymentError(RuntimeError):
    """A sanitized owner-pilot deployment failure."""


def _run(stage, arguments, *, root, runner, environment, capture_output=False):
    try:
        result = runner(
            [*COMPOSE, *arguments], cwd=root, check=False,
            capture_output=capture_output, text=capture_output, env=environment,
            timeout=STAGE_TIMEOUTS[stage],
        )
    except subprocess.TimeoutExpired as error:
        raise DeploymentError(
            f"{stage} timed out; inspect local Docker and provider state before retrying"
        ) from error
    except OSError as error:
        raise DeploymentError(
            f"{stage} could not run; inspect local Docker state before retrying"
        ) from error
    if result.returncode != 0:
        raise DeploymentError(f"{stage} failed; inspect the command output and correct it before retrying")
    return result


def _source_revision(root, git_runner):
    try:
        revision = git_runner(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=root, check=False,
            capture_output=True, text=True,
        )
    except OSError as error:
        raise DeploymentError(
            "the source revision could not be identified; deploy from a Git commit"
        ) from error
    value = revision.stdout.strip() if revision.returncode == 0 else ""
    if not REVISION.fullmatch(value):
        raise DeploymentError("the source revision could not be identified; deploy from a Git commit")
    try:
        status = git_runner(
            ["git", "status", "--porcelain"], cwd=root, check=False,
            capture_output=True, text=True,
        )
    except OSError as error:
        raise DeploymentError(
            "the source checkout could not be inspected; deployment was not started"
        ) from error
    if status.returncode != 0:
        raise DeploymentError("the source checkout could not be inspected; deployment was not started")
    if status.stdout.strip():
        raise DeploymentError("the source checkout has uncommitted changes; commit or discard them before deployment")
    return value


def deploy(*, root=ROOT, runner=subprocess.run, git_runner=subprocess.run):
    root = Path(root)
    if not (root / ".env").is_file():
        raise DeploymentError(".env is missing; configure the four required credentials before deployment")

    revision = _source_revision(root, git_runner)
    environment = os.environ.copy()
    environment["DIFFICULTAI_BUILD_SHA"] = revision

    _run("Compose validation", ("config", "--quiet"), root=root, runner=runner,
         environment=environment)
    _run("Worker image build", ("build", "worker"), root=root, runner=runner,
         environment=environment)
    _run(
        "Credentialed provider preflight",
        ("run", "--rm", "--no-deps", "worker", "python", "-m",
         "apps.livekit_agent.smoke_test"),
        root=root, runner=runner, environment=environment,
    )
    failure = "worker did not remain running and was stopped; scorecard storage was preserved"
    try:
        _run("Worker start", ("up", "-d", "--no-build", "worker"), root=root,
             runner=runner, environment=environment)
        status = _run(
            "Worker status", ("ps", "--status", "running", "--services"),
            root=root, runner=runner, environment=environment, capture_output=True,
        )
        if "worker" in status.stdout.splitlines():
            try:
                _run(
                    "Worker revision",
                    ("exec", "-T", "worker", "python", "-c",
                     "import os,sys; sys.exit(os.getenv('DIFFICULTAI_BUILD_SHA') != sys.argv[1])",
                     revision),
                    root=root, runner=runner, environment=environment,
                )
                return
            except DeploymentError:
                failure = (
                    "worker revision did not match the deployed commit and the worker was stopped; "
                    "scorecard storage was preserved"
                )
    except DeploymentError:
        pass

    # Stop only the service after an uncertain start; never remove its volume.
    try:
        _run("Worker stop", ("stop", "worker"), root=root, runner=runner,
             environment=environment)
    except DeploymentError:
        failure += "; automatic worker stop also failed, so inspect the service before retrying"
    raise DeploymentError(failure)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        deploy()
    except DeploymentError as error:
        print(f"Owner-pilot deployment blocked: {error}", file=sys.stderr)
        return 1
    print("Owner-pilot worker is running after Compose validation, image build, and LiveKit/OpenAI connectivity preflight.")
    print("Model generation, live audio, retained real-session evidence, and owner acceptance remain unverified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

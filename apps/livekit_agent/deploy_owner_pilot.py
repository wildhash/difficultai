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


class DeploymentError(RuntimeError):
    """A sanitized owner-pilot deployment failure."""


def _run(stage, arguments, *, root, runner, environment, capture_output=False):
    result = runner(
        [*COMPOSE, *arguments], cwd=root, check=False,
        capture_output=capture_output, text=capture_output, env=environment,
    )
    if result.returncode != 0:
        raise DeploymentError(f"{stage} failed; inspect the command output and correct it before retrying")
    return result


def _source_revision(root, git_runner):
    revision = git_runner(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=root, check=False,
        capture_output=True, text=True,
    )
    value = revision.stdout.strip() if revision.returncode == 0 else ""
    if not REVISION.fullmatch(value):
        raise DeploymentError("the source revision could not be identified; deploy from a Git commit")
    status = git_runner(
        ["git", "status", "--porcelain"], cwd=root, check=False,
        capture_output=True, text=True,
    )
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
        "Credentialed connectivity preflight",
        ("run", "--rm", "--no-deps", "worker", "python", "-m",
         "apps.livekit_agent.smoke_test"),
        root=root, runner=runner, environment=environment,
    )
    try:
        _run("Worker start", ("up", "-d", "--no-build", "worker"), root=root,
             runner=runner, environment=environment)
        status = _run(
            "Worker status", ("ps", "--status", "running", "--services"),
            root=root, runner=runner, environment=environment, capture_output=True,
        )
        if "worker" in status.stdout.splitlines():
            _run(
                "Worker revision",
                ("exec", "-T", "worker", "python", "-c",
                 "import os,sys; sys.exit(os.getenv('DIFFICULTAI_BUILD_SHA') != sys.argv[1])",
                 revision),
                root=root, runner=runner, environment=environment,
            )
            return
    except DeploymentError:
        pass

    # Stop only the service after an uncertain start; never remove its volume.
    try:
        runner([*COMPOSE, "stop", "worker"], cwd=root, check=False, env=environment)
    finally:
        raise DeploymentError("worker did not remain running and was stopped; scorecard storage was preserved")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        deploy()
    except DeploymentError as error:
        print(f"Owner-pilot deployment blocked: {error}", file=sys.stderr)
        return 1
    print("Owner-pilot worker is running after Compose validation, image build, and LiveKit connectivity preflight.")
    print("Live audio, OpenAI provider access, retained real-session evidence, and owner acceptance remain unverified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

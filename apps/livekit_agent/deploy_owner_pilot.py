"""Fail-closed deployment gate for the owner-pilot Compose worker."""

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ("docker", "compose", "--file", "compose.owner-pilot.yml")


class DeploymentError(RuntimeError):
    """A sanitized owner-pilot deployment failure."""


def _run(stage, arguments, *, root, runner, capture_output=False):
    result = runner(
        [*COMPOSE, *arguments], cwd=root, check=False,
        capture_output=capture_output, text=capture_output,
    )
    if result.returncode != 0:
        raise DeploymentError(f"{stage} failed; inspect the command output and correct it before retrying")
    return result


def deploy(*, root=ROOT, runner=subprocess.run):
    root = Path(root)
    if not (root / ".env").is_file():
        raise DeploymentError(".env is missing; configure the four required credentials before deployment")

    _run("Compose validation", ("config", "--quiet"), root=root, runner=runner)
    _run("Worker image build", ("build", "worker"), root=root, runner=runner)
    _run(
        "Credentialed connectivity preflight",
        ("run", "--rm", "--no-deps", "worker", "python", "-m",
         "apps.livekit_agent.smoke_test"),
        root=root, runner=runner,
    )
    try:
        _run("Worker start", ("up", "-d", "--no-build", "worker"), root=root, runner=runner)
        status = _run(
            "Worker status", ("ps", "--status", "running", "--services"),
            root=root, runner=runner, capture_output=True,
        )
        if "worker" in status.stdout.splitlines():
            return
    except DeploymentError:
        pass

    # Stop only the service after an uncertain start; never remove its volume.
    try:
        runner([*COMPOSE, "stop", "worker"], cwd=root, check=False)
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

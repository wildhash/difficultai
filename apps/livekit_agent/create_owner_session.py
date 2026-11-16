"""Create one configured LiveKit room and short-lived owner access token."""

import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import uuid

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = Path(__file__).resolve().parent
for location in (str(ROOT), str(MODULE_DIR)):
    if location not in sys.path:
        sys.path.append(location)

from scenario_validator import validate_scenario
from apps.livekit_agent.deploy_owner_pilot import (
    COMPOSE,
    DeploymentError,
    source_revision,
)

NAME = re.compile(r"[A-Za-z0-9_-]{1,128}")
LIVEKIT_VARS = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
SESSION_BOOTSTRAP_TIMEOUT_SECONDS = 30
WORKER_GATE_TIMEOUT_SECONDS = 30


def require_running_worker(*, root=ROOT, environ=None, runner=subprocess.run,
                           git_runner=subprocess.run) -> str:
    """Require the deployed worker to match the current clean commit."""
    root = Path(root)
    try:
        revision = source_revision(root, git_runner)
    except DeploymentError as error:
        raise ValueError(f"Owner-session gate blocked: {error}") from error

    environment = dict(os.environ)
    if environ is not None:
        environment.update(environ)
    environment["DIFFICULTAI_BUILD_SHA"] = revision

    def run(arguments):
        try:
            return runner(
                [*COMPOSE, *arguments], cwd=root, check=False,
                capture_output=True, text=True, env=environment,
                timeout=WORKER_GATE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError(
                "Owner-session gate timed out; inspect local Docker state before retrying"
            ) from error
        except OSError as error:
            raise ValueError(
                "Owner-session gate could not run; inspect local Docker state before retrying"
            ) from error

    status = run(("ps", "--status", "running", "--services"))
    if status.returncode != 0:
        raise ValueError(
            "Owner-session gate could not inspect the worker; run make owner-pilot-deploy"
        )
    if "worker" not in status.stdout.splitlines():
        raise ValueError(
            "Owner-pilot worker is not running; run make owner-pilot-deploy before creating a session"
        )

    worker_revision = run((
        "exec", "-T", "worker", "python", "-c",
        "import os,sys; sys.exit(os.getenv('DIFFICULTAI_BUILD_SHA') != sys.argv[1])",
        revision,
    ))
    if worker_revision.returncode != 0:
        raise ValueError(
            "Owner-pilot worker does not match the current commit; redeploy before creating a session"
        )
    return revision


def load_configuration(root: Path, environ: dict) -> dict:
    """Load the documented project .env without mutating the process environment."""
    configured = {}
    path = root / ".env"
    if path.is_file():
        try:
            configured = {key: value or "" for key, value in dotenv_values(path).items()}
        except (OSError, UnicodeError, ValueError) as error:
            raise ValueError("Project .env could not be read") from error
    # Match Docker Compose and the readiness gate: exported values win.
    return {**configured, **dict(environ)}


def load_scenario(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Scenario must be a JSON object")
    errors = validate_scenario(payload)
    if errors:
        raise ValueError("Scenario failed validation: " + "; ".join(errors))
    return payload


def configuration_issues(environ: dict) -> list[str]:
    issues = [name for name in LIVEKIT_VARS if not str(environ.get(name, "")).strip()]
    if "LIVEKIT_URL" not in issues:
        parsed = urlsplit(environ["LIVEKIT_URL"])
        if (parsed.scheme not in ("ws", "wss") or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            issues.append("LIVEKIT_URL")
        elif parsed.scheme == "ws" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            issues.append("LIVEKIT_URL")
    return issues


async def create_session(*, scenario: dict, room_name: str, identity: str,
                         ttl_minutes: int, environ: dict) -> dict:
    from livekit import api

    issues = configuration_issues(environ)
    if issues:
        raise ValueError("Missing or invalid: " + ", ".join(issues))
    if not NAME.fullmatch(room_name):
        raise ValueError("Room name must use 1-128 letters, numbers, underscores, or hyphens")
    if not NAME.fullmatch(identity):
        raise ValueError("Identity must use 1-128 letters, numbers, underscores, or hyphens")
    if not 5 <= ttl_minutes <= 120:
        raise ValueError("Token lifetime must be between 5 and 120 minutes")

    metadata = json.dumps(scenario, separators=(",", ":"), sort_keys=True)
    token = (
        api.AccessToken(environ["LIVEKIT_API_KEY"], environ["LIVEKIT_API_SECRET"])
        .with_identity(identity)
        .with_name("DifficultAI owner pilot")
        .with_ttl(timedelta(minutes=ttl_minutes))
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        ))
        .to_jwt()
    )
    async def create_room():
        async with api.LiveKitAPI(
            url=environ["LIVEKIT_URL"],
            api_key=environ["LIVEKIT_API_KEY"],
            api_secret=environ["LIVEKIT_API_SECRET"],
        ) as client:
            return await client.room.create_room(api.CreateRoomRequest(
                name=room_name,
                metadata=metadata,
            ))

    try:
        room = await asyncio.wait_for(
            create_room(), timeout=SESSION_BOOTSTRAP_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as error:
        raise ValueError(
            "Session bootstrap timed out; verify LiveKit connectivity before retrying"
        ) from error
    if room.name != room_name or room.metadata != metadata:
        raise ValueError("Room already exists with different metadata; choose another --room")
    return {
        "schema_version": 1,
        "livekit_url": environ["LIVEKIT_URL"],
        "room_name": room.name,
        "participant_identity": identity,
        "access_token": token,
        "expires_in_minutes": ttl_minutes,
        "next_action": "Paste these three connection values into the deployed app and start the owner session.",
        "sensitive": "The access token is short-lived. Do not commit or share this output.",
    }


def main(argv=None, *, root=ROOT, environ=None, runner=subprocess.run,
         git_runner=subprocess.run, worker_gate=require_running_worker):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-file", type=Path, required=True,
                        help="JSON copied from the DifficultAI scenario builder")
    parser.add_argument("--room", default=f"owner-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--identity", default=f"owner-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--ttl-minutes", type=int, default=30)
    args = parser.parse_args(argv)

    try:
        scenario = load_scenario(args.scenario_file)
        process_environment = os.environ if environ is None else environ
        worker_gate(
            root=Path(root), environ=process_environment,
            runner=runner, git_runner=git_runner,
        )
        configured = load_configuration(
            Path(root), process_environment
        )
        result = asyncio.run(create_session(
            scenario=scenario,
            room_name=args.room,
            identity=args.identity,
            ttl_minutes=args.ttl_minutes,
            environ=configured,
        ))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({
            "status": "failed",
            "error": f"Scenario file could not be read ({type(error).__name__}).",
        }))
        return 1
    except ValueError as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    except Exception as error:
        print(json.dumps({
            "status": "failed",
            "error": f"Session bootstrap failed ({type(error).__name__}).",
        }))
        return 1

    print(json.dumps({"status": "created", **result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

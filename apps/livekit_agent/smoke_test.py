"""Connectivity preflight, not an end-to-end voice acceptance test.

Run with ``make smoke-test`` or use ``--offline`` for local checks only.
Reports contain check outcomes and next actions, never credentials or tokens.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit
import uuid

# Preserve the documented direct-script entrypoint.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REQUIRED_VARS = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY")
UNVERIFIED = [
    "OpenAI provider access",
    "Two-way live audio, interruption handling, and transcript delivery",
    "Real-session scorecard and retention across worker replacement",
    "Web deployment and owner acceptance",
]
SCENARIO = {
    "persona_type": "ELITE_INTERVIEWER", "company": "TestCorp",
    "role": "Software Engineer", "stakes": "Connectivity preflight",
    "user_goal": "Verify local components", "difficulty": 0.6,
}


def environment_issues(environ):
    issues = []
    # Match the worker's default and normalization before making service requests.
    if environ.get("VOICE_MODE", "realtime").strip().lower() not in ("realtime", "pipeline"):
        issues.append("VOICE_MODE")
    for name in REQUIRED_VARS:
        value = environ.get(name, "").strip()
        if not value or value.lower().startswith("your_"):
            issues.append(name)
    if "LIVEKIT_URL" not in issues:
        url = urlsplit(environ["LIVEKIT_URL"])
        if (url.scheme not in ("ws", "wss") or not url.hostname
                or url.username or url.password
                or url.hostname.startswith("your-") or url.query or url.fragment):
            issues.append("LIVEKIT_URL")
    return issues


def check_components():
    from agents.architect import ArchitectAgent
    from agents.evaluator import EvaluatorAgent
    from apps.livekit_agent.scenario_validator import validate_scenario
    from difficultai.scorecard import SCORECARD_DIMENSIONS
    from livekit import api, rtc  # Verify installed SDKs without opening a connection.

    ArchitectAgent()
    if validate_scenario(SCENARIO):
        raise ValueError("Fixture scenario failed validation")
    evaluation = EvaluatorAgent().evaluate_conversation({
        "vague_response_count": 1, "deflection_count": 0, "commitments_made": 2,
        "total_exchanges": 5, "current_difficulty": 0.6, "scenario_difficulty": 0.6,
    }, SCENARIO)
    scores = evaluation["scores"]
    if set(scores) != set(SCORECARD_DIMENSIONS) or any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not math.isfinite(value) or not 1 <= value <= 10
        for value in scores.values()
    ):
        raise ValueError("Evaluator must return six scores on the 1-10 scale")
    if len(evaluation["feedback"]["coaching_points"]) != 3:
        raise ValueError("Evaluator must return three coaching points")


def check_storage(directory):
    directory.mkdir(parents=True, exist_ok=True)
    probe = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".preflight-", delete=False) as file:
            probe = Path(file.name)
            file.write(b"difficultai-storage-probe")
            file.flush()
            os.fsync(file.fileno())
        if probe.read_bytes() != b"difficultai-storage-probe":
            raise OSError("Storage readback mismatch")
    finally:
        if probe is not None:
            probe.unlink(missing_ok=True)


async def check_livekit(environ, timeout=10):
    from livekit import api

    async with api.LiveKitAPI(
        url=environ["LIVEKIT_URL"], api_key=environ["LIVEKIT_API_KEY"],
        api_secret=environ["LIVEKIT_API_SECRET"],
    ) as client:
        await asyncio.wait_for(client.room.list_rooms(api.ListRoomsRequest()), timeout=timeout)


async def run_checks(*, offline=False):
    checks = []

    def record(name, status, detail, next_action=None):
        checks.append({"name": name, "status": status, "detail": detail, "next_action": next_action})

    for name, check, detail, action in (
        ("components", check_components, "SDK imports, scenario, and fixture scorecard passed.",
         "Install requirements.txt and repair the local component failure."),
        ("storage", lambda: check_storage(Path(os.getenv("SCORECARD_DIR", "scorecards"))),
         "Temporary file write/read passed; replacement durability remains unverified.",
         "Configure a writable SCORECARD_DIR on persistent storage."),
    ):
        try:
            check()
            record(name, "passed", detail)
        except Exception as error:
            # Provider exceptions can contain URLs, tokens, or keys. Record only the type.
            record(name, "failed", f"Check raised {type(error).__name__}.", action)

    if offline:
        record("configuration", "not_run", "Offline mode does not check credentials.")
        record("livekit_connectivity", "not_run", "Offline mode makes no service requests.")
    else:
        try:
            issues = environment_issues(os.environ)
        except ValueError:
            issues = ["LIVEKIT_URL"]
        if issues:
            record("configuration", "failed", "Missing or invalid: " + ", ".join(issues),
                   "Configure the listed environment variables; VOICE_MODE must be realtime or pipeline. Rerun.")
            record("livekit_connectivity", "not_run", "Configuration must pass first.")
        else:
            record("configuration", "passed", "Required values present; OpenAI access is not tested.")
            try:
                await check_livekit(os.environ)
                record("livekit_connectivity", "passed", "Authenticated LiveKit room listing succeeded.")
            except Exception as error:
                record("livekit_connectivity", "failed", f"Request raised {type(error).__name__}.",
                       "Check LiveKit credentials, network access, and server availability; rerun.")

    failed = [check for check in checks if check["status"] == "failed"]
    return {
        "schema_version": 1,
        "run_id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "offline" if offline else "connectivity",
        "status": "failed" if failed else "passed",
        "checks": checks,
        "not_verified": list(UNVERIFIED),
        "next_action": failed[0]["next_action"] if failed else (
            "Configure credentials and run make smoke-test." if offline else
            "Run one owner voice session, then restart the worker and verify its transcript and scorecard."
        ),
    }


def save_report(report, directory):
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"preflight_{report['run_id']}.json"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(report, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Skip credential checks and service I/O")
    parser.add_argument("--report-dir", type=Path, help="Retain a unique JSON report for every run")
    args = parser.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv()
    report = asyncio.run(run_checks(offline=args.offline))
    directory = args.report_dir or Path(os.getenv("SCORECARD_DIR", "scorecards")) / "preflight"
    try:
        save_report(report, directory)
    except OSError as error:
        report["status"] = "failed"
        report["checks"].append({
            "name": "report_storage", "status": "failed",
            "detail": f"Report was not saved ({type(error).__name__}).",
            "next_action": "Choose a writable report directory and rerun.",
        })
        report["next_action"] = "Choose a writable report directory and rerun."
    print(json.dumps(report, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())

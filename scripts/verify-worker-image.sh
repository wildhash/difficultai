#!/bin/sh
set -eu

image="${1:-difficultai-owner-pilot:verify}"
project="difficultai-worker-verify-$$"
marker="/data/scorecards/container-replacement-fixture"
fixture_session="cccccccccccccccccccccccccccccccc"
created_env=0

cleanup() {
  docker compose --project-name "$project" --file compose.owner-pilot.yml \
    down --volumes --remove-orphans >/dev/null 2>&1 || true
  if [ "$created_env" -eq 1 ]; then
    rm -f .env
  fi
}
trap cleanup EXIT
trap 'cleanup; exit 129' HUP
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

# Compose requires its configured env file even though this verification makes
# no service requests. Never replace a developer's existing credentials.
if [ ! -e .env ]; then
  umask 077
  cat >.env <<'EOF'
OPENAI_API_KEY=your_ci_fixture
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_ci_fixture
LIVEKIT_API_SECRET=your_ci_fixture
EOF
  created_env=1
fi

export DIFFICULTAI_IMAGE="$image"
DIFFICULTAI_BUILD_SHA="$(git rev-parse --verify HEAD)"
if ! printf '%s' "$DIFFICULTAI_BUILD_SHA" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "the source revision could not be identified; deploy from a Git commit" >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "the source checkout has uncommitted changes; image verification was not started" >&2
  exit 1
fi
export DIFFICULTAI_BUILD_SHA
compose="docker compose --project-name $project --file compose.owner-pilot.yml"
$compose config --quiet
$compose build

# The production image must execute as the unprivileged account declared in
# the Dockerfile and expose the supported LiveKit worker CLI.
$compose run --rm --no-deps worker sh -c 'test "$(id -u)" -ne 0'
$compose run --rm --no-deps worker python -m apps.livekit_agent --help >/dev/null
$compose run --rm --no-deps worker python -c \
  "import os,sys; sys.exit(os.environ.get('DIFFICULTAI_BUILD_SHA') != sys.argv[1])" \
  "$DIFFICULTAI_BUILD_SHA"
$compose run --rm --no-deps worker \
  python -m apps.livekit_agent.smoke_test --offline >/dev/null

# Two separate Compose containers must see the same configured volume fixture.
# This proves the deployment wiring without claiming that a live scorecard exists.
$compose run --rm --no-deps worker \
  python -c "from pathlib import Path; Path('$marker').write_text('fixture', encoding='utf-8')"
$compose run --rm --no-deps worker \
  python -c "from pathlib import Path; assert Path('$marker').read_text(encoding='utf-8') == 'fixture'"

# Exercise the complete private evidence chain through separate containers on
# the configured volume. This is an internal fixture, not a real voice session,
# owner decision, customer acceptance, payment, or revenue evidence.
$compose run --rm --no-deps -T worker \
  python - "$fixture_session" "$DIFFICULTAI_BUILD_SHA" <<'PY'
import json
from pathlib import Path
import sys

from difficultai.scorecard import SCORECARD_DIMENSIONS

session_id, source_revision = sys.argv[1:]
scorecard = {
    "session_id": session_id,
    "source_revision": source_revision,
    "status": "completed",
    "error": None,
    "scenario": {"fixture": True},
    "transcript": [
        {"role": "user", "content": "internal CI fixture user turn"},
        {"role": "assistant", "content": "internal CI fixture assistant turn"},
    ],
    "evaluation": {
        "scores": {name: 8 for name in SCORECARD_DIMENSIONS},
        "feedback": {"coaching_points": ["fixture one", "fixture two", "fixture three"]},
    },
}
destination = Path("/data/scorecards") / f"scorecard_{session_id}.json"
destination.write_text(json.dumps(scorecard), encoding="utf-8")
PY
# Recovery must remain available from the retained volume even when no worker
# service is running. This is still internal fixture evidence only.
$compose run --rm --no-deps worker \
  python -c "from pathlib import Path; from apps.livekit_agent.owner_pilot_status import latest_owner_pilot_status; assert latest_owner_pilot_status(Path('/data/scorecards'))['stage'] == 'scorecard_verified'"
$compose run --rm --no-deps worker \
  python apps/livekit_agent/replacement_receipt.py "$fixture_session" \
    --source-revision "$DIFFICULTAI_BUILD_SHA" >/dev/null
$compose run --rm --no-deps worker \
  python apps/livekit_agent/record_owner_acceptance.py "$fixture_session" \
    --decision accepted --audio-quality acceptable >/dev/null
$compose run --rm --no-deps worker \
  python apps/livekit_agent/verify_owner_acceptance.py "$fixture_session" >/dev/null
$compose run --rm --no-deps worker \
  python -c "from pathlib import Path; from apps.livekit_agent.owner_pilot_status import latest_owner_pilot_status; assert latest_owner_pilot_status(Path('/data/scorecards'))['stage'] == 'acceptance_verified'"

echo "worker image and internal acceptance-chain fixture verified"

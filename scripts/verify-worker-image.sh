#!/bin/sh
set -eu

image="${1:-difficultai-owner-pilot:verify}"
project="difficultai-worker-verify-$$"
marker="/data/scorecards/container-replacement-fixture"
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

echo "worker image and replacement-volume fixture verified"

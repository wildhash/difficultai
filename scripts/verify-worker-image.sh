#!/bin/sh
set -eu

image="${1:-difficultai-owner-pilot:verify}"
volume="difficultai-worker-verify-$$"
marker="/data/scorecards/container-replacement-fixture"

cleanup() {
  docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

docker build --tag "$image" .

# The production image must execute as the unprivileged account declared in
# the Dockerfile and expose the supported LiveKit worker CLI.
docker run --rm "$image" sh -c 'test "$(id -u)" -ne 0'
docker run --rm "$image" python -m apps.livekit_agent --help >/dev/null

# Two separate containers must see the same named-volume fixture. This proves
# the deployment storage wiring without claiming that a live scorecard exists.
docker volume create "$volume" >/dev/null
docker run --rm --volume "$volume:/data/scorecards" "$image" \
  python -c "from pathlib import Path; Path('$marker').write_text('fixture', encoding='utf-8')"
docker run --rm --volume "$volume:/data/scorecards" "$image" \
  python -c "from pathlib import Path; assert Path('$marker').read_text(encoding='utf-8') == 'fixture'"

echo "worker image and replacement-volume fixture verified"

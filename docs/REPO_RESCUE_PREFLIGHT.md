# Repo Rescue: executable preflight and development memory

Date: 2026-10-14. Baseline: `07d3d3c` (DifficultAI main).

## Diagnosis and decision

The next owner acceptance step depended on a smoke test that did not work with
the installed requirements. Running the original script with fixture credentials
failed before network I/O:

```text
LiveKit connection failed: module 'livekit.api' has no attribute 'RoomServiceClient'
```

The same script did not await room listing and subsequently read a nonexistent
`evaluation['scores']['overall']` field. The evaluator actually returns six
scores on a 1–10 scale. Its description also claimed it joined a room and
received transcripts, although the implementation only attempted room listing.
A separate reproduction showed `make clean` deleted saved owner scorecards.

Repair the preflight and preserve evidence before using it to guide the next
work cycle. A check can justify only what it actually exercises. This change
provides deterministic diagnosis and run history, not model training or an
independently operating self-modifying agent.

## Changes

- `apps/livekit_agent/smoke_test.py`: use `LiveKitAPI` as an async context manager,
  await room listing with a ten-second timeout, and close the client on success,
  failure, and cancellation. Validate the actual six-score evaluator contract.
- Reject missing/example credentials before service I/O. Do not print credentials,
  token fragments, room identities, or raw provider exceptions.
- Check local scorecard-directory write/read access. This does not prove retention
  across a container replacement or test a backup.
- Emit a JSON report with check outcomes, unverified capabilities, and the next
  action selected from failed checks. Preserve a unique, atomically replaced file
  per run under `$SCORECARD_DIR/preflight` (default `scorecards/preflight`).
- `Makefile`: add `preflight-offline`; preserve session evidence during `clean`.
- `test_smoke_test.py`: cover real SDK construction with substituted service I/O,
  awaited calls, timeout/cleanup, failed and offline runs, credential redaction,
  report retention, output/exit codes, and preservation of scorecards by `clean`.
- `.github/workflows/python-tests.yml`: run offline preflight, retain its JSON as
  a CI artifact, and use python-dotenv's actual `PYTHON_DOTENV_DISABLED` switch.

## Reproduce and verify

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
OPIK_DISABLED=1 PYTHON_DOTENV_DISABLED=1 python -m unittest discover -p 'test_*.py' -v
OPIK_DISABLED=1 PYTHON_DOTENV_DISABLED=1 python -m apps.livekit_agent --help
make preflight-offline
# After configuring .env with actual credentials:
make smoke-test
```

The direct script and `python -m apps.livekit_agent.smoke_test` entrypoints both
work. `--report-dir PATH` overrides the report destination. Exit code 1 means a
check failed, including failure to save the report. Exit code 0 means only that
the checks for the reported mode passed; inspect `not_verified` before making
any readiness claim. CI exercises offline mode and never contacts a provider.
Local proxy environments may need the optional `httpx[socks]` transport extra.

Local verification: 64 Python tests passed (52 existing plus 12 new); all 10 web
component tests and the Pages build passed. No live room or OpenAI request was
made. The existing web bundle-size warning remains.

## Current external blockers

The latest previously failed Pages run remains
[37513620791](https://github.com/wildhash/difficultai/actions/runs/37513620791):
build passed; Configure Pages returned `Not Found`; publication was skipped.
The connected GitHub tools provide repository and PR changes but no Pages
settings mutation. Repository permissions alone do not supply that operation.

An administrator must select **Settings → Pages → Build and deployment → Source:
GitHub Actions**, then rerun the Pages workflow. Adding `enablement: true` with
the workflow's normal token is not sufficient:
[configure-pages documents the separate token permissions required](https://github.com/actions/configure-pages/blob/main/action.yml).
Record the successful deployment run and actual public URL after verification.

LiveKit/OpenAI credentials are absent from this execution environment. After
configuration, run the connectivity preflight, complete a short owner voice
session, restart/replace the worker with its persistent volume mounted, and
verify its transcript and scorecard. Public deployment, live audio quality,
provider access, storage durability, and owner acceptance remain unverified.
No sale, customer acceptance, or revenue is represented by this repair.

## Resume the next development cycle

### 2026-10-15: reject an unusable voice mode before connectivity

Baseline: `00e78e256929c5aac6e8f85d9577b25d2ee8a46c` (merged PR #9).
No open PRs or issues were present in DifficultAI, RepoMan, or make_my_day.
The latest [Pages attempt](https://github.com/wildhash/difficultai/actions/runs/38682007426)
built successfully but failed Configure Pages with `Not Found`; deployment was
skipped. No rerun was requested because configuration access has not changed.

Diagnosis: connectivity preflight ignored `VOICE_MODE`, while the worker rejects
anything except normalized `realtime` or `pipeline`. With `VOICE_MODE=unsupported`
and fixture credentials, substituted component/network checks produced `passed`,
called the LiveKit check once, and recommended an owner session that could not
start. This is a local regression reproduction, not a successful provider call.

Decision: validate the mode in the existing configuration gate rather than change
the worker's accepted modes or silently fall back to a different provider path.
Missing mode retains the realtime default; whitespace and case follow the worker.
Invalid values are not echoed, and LiveKit I/O is skipped. Offline mode still
explicitly skips configuration and cannot establish configured readiness.

Verification: 66 Python tests passed (64 existing plus two regression tests),
worker CLI imports passed, and offline preflight passed. A separate substituted-I/O
probe covered nine valid/invalid/default cases. The first full-suite attempt had
one environment error from missing SOCKS support; installing the already documented
optional `httpx[socks]` extra locally resolved it. No dependency pins changed.
The PR #9 dotenv review concern was checked against installed python-dotenv 1.2.1:
`load_dotenv` itself honors `PYTHON_DOTENV_DISABLED`; no redundant guard was added.

Limitations: no live audio, provider access, replacement durability, deployment,
owner acceptance, payment, or revenue was verified. Web code was not changed or
retested in this cycle. Next executable owner action remains enabling Pages with
GitHub Actions, then verifying a deployment; next voice acceptance requires the
configured environment and persistent storage described above.

Rollback: revert only the voice-mode validation repair commit. This restores the
preflight blind spot but does not alter scorecards, worker behavior, or cleanup.

### 2026-10-20: distinguish documentation publication from demo deployment

Baseline: `2d3182ac7c3b79e4b60a4d5de5812df008c290f6` (merged PR #11).
The repository Pages workflow
[39314009903](https://github.com/wildhash/difficultai/actions/runs/39314009903)
published successfully at <https://wildhash.github.io/difficultai/>. A fresh HTTP
request returned status 200. The result is nevertheless the Jekyll-rendered
repository README, not the Vite app under `apps/web/demo`.

Diagnosis: a green Pages deployment proves that an artifact was published, but
not that the intended application was selected. The successful build rendered
the repository with Jekyll and uploaded `_site`; the custom Web demo workflow's
latest main run still failed before deploying `apps/web/demo/dist`.

Decision: do not change application code or claim owner acceptance. Select
**Settings → Pages → Build and deployment → Source: GitHub Actions**, then run
the existing **Web demo CI and Pages** workflow. Accept deployment only after the
public root loads the demo HTML and its versioned JavaScript and CSS assets.

Verification: CI logs show successful Jekyll build and publication, and an HTTP
fetch confirms the live documentation page. No LiveKit/OpenAI session, voice
quality, transcript, scorecard, worker-replacement persistence, customer
acceptance, payment, or revenue was verified.

Rollback: revert this documentation-only record if later evidence disproves it.
Changing or reverting documentation does not alter the Pages source setting.

### 2026-10-22: make artifact identity a deployment gate

Baseline: `484eae943fd4790b4430d197df42396c853749a7` (merged PR #12).
The automatic [Pages run 39672698390](https://github.com/wildhash/difficultai/actions/runs/39672698390)
after that merge succeeded, but its build job again used Jekyll. A fresh request
returned HTTP 200 with Jekyll metadata and repository documentation, not the Vite
owner-pilot application.

Diagnosis: status and publication checks alone cannot distinguish the intended
application from the wrong successful artifact. Waiting for the Pages source
setting is necessary, but leaves the workflow able to report green without an
explicit application-identity and asset-availability acceptance check.

Decision: add a post-deployment verifier to the existing workflow. It requires
the DifficultAI demo title plus same-origin, versioned JavaScript and CSS assets,
then fetches those assets. The verifier retries briefly for Pages propagation.
Unit regressions cover the current documentation false-positive, the expected
app, and a missing asset. This does not change the application or Pages setting.

Verification: all 10 component tests and five deployment-verifier regressions
passed. The Pages-mode production build passed and retained the existing 500 kB
chunk warning. A locally served Pages-shaped artifact passed the new gate with
both versioned assets; the current public documentation page was rejected as the
wrong artifact. The gate also rejects an HTTP-200 HTML fallback for an asset.

Limitations: this gate does not prove microphone access, LiveKit/OpenAI service,
voice quality, transcript/scorecard creation, replacement-storage durability,
owner acceptance, customer acceptance, payment, or revenue.

Next executable owner action: select **Settings → Pages → Build and deployment →
Source: GitHub Actions**, then run **Web demo CI and Pages**. The workflow must
pass its new post-deployment verification before the app is called deployed.

Rollback: revert this repair commit to remove only the artifact-identity gate;
it does not change application data, provider configuration, or Pages settings.

Post-merge evidence revised one conclusion. [Run 39806370378](https://github.com/wildhash/difficultai/actions/runs/39806370378)
built and deployed the Vite artifact successfully, then the gate immediately saw
the prior Jekyll page. A cache-busting request after propagation returned the app
title and both versioned assets. Therefore a title mismatch can be transient at
the deployment boundary. The follow-up repair cache-busts each page request and
retries this demonstrated stale-documentation state; a regression models the
stale page transitioning to the app. The static owner-pilot shell is deployed,
but live voice, persistent scorecards, and owner acceptance remain unverified.

1. Read this record and the latest repository/CI state; distinguish historical
   observations from fresh evidence. Do not repeat the same blocked deployment
   without changed configuration or access.
2. Inspect the newest retained preflight report. Use its failed check and next
   action as a hypothesis to verify, not authority to bypass permissions.
3. Reproduce one concrete failure, make the smallest repair, run the relevant
   regression checks, and preserve the commit, result, limitation, and next step.
4. Keep reports and session data on the configured persistent volume; back them
   up according to the owner's retention policy. Never commit private session
   transcripts or credentials to this public repository.

Rollback: revert this PR's commit. This restores the previous smoke-test entrypoint
and CI behavior; reverting also restores `make clean`'s scorecard deletion, so do
not run that older clean target against retained session data.

### 2026-10-23: make replacement evidence verifiable without transcript disclosure

Baseline: `1b424407a0dbe11cc675b09930d954195f9e36db` (merged PR #14).
The static owner-pilot shell remains deployed and its exact-main workflow is
green. There are no open PRs or issues in DifficultAI, RepoMan, or make_my_day.
LiveKit/OpenAI credentials and an explicit persistent `SCORECARD_DIR` are absent
from this execution environment, so a live session or replacement test cannot
be claimed.

Diagnosis: the runbook required manually verifying a private transcript and
scorecard after worker replacement, but provided no privacy-safe executable
check. Direct inspection risks disclosing session contents, while file existence
alone would accept a failed or one-way session.

Decision: add a read-only retained-scorecard verifier. It accepts only the
worker's 32-character session ID, reads only its expected filename, and emits a
sanitized report. It requires a completed session without a recorded error,
non-empty user and assistant turns, all six finite 1-10 scores, and three
coaching points. It does not expose the room, job, scenario, transcript, error,
or storage path.

Verification: seven verifier regressions cover a valid retained scorecard, a
missing file, failed/one-way evidence, non-object and null-feedback payloads,
traversal-shaped input, and sanitized CLI output. All 73 Python tests and the offline preflight passed. The first full-suite
attempt reproduced the documented local SOCKS transport dependency; installing
the optional `httpx[socks]` extra resolved it without changing project pins.

Limitations: fixtures do not prove provider access, live audio, a real worker
replacement, persistent storage, owner acceptance, payment, or revenue.

Next executable step: configure LiveKit/OpenAI and a persistent `SCORECARD_DIR`,
complete one owner session, record its session ID, replace the worker with that
volume mounted, and run `make verify-scorecard SESSION_ID=<session-id>` before
recording owner acceptance separately.

Rollback: revert the verifier commit. This removes only the read-only command,
tests, and documentation; it does not alter or delete saved scorecards.

Post-merge deployment evidence changed the diagnosis. The successful automatic
[Pages run 39982479976](https://github.com/wildhash/difficultai/actions/runs/39982479976)
for merge `e22d174` republished the Jekyll repository page because the custom
Vite workflow ignored Python/documentation-only pushes. A fresh cache-busted
request returned `Difficult AI | difficultai`, not the owner-pilot app.

Repair decision: run the custom build, deploy, and artifact-identity gate on
every `main` push. Keep pull-request path filtering so unrelated PRs do not run
the web suite twice. This closes the demonstrated route by which non-web merges
could silently replace a previously verified deployment. The exact repair head
must pass the web tests/build in PR CI; after merge, both the deployment workflow
and a fresh public fetch must show the Vite app before deployment is restored.

Rollback: revert only the workflow-trigger repair, understanding that this
reopens the demonstrated Jekyll-overwrite failure on later non-web merges.

### 2026-10-24: make the configured owner session executable

Baseline: `00b9e45837fc3c785693455464cbb480ed659018` (merged PR #16).
The deployed Vite app and versioned assets remain reachable. There are no open
PRs or issues in DifficultAI, RepoMan, or make_my_day. LiveKit/OpenAI credentials
and persistent scorecard storage remain absent from this execution environment.

Diagnosis: the recommended Python direct-connection instructions call
`livekit.api.RoomServiceClient`, which is absent from the pinned SDK. Generating
a participant token alone also does not attach the scenario configured in the
web app; the worker reads scenario JSON from room metadata. Therefore the
documented owner path could not create the configured session it described.

Decision: add an executable owner-pilot launcher using `LiveKitAPI` as an async
context manager. It validates the scenario and connection configuration, creates
a uniquely named room with canonical scenario metadata, and emits a participant
token limited to that room for 30 minutes by default. Names and token lifetime
are bounded. Provider failures report only their exception type. The output is
explicitly sensitive and must remain local. A public token service remains a
separate authenticated-backend requirement.

Verification: targeted regressions cover room metadata, room-scoped token claims,
client closure, invalid configuration before provider I/O, remote plaintext
rejection, token failure before room creation, conflicting reused-room metadata,
bounded identifiers and lifetime, malformed scenarios, and sanitized provider
failures. The full Python suite and offline
preflight must pass before merge. No provider request is made by tests.

Limitations: this repair does not prove credentials, worker deployment, live
audio, transcript delivery, scorecard retention across replacement, owner or
customer acceptance, payment, or revenue.

Next executable step: configure LiveKit/OpenAI and persistent `SCORECARD_DIR`,
run `make owner-session SCENARIO=owner-scenario.json`, connect through the
deployed app, complete one session, replace the worker, then run the retained
scorecard verifier and record owner acceptance separately.

Rollback: revert the owner-session launcher commit. It removes only the CLI,
tests, and documentation; it does not change or delete rooms or scorecards.

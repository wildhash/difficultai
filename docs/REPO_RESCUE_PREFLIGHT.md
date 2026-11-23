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

### 2026-10-25: make owner acceptance explicit and auditable

Baseline: `8cb2dadf61f8b871d37c589c003264dc0fb31d0f` (merged PR #17).
The Vite pilot remains deployed and no repository has competing open work.
Credentials and persistent runtime storage remain unavailable here, so a live
session cannot be fabricated or inferred from local fixtures.

Diagnosis: the runbook ended with “record owner acceptance separately,” but had
no executable format or gate. A free-form note could be confused with verified
session evidence, expose private content, or claim acceptance after a failed or
one-way session.

Decision: add an immutable owner self-attestation command. It first requires the
privacy-safe retained-scorecard verifier to pass, requires an explicit accepted
or rejected decision and live-audio judgment, and stores no transcript, scenario,
free-form notes, room, provider error, or credentials. An accepted decision is
invalid when audio is marked unacceptable. The record labels itself as manually
recorded and explicitly excludes customer, payment, and revenue claims.

Verification: seven targeted regressions cover a minimal private record, file
permissions and no overwrite, volumes without hard links, timezone handling,
rejection of failed evidence, accepted/audio consistency, rejected outcomes,
and sanitized CLI output. The full Python suite
and offline preflight must pass before merge. Fixtures do not establish live
audio, replacement durability, owner acceptance, customers, payments, or revenue.

Next executable step: configure LiveKit/OpenAI and persistent `SCORECARD_DIR`,
launch and complete one owner session, replace the worker, verify the retained
scorecard, then personally record the owner decision with the new command.

Rollback: revert the acceptance-record commit. Existing scorecards and any
previously written acceptance records remain untouched.

### 2026-10-26: make worker deployment reproducible without losing evidence

Baseline: `68c251e6e516d699166ef0f5c8d20dd8fd97e467` (merged PR #18).
The static pilot remains deployed, all three repositories have no open work,
and credentialed voice operation remains unavailable in this environment.

Diagnosis: the deployment guide recommended the obsolete
`livekit-cli deploy create` interface and embedded a Dockerfile that was never
checked in. More materially, it paired the worker's local-file scorecards with
a managed deployment whose local storage is ephemeral. That path could not
support the required replacement-retention evidence.

Alternatives: external object/database storage would support managed workers but
requires a new authenticated storage design. For the first owner pilot, use the
smaller existing file-store architecture on a self-hosted worker container with
a named volume while continuing to use LiveKit Cloud for rooms and media.

Decision: check in a non-root worker image, a credential-excluding build context,
and an owner-pilot Compose definition that mounts `difficultai-scorecards` at the
same absolute path configured by `SCORECARD_DIR`. Update deployment commands to
the current `lk agent create` / `lk agent deploy` interface and record a rollback
that preserves the volume.

Verification: three configuration regressions validate the production entrypoint,
unprivileged runtime, credential exclusions, and exact scorecard-volume mapping.
The full Python suite and offline preflight must pass before merge. Docker is not
available in this execution environment, so an image build and container start
remain unverified; no credential, provider request, live audio, replacement,
owner acceptance, customer, payment, or revenue evidence is claimed.

Next executable step: on a Docker host, configure `.env`, build and start
`compose.owner-pilot.yml`, run connectivity preflight inside the worker, then
complete the owner-session/replacement/verification/attestation sequence.

Rollback: restore the prior Docker and Compose files from a known-good commit
and rebuild without deleting the `difficultai-scorecards` volume.

### 2026-10-27: execute the worker image and replacement-volume contract in CI

Baseline: `aba84cd3f1d2f708b7284fde9467cf1f0fa0dd3f` (merged PR #19).
The static pilot remains deployed and all three repositories have no competing
open work. LiveKit/OpenAI credentials remain unavailable here.

Diagnosis: the checked-in Docker and Compose contracts had only source-level
assertions. This environment has no Docker runtime, so neither the production
image nor its named-volume behavior had ever executed. Repeating a local build
was impossible and would not create durable, reviewable evidence.

Alternatives: provision a new Docker host, which adds an unmanaged operational
dependency, or use the repository's existing Linux CI runner. The latter is the
smallest reproducible check and requires no credentials or paid service.

Decision: add a CI gate that builds the exact worker image, asserts it runs as a
non-root user, imports the supported worker CLI, writes a clearly labeled
fixture through the scorecard mount, and reads it from a second container using
the same temporary named volume. The script always removes that test volume.

Verification: the full Python suite, offline preflight, and exact-head CI must
pass. CI is the authoritative image-build evidence because Docker is absent
locally. The volume payload is an internal fixture; it is not a scorecard.

Limitations: this does not prove a deployed worker, provider credentials, live
audio, a real scorecard surviving host or worker replacement, owner acceptance,
customers, verified payment, or revenue.

Next executable step: on the intended Docker host, configure the four required
credentials, start `compose.owner-pilot.yml`, run connectivity preflight, then
complete the owner-session/replacement/verification/attestation sequence.

Rollback: revert the CI verification commit. It affects only tests, workflow,
and documentation and does not alter a deployed worker or retained evidence.

### 2026-10-28: verify the actual Compose deployment path

Baseline: `52846a1df8456ce00e24e88f0c6f5b26eb92c1be` (merged PR #20).
All three repositories have no competing open work, the Vite pilot remains
deployed, and LiveKit/OpenAI credentials remain unavailable here.

Diagnosis: the image CI built the Dockerfile and verified a raw Docker named
volume, but it did not parse or run `compose.owner-pilot.yml`. The operator path
could therefore drift or fail while the lower-level image check stayed green.

Alternatives: keep static string assertions around Compose, or execute the real
service definition without provider I/O. The executable check provides stronger
evidence and can safely use placeholder credentials because offline preflight
makes no service requests.

Decision: make the existing CI verifier create an isolated Compose project,
validate its rendered configuration, build its explicitly tagged worker image,
run the non-root and CLI checks plus offline preflight inside the service, then
write and read a labeled fixture from replacement service containers. Cleanup
deletes only the isolated test volume and never replaces an existing `.env`.

Verification: the full Python suite, offline preflight, shell syntax, and the
exact-head Compose CI job must pass before merge. The stored payload is still an
internal fixture, not a real owner-session scorecard.

Limitations: this does not deploy the worker or verify provider credentials,
live audio, a real scorecard across replacement, owner acceptance, customers,
verified payment, or revenue.

Next executable step: configure the four credentials on the intended Docker
host, start the checked-in Compose service, run credentialed connectivity
preflight, then complete the owner-session/replacement/verification/attestation
sequence.

Rollback: revert the Compose-verification commit. No production container or
retained evidence is created or modified by this CI-only change.

### 2026-10-29: fail closed before starting the owner-pilot worker

Baseline: `1da9a35e5bf9c4cb2ea77052026d26392c46a477` (merged PR #21).
All three repositories have no competing open work, the static pilot remains
deployed, and the four LiveKit/OpenAI credentials are still unavailable here.

Diagnosis: the runbook built and started the long-running Compose worker before
running credentialed connectivity preflight. Invalid or placeholder credentials
could therefore produce a restart-looping service that looked deployed without
passing its minimum reachable operational gate.

Alternatives: rely on the operator to run commands in the right order, or encode
the order in a tested command. The latter makes failure behavior reproducible
and reduces the owner action to one auditable entrypoint.

Decision: add `make owner-pilot-deploy`. It requires a local `.env`, validates
Compose, builds the worker, and runs the existing credentialed LiveKit preflight
inside a one-off service before starting the long-running worker. It then checks
that the service remains running. A failed preflight never starts the worker; a
failed post-start status check stops only the worker and preserves its volume.
Errors remain sanitized and no credential values are read or printed directly.

Verification: regressions cover missing configuration before Docker access,
preflight failure before startup, successful command ordering, and fail-closed
startup/status handling without volume removal. The full Python suite, offline
preflight, and exact-head CI must pass before merge.

Limitations: tests mock the operational command sequence. This does not deploy a
worker or verify real credentials, OpenAI access, live audio, retained session
evidence, owner acceptance, customers, verified payment, or revenue.

Next executable step: put the four credentials in `.env` on the intended Docker
host and run `make owner-pilot-deploy`; only after it passes should the owner
complete the session/replacement/verification/attestation sequence.

Rollback: revert the deployment-gate commit. It does not delete the named volume
or alter previously retained evidence.

### 2026-10-30: make replacement-retention evidence executable

Baseline: `7388df7166eca5b76f8b5702d76d04bf39f6ad2d` (merged PR #22).
All three repositories have no competing open work, the static pilot remains
deployed, and LiveKit/OpenAI credentials remain unavailable here.

Diagnosis: the owner runbook still required manually replacing the worker and
then running the scorecard verifier. A passing post-replacement structure check
did not bind the retained file to the exact private file seen beforehand, and an
operator could accidentally rebuild or remove the volume during the sequence.

Alternatives: document more manual commands, persist a public fingerprint, or
perform the comparison privately in one executable operation. The last option
provides stronger evidence without publishing transcript-derived material.

Decision: add `make owner-pilot-replace SESSION_ID=<id>`. It requires the worker
to be running, verifies the completed scorecard, computes an unprinted SHA-256
fingerprint inside the container, force recreates only the worker without a
build or volume operation, then repeats both checks. The operation passes only
when the worker remains running and the private file fingerprint is unchanged.

Verification: regressions cover invalid IDs before Docker, failed evidence
before replacement, one exact force recreation with no volume-removal command,
changed private evidence without fingerprint disclosure, and a non-running
replacement. The full Python suite, offline preflight, and exact-head CI must
pass before merge.

Review revision: bound every Compose subprocess beyond the configured 15-minute
worker stop grace period, retry post-replacement readiness five times, and read
the scorecard directory from the service environment rather than duplicating
its path. Timeout reports remain sanitized.

Limitations: tests mock the replacement command sequence. This does not deploy a
worker or establish real-session retention, live audio, owner acceptance,
customers, verified payment, or revenue without a credentialed owner run.

Next executable step: deploy with real credentials, complete one owner session,
run the replacement command with its session ID, then personally record the
owner acceptance decision.

Rollback: revert the replacement-verification commit. It adds no persistent
public record and never removes the named scorecard volume.

### 2026-10-30: serialize Vite publication after legacy Pages

Baseline: `0f2b1ec3c3f03c5ad876caca7048dc3771fa0ec4` (merged PR #23).

Diagnosis: the custom Pages run built, deployed, and verified the Vite app, but
GitHub's automatic `pages build and deployment` run completed afterward. A
fresh public fetch then returned the repository Jekyll page (`Difficult AI |
difficultai`) with one stylesheet instead of the Vite app. Two green workflows
therefore did not establish a durable deployment because their writes raced.

Alternatives: change the repository Pages source to GitHub Actions, which needs
an unavailable settings action, or serialize the existing deployments in code.
The smallest reachable repair is to republish Vite after the legacy workflow
completes while retaining push deployment for repositories already configured
for Actions.

Decision: listen for successful completion of `pages build and deployment`,
check out its exact head SHA, rebuild the Pages variant, deploy it, and run the
existing public asset verifier. Failed legacy builds do not trigger deployment.

Verification: a regression locks the workflow name, successful-run gate, and
exact-SHA checkout. Before merge, the full Python suite plus web tests/build and
exact-head PR CI must pass. After merge, the chained deployment must pass and a
fresh public fetch must expose the Vite title and versioned JavaScript/CSS assets.

Limitations: this repairs static publication only. It does not establish a
credentialed worker, live audio, persistent real scorecards, owner acceptance,
customers, verified payment, or revenue.

Next executable step: merge after exact-head CI, wait for both the automatic
Pages run and its chained Vite run, then verify the public app without cache.

Rollback: revert this workflow commit. The prior deployment artifact remains
available in Actions, and no worker, credential, or scorecard is modified.

### 2026-10-30 revision: wait for the dynamic Pages run

Evidence after merging PR #24 invalidated its proposed solution: the automatic
Pages workflow succeeded for merge commit `adf2520f900f1186c317be5daf115e9f16460e34`,
but no `workflow_run` event started the expected follow-up. GitHub represents
this legacy publication as a dynamic workflow, so the trigger was not executable
in this repository.

Decision: remove the ineffective trigger. On each `main` push, the deploy job
uses read-only Actions access to find the matching dynamic run by exact commit
SHA, waits until it is terminal, and only then publishes and verifies Vite. A
30-second discovery bound lets repositories already configured for GitHub
Actions proceed; a five-minute completion bound fails closed instead of racing.

Verification: Node regressions cover waiting for the exact dynamic run, ignoring
another commit, the dormant/no-run path, and API failure. The parsed workflow
regression requires read-only Actions permissions and the wait step. After merge,
both publications must finish, the push deployment must finish last, and a fresh
public fetch must expose Vite's title and JavaScript/CSS assets.

Limitations and next step remain unchanged for the voice pilot: this deployment
repair does not verify credentials, live audio, persistent real scorecards, or
owner acceptance. After static verification, run the credentialed owner pilot.

Rollback: revert the serialization commit to restore the prior deployment
behavior; this touches no credentials, workers, or retained scorecards.

### 2026-10-30: bind owner evidence to the deployed revision

Baseline: `3ae9b4745aee7ec6c10e546a4bf2b581c80482a1` (merged PR #25).
The Vite pilot is deployed and verified, no open work exists across the three
Repo Rescue repositories, and the four voice credentials and Docker remain
unavailable in this environment.

Diagnosis: the worker image, retained scorecard, and owner attestation carried
no source revision. Replacement could prove that the same private file survived,
but could not prove which code produced it. A successful build or static deploy
does not close that operational evidence gap.

Alternatives: rely on a mutable image tag or ask the operator to write down a
commit. The smaller reliable change is to derive the exact Git HEAD in the
deployment gate, reject dirty or unidentified checkouts, pass the revision as a
build argument and runtime value, and verify it inside the started worker.

Decision: record the validated 40-character revision in every new scorecard.
The privacy-safe verifier and owner attestation now require and retain that
public revision, while continuing to omit rooms, scenarios, and transcripts.
The Compose image CI also builds and checks the exact workflow revision.

Verification: regressions first reproduced an unbound scorecard being accepted
and an unversioned deploy path. All 108 Python tests, offline preflight, shell
syntax, and diff checks pass locally. Exact-head CI must pass before merge.

Review revision: normalize the runtime revision once, sanitize missing-Git
errors, validate the CI revision and clean checkout before Compose, and preserve
a specific revision-mismatch diagnosis while stopping the worker. Compose and
the Dockerfile already pass the revision into the built and running service.

Limitations: no worker was deployed and no credentials, provider access, live
audio, real scorecard, replacement retention, or owner acceptance was verified.

Next executable step: merge after exact-head CI, then on the intended Docker
host deploy the clean merged revision with real credentials and complete one
owner session, replacement check, and acceptance record.

Rollback: revert this provenance commit and rebuild the worker without deleting
the named scorecard volume. Previously saved scorecards remain untouched but
will not pass the stricter revision-bound acceptance gate.

### 2026-10-31: bind replacement proof to the worker revision

Baseline: `2a2f7876dadb6f2e0993651b838a8a109636b933` (merged PR #26).
The latest main Python/image and serialized Vite workflows passed. RepoMan and
make_my_day remain at `eac812e` and `d198eac`, with no open work across the three
repositories. Docker and the four voice credentials remain unavailable here.

Diagnosis: the replacement command validated the scorecard's new source revision
only indirectly, then compared the private file fingerprint. It never checked
the running container's `DIFFICULTAI_BUILD_SHA`. A stale or retagged image could
therefore be recreated and still produce a successful retention message.

Alternatives: trust the Compose tag, print revisions for manual comparison, or
perform the comparison privately inside the existing operation. The last option
is the smallest safe extension and does not expose transcript-derived material.

Decision: parse the verifier's sanitized JSON, require its exact source revision,
and compare it with the running worker environment before and after the forced
recreation. A mismatch fails immediately without printing either revision. The
existing unprinted file fingerprint must still remain identical.

Review revision: use a typed terminal integrity failure instead of message-text
matching, normalize absent subprocess output, and extract the verifier's JSON
object without assuming that stdout contains no harmless wrapper lines.

Verification: regressions reproduce false passes for both pre- and post-replace
revision mismatches, plus malformed, wrapped, missing, or null subprocess output.
All 114 Python tests and the offline preflight pass on the revised head. Exact-head
CI must pass before merge.

Limitations: mocked command sequencing does not deploy a worker or establish
credentials, provider access, live audio, real-session storage retention, owner
acceptance, customer activity, payment, or revenue.

Next executable step: after merge, deploy the exact clean main revision on the
intended Docker host, complete one real owner session, run the bound replacement
check, and record the owner's separate acceptance decision.

Rollback: revert this repair. It changes no image, scorecard, transcript, volume,
or acceptance record and never invokes a volume-removal command.

### 2026-11-01: require durable replacement evidence before owner acceptance

Baseline: `89e375ae428a64ffcd05c65083633f8e37f315d9` (merged PR #27).
All three repositories have no competing open work. The static pilot workflows
are green; Docker and the four voice credentials remain unavailable here.

Diagnosis: the replacement command proved revision-bound retention only in its
terminal output. `record-owner-acceptance` independently rechecked the scorecard
but did not require durable evidence that replacement had occurred. An operator
could therefore skip the required replacement and still create an attestation.

Alternatives: trust command history, add a manual confirmation flag, or retain a
private receipt on the existing scorecard volume. The receipt provides the
strongest executable link without publishing transcript-derived material.

Decision: after a successful replacement comparison, write one immutable mode
`0600` receipt bound to the session ID, source revision, private scorecard SHA-256,
and UTC time. Owner acceptance now rejects missing, malformed, mismatched, or
stale receipts and records that replacement verification passed. Neither command
prints the private fingerprint, transcript, scenario, provider error, or path.

Verification: regressions cover immutable and hard-link-free volume writes,
revision mismatch, scorecard mutation after replacement, sanitized CLI output,
receipt-command failure, and acceptance without a receipt. The full Python suite,
offline preflight, and exact-head CI must pass before merge.

Review revision: fsync the receipt's parent directory after exclusive publication,
require the receipt subprocess's sanitized success response to bind the expected
session and revision, and validate acceptance arguments before evidence I/O.

Limitations: the receipt is locally recorded operational evidence, not an
independent audit. Mocked command sequencing does not deploy a worker or establish
credentials, live audio, real retention, owner acceptance, customers, payment,
or revenue.

Next executable step: deploy exact clean main on the intended Docker host with
the four credentials, complete one real owner session, run
`make owner-pilot-replace SESSION_ID=<id>`, then record the owner's decision.

Rollback: revert this repair. Existing receipts and scorecards remain private on
the named volume; the prior acceptance path will no longer require a receipt.

### 2026-11-02: make the retained acceptance chain re-verifiable

Baseline: `71590267cf85463bc25a297f760c14f166f7baa1` (merged PR #28).
Its Python, image, serialized Vite, and Pages workflows passed. No competing PR
or issue exists across DifficultAI, RepoMan, or make_my_day. Docker and the four
voice credentials remain unavailable in this environment.

Diagnosis: the operator could create a revision-bound scorecard, immutable
replacement receipt, and owner attestation, but there was no single executable
check that those three retained artifacts still agreed. Later reporting could
therefore rely on stale or internally inconsistent acceptance evidence.

Alternatives: document manual file inspection, extend the public static app, or
add a private local verifier beside the existing evidence commands. The local
verifier is the smallest safe change and avoids publishing session material.

Decision: add `make verify-owner-acceptance SESSION_ID=<id>`. It fails closed on
scorecard or replacement changes, mismatched identity/revision, impossible
decision and audio combinations, false evidence flags, or timestamps that do
not match the replacement receipt and precede the attestation. Output contains
only the session ID, public revision, decision, named checks, and limitations.
Acceptance creation now also rejects a timestamp before replacement.

Verification: focused regressions cover a valid chain, missing acceptance,
tampered judgment and chronology, changed private scorecards, sanitized CLI
output, and invalid IDs before path access. The full suite, offline preflight,
and exact-head CI must pass before merge.

Review revision: bound acceptance reads to 64 KiB, treat unexpected malformed
replacement types as sanitized failures, and stop before surfacing a decision
when the attestation identity does not match the requested session and revision.

Limitations: this verifies locally retained evidence, not a deployed worker or
independent audit. No credentials, live audio, real scorecard, replacement,
owner acceptance, customer activity, payment, or revenue were established.

Next executable step: after merge, deploy exact clean main on the intended
Docker host with all four credentials; complete one owner session, replacement,
and decision; then run the new verifier against that retained session.

Rollback: revert this repair. It reads but does not modify existing evidence;
the earlier recording commands and private artifacts remain intact.

### 2026-11-03: exercise the acceptance chain on the Compose volume

Baseline: `ed1db48654e704e975a509c1dca308539d9ded14` (merged PR #29).
Its Python/image and both Pages workflows passed. DifficultAI, RepoMan, and
make_my_day have no competing open PR or issue. Docker and the four voice
credentials remain unavailable in this execution environment.

Diagnosis: image CI proved only that a generic marker file remained visible to
two containers. It never exercised the required scorecard, immutable replacement
receipt, owner attestation, and final verifier through the configured Compose
volume. Unit tests therefore covered evidence logic while deployment CI covered
only shallow storage wiring.

Alternatives: leave the layers independently tested, add another host-only unit
test, or rehearse the private evidence chain in separate image containers. The
Compose rehearsal gives the strongest credential-free deployment evidence and
uses the existing isolated fixture volume and cleanup path.

Decision: after image and offline checks, create a revision-bound internal
scorecard fixture in one container, record its replacement receipt in a second,
record an explicit fixture acceptance in a third, and verify the complete chain
in a fourth. The script labels the result as an internal fixture and deletes its
isolated volume during cleanup.

Verification: the deployment regression requires scorecard creation, all three
evidence commands, the fixture label, and non-TTY stdin forwarding. Local Python
tests, offline preflight, shell syntax, and exact-head image CI must pass before
merge.

Review revision: disable pseudo-TTY allocation for the heredoc container so CI
forwards the fixture deterministically, and assert the specific scorecard and
evidence commands instead of coupling the regression to a raw run-count total.

Limitations: this is an internal deterministic fixture. It does not deploy the
long-running worker or establish credentials, provider access, live audio, a
real scorecard, actual replacement, owner acceptance, customer activity,
payment, or revenue.

Next executable step: after merge, deploy exact clean main on the intended
Docker host with the four credentials, complete the real owner workflow, and
run `make verify-owner-acceptance SESSION_ID=<id>` against its retained volume.

Rollback: revert this CI rehearsal. It creates and removes only the isolated CI
Compose project and volume; production images and private evidence are untouched.

### 2026-11-04: make the deployment blocker executable before build

Baseline: `de66f8e06d24489bcda01f6302734e70aaf8dd44` (merged PR #30).
Its Python/image and both Pages workflows passed. DifficultAI, RepoMan, and
make_my_day have no competing open PR or issue. This environment still has no
Docker executable or four voice credentials, so a real worker deployment cannot
be attempted here.

Diagnosis: `owner-pilot-deploy` fails closed, but the operator had no read-only
command that reported all host prerequisites before a potentially expensive
image build. The checked-in evidence therefore could not turn the known generic
"Docker host plus credentials" blocker into a precise, repeatable handoff.

Alternatives: repeat the written checklist, add provider probes, or add a local
readiness gate. Provider probes need secrets and service I/O; the local gate is
the smallest safe change and can validate the exact host without deploying.

Decision: add `make owner-pilot-ready`. It checks a clean source revision,
credential names and LiveKit URL shape without printing values, Docker Engine
and Compose reachability, and Compose rendering. It never builds, starts, stops,
or contacts providers, and its report states the deployment and acceptance
boundaries.

Verification: regressions reproduce the present missing `.env`/Docker blockers,
missing credential names, a dirty checkout, and invalid Compose; the passing
fixture requires every prerequisite. The full Python suite, offline preflight,
and exact-head CI must pass before merge.

Review revision: bound Docker and Compose probes to 30 seconds, map Git/Docker
subprocess failures to sanitized checks, and lock process-environment precedence
to Docker Compose semantics with a regression.

Limitations: readiness does not validate credentials, build or deploy a worker,
contact LiveKit/OpenAI, exercise live audio, retain a real scorecard, establish
owner acceptance, customer activity, payment, or revenue.

Next executable step: on the intended Docker host, run
`make owner-pilot-ready`, correct only the named blockers, then run
`make owner-pilot-deploy` and complete the real owner workflow.

Rollback: revert this readiness command and documentation. It reads local state
only and creates, changes, starts, or removes no credential, image, service,
volume, or evidence file.

### 2026-11-05: gate deployment on Pages artifact visibility

Baseline: `fb59dd838c75610d6fe57d263e2b2e9b28f92bd9` (merged PR #31).
Its Python/image workflow and the separate legacy Pages publication passed, but
the custom Vite deployment failed while GitHub's Pages API returned HTTP 500.
One targeted failed-job rerun a day later exposed a different deterministic
failure: the build job passed and uploaded `github-pages`, while the dependent
deploy job immediately listed zero artifacts and stopped before publication.

Diagnosis: job dependency completion does not guarantee that the Actions
artifact-list API already exposes the completed upload. `deploy-pages` performs
its artifact lookup once, so an otherwise valid rerun can fail during this
short visibility window.

Alternatives: keep rerunning an unchanged deployment, add an unbounded sleep,
or poll the exact run for its named artifact. Repeated reruns do not remove the
race and a fixed sleep cannot prove readiness. Polling the existing read-only
Actions API is bounded, specific, and preserves the current architecture.

Decision: before `deploy-pages`, wait up to 60 seconds for a non-expired
`github-pages` artifact belonging to the current workflow run. Retry empty
lists, rate limits, and server errors; fail closed on permanent API errors,
malformed responses, or timeout. The gate logs only the public artifact ID.
Each request receives an abort signal for the remaining overall budget, and
network and JSON failures are reported without raw intermediary details.

Verification: web component tests, 14 Node deployment regressions, the
Pages-mode production build, the full Python suite, offline preflight, and
exact-head PR CI must pass. After merge, the custom workflow must publish and
public verification must pass before the Vite app is called deployed.

Limitations: this closes artifact visibility only. It does not prevent a later
GitHub Pages service error or establish a credentialed worker, live audio,
retained real scorecard, owner acceptance, customer activity, payment, or
revenue.

Next executable step: merge only after exact-head CI and review, then verify the
post-merge custom Pages run and public Vite assets. Independently, the owner
pilot still requires the intended Docker host and four voice credentials.

Rollback: revert this repair to remove the read-only visibility gate. It does
not modify Pages settings, artifacts, deployments, credentials, or evidence.

### 2026-11-06: make an interrupted owner workflow resumable

Baseline: `27ad6e8323082ef39ab16e2c71d49edc924d6e32` (merged PR #32).
Its Python/image, serialized Vite, and legacy Pages workflows passed. DifficultAI,
RepoMan, and make_my_day have no open PR or issue. The static pilot is deployed
and verified, while the credentialed voice worker and real owner session remain
unrun in this environment.

Diagnosis: the operator path has strong gates for each individual stage, but no
single read-only command identifies where a specific interrupted session should
resume. The evidence Make targets also ran on the host even though deployed
evidence is retained only in the Compose volume at `/data/scorecards`. An
operator could inspect the wrong directory, repeat an immutable evidence write,
skip replacement, or mistake a missing future artifact for invalid evidence.

Alternatives: rely on the written runbook, combine all mutating steps into one
command, or add a read-only state inspector. The inspector is the smallest safe
change: human judgment remains separate, existing commands remain authoritative,
and no provider or deployment action occurs.

Decision: add `make owner-pilot-status SESSION_ID=<id>`. It validates the session
ID before path access, distinguishes absent future stages from invalid or
inaccessible existing evidence, reuses the scorecard, replacement, and acceptance
verifiers, and emits the exact next command or decision step. Status, scorecard
verification, acceptance recording, and final verification now execute inside
the running worker so they share its retained Compose volume. Output excludes
transcripts, scenarios, fingerprints, credential values, and private paths.

Verification: regressions cover invalid IDs, missing sessions, scorecard-ready,
replacement-ready, fully verified, corrupt or inaccessible evidence, sanitized
CLI output, and Compose-volume routing for all evidence commands. The full Python
suite, offline preflight, and exact-head CI must pass before merge.

Limitations: the status command is a local evidence navigator, not a deployment,
provider test, live-audio result, independent audit, customer acceptance, payment,
or revenue claim.

Next executable step: after merge, deploy exact clean main on the intended Docker
host with the four voice credentials. After the first real session, run the new
status command after each stage until the retained acceptance chain verifies.

Rollback: revert this command and documentation. It is read-only and creates,
changes, starts, stops, or removes no credential, worker, volume, or evidence.

### 2026-11-07: bound every owner-pilot deployment stage

Baseline: `9614c284c14fbfe07a656140c96231400bdccabe` (merged PR #33).
DifficultAI, RepoMan, and make_my_day have no open PR or issue. The static pilot
remains the only verified deployment; this environment still lacks the intended
Docker host and four voice credentials.

Diagnosis: readiness and replacement subprocesses have explicit deadlines, but
`owner-pilot-deploy` could wait forever during Compose validation, image build,
credentialed preflight, startup, status, revision verification, or cleanup. A
stalled provider or Docker daemon therefore left the operator without a bounded
failure or a reliable next action.

Alternatives: rely on external shell timeouts, apply one deadline to the whole
deployment, or bound each stage. Per-stage limits preserve a realistic image
build window while failing faster for validation and runtime checks, and they
identify the stalled stage without exposing command output or credentials.

Decision: give every deployment and cleanup subprocess a stage-specific timeout.
Convert timeout and process-start failures into sanitized `DeploymentError`
messages. A timeout before startup never starts the worker; a timeout during or
after startup still attempts a separately bounded worker stop and never removes
the persistent scorecard volume.

Verification: regressions must prove credentialed-preflight timeout prevents
startup, startup timeout invokes bounded cleanup, all successful subprocesses
receive a positive deadline, and existing ordering and volume-preservation tests
continue to pass. The full Python suite, offline preflight, exact-head CI, and
review must pass before merge.

Limitations: timeouts do not validate credentials, deploy from this environment,
exercise live audio, create a real scorecard, establish owner acceptance, or
prove customer activity, payment, or revenue.

Next executable step: after merge, run `make owner-pilot-ready` and
`make owner-pilot-deploy` from a clean checkout on the intended Docker host with
the four configured credentials, then complete one real owner workflow.

Rollback: revert this change to restore unbounded subprocess waits. No credential,
worker, volume, deployment, or private evidence is created by this repair.

### 2026-11-08: make owner-session use the documented credentials

Baseline: `ab118615008873b6f427eed67c6df6b4690455e9` (merged PR #34).
Its Python/image and both Pages workflows passed. DifficultAI, RepoMan, and
make_my_day have no open PR or issue. The static pilot remains deployed, while
the credentialed voice worker and real owner workflow remain unrun here.

Diagnosis: readiness and Compose deployment read credentials from the project
`.env`, but `make owner-session` passed only the shell process environment to its
LiveKit client. Following the documented setup exactly could therefore deploy a
configured worker and then fail the first owner-room command unless the operator
also exported the same secrets manually.

Alternatives: require an undocumented shell export, run session creation inside
the worker and copy the host scenario into it, or load project configuration in
the existing host command. Loading `.env` is the smallest change and matches the
precedence already used by readiness and Docker Compose.

Decision: load project `.env` for owner-session without mutating `os.environ`.
Explicit process values continue to override file values. Missing or invalid
configuration still fails before provider I/O, and credential values remain out
of errors and checked-in evidence.

Verification: regressions prove `.env` works without exported credentials and
that explicit process values win. Existing token scope, scenario validation,
provider-error sanitization, the full Python suite, offline preflight, exact-head
CI, and review must pass before merge.

Limitations: this aligns configuration only. It does not validate credential
values here, deploy the worker, contact LiveKit in tests, exercise live audio,
create retained real evidence, establish owner acceptance, or prove customer
activity, payment, or revenue.

Next executable step: after merge, use a clean checkout on the intended Docker
host, configure `.env`, run readiness and deployment, then run
`make owner-session SCENARIO=<private-json-path>` without separately exporting
the credentials.

Rollback: revert this loader and documentation. It creates no credential,
session, worker, volume, deployment, or evidence by itself.

### 2026-11-09: bound the first credentialed room request

Baseline: `4231c1552ffa48611dca30d366851784874b8104` (merged PR #35).
Its Python/image and both Pages workflows passed. DifficultAI, RepoMan, and
make_my_day have no open PR or issue. The static pilot remains deployed, while
the credentialed voice worker and real owner workflow remain unrun here.

Diagnosis: deployment subprocesses have explicit deadlines, but the host-side
`owner-session` command could wait forever while opening its LiveKit client or
creating the first room. A stalled provider connection therefore left the
operator without a bounded failure or reliable retry decision.

Alternatives: rely on an external shell timeout, expose a new operator-tunable
deadline, or enforce one conservative application deadline around the existing
provider context. The fixed application deadline is the smallest safe repair:
it covers connection, request, and cleanup without expanding configuration.

Decision: allow 30 seconds for the LiveKit client context and room request.
On timeout, cancel the provider task, close its context, and return a sanitized
actionable error without provider details or credentials. Token and scenario
validation behavior remains unchanged.

Verification: a regression must prove a non-returning room request is cancelled,
the provider context exits, and the caller receives the sanitized timeout. The
full Python suite, offline preflight, exact-head CI, and review must pass before
merge.

Limitations: this bounds one provider operation only. It does not validate real
credentials here, deploy the worker, exercise live audio, create retained real
evidence, establish owner acceptance, or prove customer activity, payment, or
revenue.

Next executable step: after merge, use a clean checkout on the intended Docker
host with the four configured credentials, run readiness and deployment, then
create one real owner session and follow the retained-evidence status workflow.

Rollback: revert this timeout and regression to restore the unbounded provider
wait. This repair itself creates no credential, session, worker, volume,
deployment, or evidence.

### 2026-11-10: require both providers before worker startup

Baseline: `3af053b9d453b1074590c4a618cdfb6189533279` (merged PR #36).
Its Python/image and both Pages workflows passed. DifficultAI, RepoMan, and
make_my_day have no open PR or issue. The static pilot remains deployed, while
the credentialed voice worker and real owner workflow remain unrun here.

Diagnosis: the deployment gate required an OpenAI key but authenticated only to
LiveKit before starting the worker. An expired, revoked, or unreachable OpenAI
account could therefore pass readiness and fail only after an owner joined.

Alternatives: leave OpenAI validation to the first live session, generate a test
response during deployment, list models, or open the worker's transport without
sending content. A bounded Realtime handshake is the closest safe check: it
matches the worker's model and permission scope without generating content.

Decision: credentialed preflight now performs independent, ten-second-bounded
LiveKit room listing and OpenAI `gpt-realtime` WebSocket handshake checks. Either failure blocks
worker startup, reports only the exception type and an actionable provider-specific
next step, and retains the existing private preflight report.

Verification: regressions must prove OpenAI success is required, failure details
are sanitized, a hung request is cancelled, and the client context closes. The
full Python suite, offline preflight, exact-head CI, and review must pass before
merge.

Limitations: the Realtime handshake proves authentication and transport access,
not model generation, live audio, interruption handling, retained real evidence,
owner acceptance, customer activity, payment, or revenue.

Next executable step: after merge, deploy clean main on the intended Docker host
with the four configured credentials. The gate must pass both providers before
startup; then complete one real owner session and retained-evidence workflow.

Rollback: revert this provider check and regressions to restore LiveKit-only
deployment preflight. This repair itself creates no content, session, worker,
volume, deployment, or evidence.

### 2026-11-11: minimize browser retention of the owner access token

Baseline: `534b7a99c63d23ea1ca4525784b6ce8041c77e8e` (merged PR #37).
Its Python/image and both Pages workflows passed. DifficultAI, RepoMan, and
make_my_day have no open PR or issue. The static pilot remains deployed, while
the credentialed voice worker and real owner workflow remain unrun here.

Diagnosis: the direct-connect form rendered the short-lived LiveKit JWT in a
plain textarea and retained it in React state after handing it to the SDK. A
screen observer could read it, and returning to the form after a failed or
cancelled attempt exposed the stale credential again.

Alternatives: remove direct connection, retain the token for convenient retries,
or mask it and clear application state as soon as connection begins. Masking and
immediate clearing preserve the existing owner workflow while reducing browser
credential exposure and avoiding a stale asynchronous attempt clearing a newer
token.

Decision: use a password input that requests a non-reused browser value and has
spellcheck disabled, and tell the operator that retries require pasting again.
After non-empty fields validate, snapshot the trimmed token for the one SDK call
and synchronously clear React state before any asynchronous provider work.

Verification: regressions must prove masking and clearing after rejected and
cancelled connections. The web unit suite, production build, exact-head CI, and
review must pass before merge.

Limitations: JavaScript and the LiveKit SDK still hold the token while connecting
and as required for the active room. This does not deploy the voice worker,
validate credentials, exercise live audio, verify persistent evidence, establish
owner acceptance, or prove customer activity, payment, or revenue.

Next executable step: after merge and Pages deployment, use clean main on the
intended Docker host, pass both provider preflights, create one short-lived owner
token, and complete one real owner session plus retained-evidence verification.

Rollback: revert this UI and regression change to restore visible, retained token
entry. No credential, provider request, session, worker, or evidence is created
by this repair.

### 2026-11-12: discover the retained owner session safely

Baseline: `ff799f657416b4a340dfad6b9666b4ff4b9fc7e2` (merged PR #38).
Its exact-head and post-merge Pages workflows passed, and the deployed token
field was verified. DifficultAI, RepoMan, and make_my_day have no open PR or
issue. The voice worker and real owner workflow remain unrun here.

Diagnosis: every post-session durability and acceptance command requires the
worker's 32-character session ID, but the runbook only told the operator to
retain it. After a real call, the durable source is the private scorecard volume;
recovering the ID otherwise requires parsing logs or inspecting private storage.

Alternatives: document a log command, print the ID in the browser, list every
retained session, or discover only the newest scorecard through the deployed
worker. Newest-session discovery is the smallest handoff: it keeps private
evidence inside the container and feeds the existing status verifier.

Decision: add `make owner-pilot-latest`. It scans only regular files matching
`scorecard_<32 lowercase hex>.json`, selects the newest by filesystem timestamp,
and returns the existing privacy-safe stage and exact next command. Unrelated
files and symlinks are ignored; missing evidence is incomplete, while inaccessible
storage blocks progress with a sanitized result.

Verification: regressions cover empty storage, deterministic newest selection,
unrelated and symlinked files, inaccessible storage, sanitized CLI output, and
Compose-volume routing. The full Python suite, offline preflight, exact-head CI,
worker-image rehearsal, and review must pass before merge.

Limitations: filesystem recency identifies the newest saved scorecard, not the
operator's intended session. This does not deploy the worker, validate providers,
exercise live audio, create real evidence, establish owner acceptance, or prove
customer activity, payment, or revenue.

Next executable step: after merge, deploy clean main on the credentialed Docker
host, complete one owner session, run `make owner-pilot-latest`, and follow its
reported replacement and acceptance steps until the retained chain verifies.

Rollback: revert this command, regressions, and documentation. It is read-only
and creates, changes, or removes no credential, session, worker, volume, or
evidence.

### 2026-11-13: recover retained evidence without a running worker

Baseline: `bbcaac57114d912b6f98812cad81a3a8b6eac49a` (merged PR #39).
Its exact-head Python and worker-image jobs passed. DifficultAI, RepoMan, and
make_my_day have no open PR or issue. The static pilot remains deployed, while
the credentialed voice worker and real owner workflow remain unrun here.

Diagnosis: every volume-backed status and evidence command used `docker compose
exec`. If the worker stopped after a failed or completed owner session, the
named scorecard volume could remain intact while the operator lost access to
latest-session discovery, verification, and acceptance recording.

Alternatives: require the operator to restart the worker, inspect the volume
manually, add a separate recovery service, or use the production image in a
removable one-shot container attached to the existing volume. The one-shot path
is smallest and matches the existing image rehearsal without starting the voice
worker or contacting providers.

Decision: route status, scorecard verification, acceptance recording, and final
verification through `docker compose run --rm --no-deps -T worker`. Keep actual
worker replacement on the guarded running-service path. Extend image CI to
prove latest-session status both after the scorecard fixture is created and
after its complete internal acceptance chain, without starting the service.

Verification: Makefile contract regressions, the full Python suite, offline
preflight, exact-head CI, the worker-image recovery rehearsal, and review must
pass before merge.

Limitations: local Docker is unavailable in this execution environment, so the
container recovery path must be established by exact-head CI. One-shot commands
still require the built production image, Compose file, `.env`, and accessible
named volume. This does not deploy the worker, exercise live audio, create real
evidence, establish owner acceptance, or prove customer activity, payment, or
revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host, deploy the worker, complete one owner session, stop the worker deliberately,
and run `make owner-pilot-latest` before continuing the replacement and owner
acceptance chain.

Rollback: revert the Makefile, image rehearsal, regressions, and documentation
to restore running-worker-only evidence access. No credential, provider request,
session, worker, volume, or evidence is created by this repair itself.

### 2026-11-14: decouple evidence recovery from provider credentials

Baseline: `4bb11649fd48f7b96030b4c7181062cac7a7113b` (merged PR #40).
Its exact-head Python and worker-image recovery jobs passed. DifficultAI,
RepoMan, and make_my_day have no open PR or issue. The static pilot remains
deployed, while the credentialed voice worker and real owner workflow remain
unrun here.

Diagnosis: stopped-worker recovery still invoked the worker service definition.
That service requires `.env`, so missing or rotated LiveKit/OpenAI credentials
could block access to an otherwise intact private scorecard volume even though
status and acceptance verification make no provider requests.

Alternatives: require placeholder credentials, make the production worker's
environment file optional, export the volume to the host, or define a separate
evidence service. A separate service keeps the production startup contract
strict while giving recovery the minimum runtime capabilities.

Decision: add `compose.owner-evidence.yml` using the deployed image and the same
project-scoped named volume, with no `env_file`, no network, a read-only root
filesystem, and bytecode writes disabled. Route volume-backed status and
acceptance commands through that service with an explicit empty Compose env
file. Extend image CI to create evidence through the worker definition and read,
advance, and verify it through the isolated evidence definition.

Verification: configuration regressions must prove the evidence service has no
credential file or network and shares the scorecard volume. The full Python
suite, offline preflight, shell syntax, exact-head worker-image rehearsal, and
review must pass before merge.

Limitations: local Docker is unavailable here, so exact-head CI must prove the
cross-file Compose volume contract. Recovery still requires the previously built
image, Compose, and the intact named volume. This does not deploy the worker,
exercise live audio, create real evidence, establish owner acceptance, or prove
customer activity, payment, or revenue.

Next executable step: after merge, deploy clean main on the credentialed Docker
host, complete one owner session, stop the worker, temporarily remove `.env`,
and run `make owner-pilot-latest` before restoring credentials and completing
the replacement and acceptance chain.

Rollback: revert the evidence Compose file, Makefile routing, image rehearsal,
regressions, and documentation. This restores credential-dependent recovery but
does not change or delete any retained volume or evidence.

### 2026-11-15: bound isolated evidence commands

Baseline: `ecac1d66970bdc3620d60004a5acccbe4a23b7d5` (merged PR #41).
Its exact-head Python and worker-image jobs passed. DifficultAI, RepoMan, and
make_my_day have no open PR or issue. The static pilot remains deployed, while
the credentialed voice worker and real owner workflow remain unrun here.

Diagnosis: the deployment and replacement paths have subprocess deadlines, but
every recovery command invoked `docker compose run` directly. A stalled Docker
daemon, image lookup, or container command could therefore block the owner at a
recovery or acceptance gate indefinitely.

Alternatives: require an external shell `timeout`, duplicate deadline handling
in each Make target, configure only application-level timeouts, or add one
host-side wrapper for the isolated evidence service. A wrapper is portable
across the existing Python-supported hosts, centralizes the allowlist and error
redaction, and leaves the evidence modules and Compose isolation unchanged.

Decision: add a strict four-module wrapper with a two-minute subprocess
deadline. Route every volume-backed evidence Make target through it. Preserve
only command stdout, which is already covered by privacy-safe module contracts,
and replace Docker start, timeout, and stderr details with sanitized guidance.
Name each one-off container and make one bounded force-removal attempt after a
timeout. Exercise the same wrapper in the worker-image recovery rehearsal, and
preserve its exit status before parsing the privacy-safe JSON assertion.

Verification: regressions must prove the exact credential-free, network-disabled
Compose command, allowlisted module mapping, deadline, timeout redaction, and
Docker-stderr suppression. The full Python suite, offline preflight, shell
syntax, exact-head worker-image rehearsal, and review must pass before merge.

Limitations: the deadline bounds the local Docker client invocation; it cannot
repair a failed daemon or prove provider connectivity. Local Docker is
unavailable here, so exact-head CI must exercise the container path. This does
not deploy the worker, exercise live audio, create real evidence, establish
owner acceptance, or prove customer activity, payment, or revenue.

Next executable step: after merge, deploy clean main on the credentialed Docker
host, complete one owner session, stop the worker, and run `make
owner-pilot-latest`. Follow its reported replacement and acceptance steps while
retaining the private scorecard volume.

Rollback: revert the wrapper, Makefile routing, image rehearsal, regressions,
and documentation to restore direct unbounded evidence commands. No credential,
provider request, session, worker, volume, or evidence is created or changed by
this repair itself.

### 2026-11-16: bind owner-session creation to the deployed worker

Baseline: `915056158bd9b81b318449d11cb3be9e3d7a2cc4` (merged PR #42).
Its post-merge Python, worker-image, custom Pages, and GitHub Pages workflows
passed. DifficultAI, RepoMan, and make_my_day have no open PR or issue. The
static pilot is deployed, while the credentialed voice worker and real owner
workflow remain unrun here.

Diagnosis: `make owner-session` validated its scenario and credentials, then
created a LiveKit room and bearer token without checking the worker. A stopped
worker or one built from another commit would leave the owner with credentialed
provider state that could not produce the intended exact-revision pilot.

Alternatives: rely on runbook ordering, call the full deploy command every time,
start the worker automatically, or add a read-only gate to the session launcher.
The read-only gate is smallest: it preserves deployment policy and makes no
provider request when the worker is absent or stale.

Decision: before constructing a token or contacting LiveKit, require a clean Git
checkout, a running Compose `worker` service, and an embedded
`DIFFICULTAI_BUILD_SHA` equal to the current 40-character commit. Bound both
Docker checks to 30 seconds, suppress raw Docker output, and return only
sanitized repair guidance.

Verification: regressions must prove the gate orders status before exact-revision
verification, carries the source revision into Compose interpolation, blocks a
stopped or stale worker before provider I/O, and rejects a dirty checkout before
Docker. The first exact-head CI run exposed a stale readiness import of the
renamed private revision helper that local test import order had masked. Move
that caller to the public helper, retain the private alias for compatibility,
and prove the readiness test passes alone. Preserve the host environment when
adding test overrides so Docker discovery and host configuration still work.
The full Python suite, offline preflight, exact-head CI, and review must pass
before merge.

Limitations: substituted Docker responses establish command ordering and
fail-closed behavior locally; they do not deploy a worker or validate provider
credentials. This change does not exercise live audio, create a real scorecard,
establish owner acceptance, or prove customer activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host, run `make owner-pilot-deploy`, then run `make owner-session
SCENARIO=<private-json-path>` and complete one retained evidence and acceptance
chain.

Rollback: revert the owner-session gate, regressions, and documentation to
restore unguarded room and token creation. No credential, provider request,
session, worker, volume, or evidence is created by this repair itself.

### 2026-11-17: require bounded regular scorecard evidence

Baseline: `5a22d4a321942fa3f9c81ed0309f036f9c41cc94` (merged PR #43).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. The static pilot remains deployed;
the credentialed worker, live session, retained real scorecard, and owner
acceptance remain unverified here.

Diagnosis: explicit scorecard verification followed a final symlink and read
the entire target without a size limit. A substituted valid JSON file outside
the retained evidence directory passed the verifier, weakening the evidence
anchor used before replacement and owner acceptance. A malformed very large
file could also consume unbounded memory.

Alternatives: rely only on the existing latest-session discovery check, reject
symlinks with `lstat`, copy scorecards before verification, or open a bounded
regular file without following the final symlink. The bounded descriptor-based
read is smallest and also closes the check/open race for the selected file.

Decision: accept only a regular scorecard no larger than 4 MiB. Check both the
path metadata and opened descriptor, use `O_NOFOLLOW` where available, and read
at most one byte beyond the limit before JSON parsing. Keep all failure output
sanitized.

Verification: reproduce the former false pass with a valid external scorecard
symlink, then require regressions for symlink and oversized-file rejection.
Run the focused evidence suites, full Python suite, offline preflight, exact-head
CI, and review before merge.

Limitations: this validates local file type and size, not independent custody or
the truth of transcript content. It does not deploy the worker, exercise live
audio, create real evidence, establish owner acceptance, or prove customer
activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host, run `make owner-pilot-ready`, deploy the worker, and complete one live
owner session plus retained replacement and acceptance verification.

Rollback: revert the bounded scorecard reader, tests, and documentation to
restore the previous unbounded symlink-following verifier. This repair reads
only test fixtures and creates no provider, deployment, or production state.

### 2026-11-18: apply regular-file custody to the full evidence chain

Baseline: `5da08d7fcb64f12215a78ba8bbe616f4671a4ed7` (merged PR #44).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. No checked-in evidence shows a new
credentialed worker deployment or real owner session.

Diagnosis: the scorecard now has a bounded regular-file gate, but replacement
and owner-acceptance verifiers still followed final symlinks. Moving each valid
artifact outside the private evidence directory and substituting a symlink left
both replacement and complete acceptance verification at `passed`.

Alternatives: rely on the scorecard as the only custody anchor, duplicate file
checks in both verifiers, embed all evidence in one file, or reuse the bounded
descriptor reader across the chain. Reuse is the smallest consistent change
and preserves the existing artifact schemas and workflow.

Decision: expose the bounded regular-JSON reader, retain the 4 MiB scorecard
limit, and apply a 64 KiB limit plus regular-file and no-final-symlink checks to
replacement receipts and owner attestations. Keep failure reports path-free.

Verification: reproduce the former false passes for external replacement and
acceptance symlinks. Add regressions for both symlinks and an oversized
replacement receipt, then run focused evidence tests, the full Python suite,
offline preflight, exact-head CI, and review before merge.

Limitations: regular-file custody is local evidence hygiene, not independent
attestation or proof that transcript content is true. This change does not
deploy the worker, exercise live audio, create real evidence, establish owner
acceptance, or prove customer activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host, run `make owner-pilot-ready`, deploy the worker, and complete one live
owner session plus retained replacement and acceptance verification.

Rollback: revert the shared reader and replacement/acceptance integrations,
their regressions, and documentation. The repair changes only verifier behavior
and creates no provider, deployment, or production state.

### 2026-11-19: make new scorecard storage private by default

Baseline: `acf707179767db0023dd77b9e4b31209a3751e17` (merged PR #45).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. No checked-in evidence shows a new
credentialed worker deployment, real owner session, or operational acceptance.

Diagnosis: under a normal `022` host umask, the worker created a missing
`SCORECARD_DIR` with mode `0755`. Atomic scorecard files were already `0600`,
so their contents stayed unreadable, but another host user could enumerate
session identifiers and evidence filenames in newly created local storage.

Alternatives: rely on file permissions alone, chmod every existing persistent
volume, or make only newly created storage private. Changing every existing
volume could override deliberate operator ownership and shared-container access.

Decision: create a missing scorecard directory with mode `0700`, preserve
operator-managed permissions when it already exists, and retain atomic `0600`
scorecard publication.

Verification: reproduce `0755` creation with an explicit `022` umask, then add
a lifecycle regression requiring `0700` directory and `0600` scorecard modes.
Run the focused regression, full Python suite, offline preflight, exact-head CI,
and review before merge.

Limitations: this protects newly created POSIX storage; it does not repair an
existing volume's permissions or provide independent custody. It does not
deploy the worker, exercise live audio, create real evidence, establish owner
acceptance, or prove customer activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host, validate the existing volume with `make owner-pilot-ready`, deploy the
worker, and complete one live owner session plus retained replacement and
acceptance verification.

Rollback: revert the directory mode, regression, and documentation to restore
umask-derived creation. The repair creates only temporary test evidence and no
provider, deployment, or production state.

### 2026-11-20: enforce private storage on the Compose deployment path

Baseline: `757db64e6cd3530e17d06e831bbcae8382e9a2c3` (merged PR #46).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. No checked-in evidence shows a new
credentialed worker deployment, real owner session, or operational acceptance.

Diagnosis: the worker now creates a missing scorecard directory as `0700`, but
the production image already created `/data/scorecards` with the image-builder
default mode. Under the normal `022` umask that directory was `0755`, and Docker
could seed a fresh named volume from it before the worker ran. The storage
preflight tested write/read durability but accepted an existing `0755` volume.

Alternatives: chmod every mounted volume at worker startup, rely only on each
scorecard's `0600` mode, or seed new volumes privately and reject permissive
existing storage. Automatic chmod could override deliberate operator ownership
and shared-container access, so the last option is the smallest safe change.

Decision: seed `/data/scorecards` as owner-only `0700` in the image. Make the
storage preflight create missing local storage as `0700` and fail if an existing
directory grants any group or world permission. Do not print its path or alter
existing permissions.

Verification: reproduce both false passes: the Dockerfile lacked a private
directory contract, and `check_storage` accepted a `0755` directory. Add
regressions for both, then run the focused tests, full Python suite, offline
preflight, exact-head application and worker-image CI, and review before merge.

Limitations: POSIX mode checks do not inspect ACLs or independently attest host
custody. An older permissive volume requires an operator to inspect ownership
and correct its mode before deployment. This does not deploy the worker, contact
providers, exercise live audio, create real evidence, establish owner acceptance,
or prove customer activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host and run `make owner-pilot-deploy`. If the preflight reports storage failure,
inspect the named volume and set the intended scorecard directory to `0700`,
then rerun and complete one live owner evidence and acceptance chain.

Rollback: revert the image mode, preflight permission gate, regressions, and
documentation. This restores permissive-volume acceptance without changing or
deleting any existing volume, provider, deployment, or production state.

### 2026-11-21: stop before provider I/O when local deployment gates fail

Baseline: `87cf17aa6c9392943c82cd640929517349a61073` (merged PR #47).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. No checked-in evidence shows a new
credentialed worker deployment, real owner session, or operational acceptance.

Diagnosis: the connectivity preflight recorded a local component or private
storage failure but continued to authenticated LiveKit room listing and an
OpenAI Realtime handshake whenever credential shapes were valid. A deployment
that could not start therefore still contacted both providers and obscured the
ordering of its first actionable blocker.

Alternatives: keep collecting every independent diagnostic, gate only OpenAI,
or stop all provider checks after either local prerequisite fails. The strict
local gate is smallest, matches the deployment's fail-closed ordering, and
avoids service activity that cannot lead to a deployable worker.

Decision: after component and storage checks, mark configuration and both
provider checks `not_run` when either local check failed. Preserve the first
sanitized local next action and make no LiveKit or OpenAI request.

Verification: reproduce a storage `PermissionError` while substituting both
provider checks and prove each was previously awaited. Require the regression
to show neither is awaited and configuration is `not_run`, then run the focused
tests, full Python suite, offline preflight, exact-head CI, and review before
merge.

Limitations: substituted provider functions prove control flow, not credential
validity or external billing behavior. This does not deploy the worker, exercise
live audio, create real evidence, establish owner acceptance, or prove customer
activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host and run `make owner-pilot-deploy`. Correct the first sanitized local blocker
if one appears; only a locally ready worker will proceed to provider checks and
then the live owner evidence and acceptance chain.

Rollback: revert the local-gate branch, regression, and documentation to resume
provider connectivity checks despite local failure. The repair itself creates
only temporary fixtures and no provider, deployment, or production state.

### 2026-11-22: stop provider checks at the first connectivity blocker

Baseline: `b5631884eed683405e3f0ee9ea0b11b9dcdde7be` (merged PR #48).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. No checked-in evidence shows a new
credentialed worker deployment, real owner session, or operational acceptance.

Diagnosis: after local and configuration gates passed, a failed authenticated
LiveKit room listing still led to an OpenAI Realtime handshake. A substituted
LiveKit failure reproduced one call to each provider and a misleading passed
OpenAI result even though the worker could not deploy.

Alternatives: keep collecting independent provider diagnostics, run the checks
in parallel, or require the deployment's first provider dependency before the
second. Independent diagnostics may be useful interactively, but they create
avoidable provider activity after a decisive deployment blocker.

Decision: preserve the existing order and make it strict. When LiveKit fails,
record its sanitized failure and mark OpenAI `not_run`; check OpenAI only after
LiveKit passes. This keeps the first actionable next step and avoids a request
that cannot lead to deployment.

Verification: require the LiveKit-failure regression to prove the client closes,
the OpenAI function is not awaited, secrets remain absent, and the OpenAI check
is `not_run`. Run the focused test, full Python suite, offline preflight,
exact-head CI, and review before merge.

Limitations: substituted provider functions prove control flow, not credential
validity, billing behavior, or provider availability. This does not deploy the
worker, exercise live audio, create real evidence, establish owner acceptance,
or prove customer activity, payment, or revenue.

Next executable step: after merge, use clean main on the credentialed Docker
host and run `make owner-pilot-deploy`. Resolve the first sanitized provider
blocker; only both passing connectivity checks should allow worker startup and
the live owner evidence and acceptance chain.

Rollback: revert the strict provider-order branch, regression, and documentation
to resume the OpenAI check after LiveKit failure. The repair itself creates only
temporary fixtures and no provider, deployment, or production state.

### 2026-11-23: bound source-integrity inspection before deployment

Baseline: `39d1ce1119eba2f3d3ca56c4046068a6b3b3f87d` (merged PR #49).
Its exact-head application and worker-image jobs passed. DifficultAI, RepoMan,
and make_my_day have no open PR or issue. No checked-in evidence shows a new
credentialed worker deployment, real owner session, or operational acceptance.

Diagnosis: every Docker and provider deployment stage had a deadline, but the
Git revision and dirty-check subprocesses did not. A stalled local repository
therefore left readiness, deployment, and owner-session entrypoints waiting
indefinitely before their already bounded Docker and provider gates. A direct
probe confirmed both Git calls lacked a timeout.

Alternatives: rely on an external shell deadline, apply one deadline to the
entire command, or bound each source inspection. Per-call limits preserve the
existing stage-specific model and identify whether revision or checkout
inspection stalled without exposing Git output or a private host path.

Decision: allow 30 seconds each for `git rev-parse` and `git status`. Convert a
timeout into a sanitized `DeploymentError`; do not proceed to Docker, provider
I/O, or worker state changes. The shared source gate also protects readiness and
owner-session commands.

Verification: reproduce two successful Git calls with no timeout, then require
the regression to prove a timed-out revision probe is bounded, sanitized, and
stops before Docker. Require the successful deployment path to show both source
calls carry the deadline. Run focused deployment, readiness, and owner-session
tests, the full Python suite, offline preflight, exact-head CI, and review.

Limitations: substituted subprocesses prove control flow, not the health of the
owner's Git checkout or Docker host. This does not deploy the worker, contact
providers, exercise live audio, create real evidence, establish owner acceptance,
or prove customer activity, payment, or revenue.

Next executable step: after merge, update clean main on the credentialed Docker
host and run `make owner-pilot-ready`, then `make owner-pilot-deploy`. Correct
the first sanitized local or provider blocker before the live owner evidence and
acceptance chain.

Rollback: revert the source-inspection deadlines, regression, and documentation
to restore unbounded Git waits. The repair itself reads only substituted/local
source state and creates no provider, deployment, or production state.

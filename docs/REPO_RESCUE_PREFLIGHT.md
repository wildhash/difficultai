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

Verification: regressions reproduce false passes for both pre- and post-replace
revision mismatches, plus malformed or missing sanitized evidence. All 112 Python
tests and the offline preflight pass locally. Exact-head CI must pass before merge.

Limitations: mocked command sequencing does not deploy a worker or establish
credentials, provider access, live audio, real-session storage retention, owner
acceptance, customer activity, payment, or revenue.

Next executable step: after merge, deploy the exact clean main revision on the
intended Docker host, complete one real owner session, run the bound replacement
check, and record the owner's separate acceptance decision.

Rollback: revert this repair. It changes no image, scorecard, transcript, volume,
or acceptance record and never invokes a volume-removal command.

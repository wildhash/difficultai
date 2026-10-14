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

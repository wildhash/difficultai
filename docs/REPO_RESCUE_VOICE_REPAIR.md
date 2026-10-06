# Repo Rescue owner pilot: voice SDK repair

Date: 2026-10-06. Baseline: `8c8e558374cc639abe4b0fe627cf7bc5787d471b`.
This is a separate repair from the [web lifecycle PR](https://github.com/wildhash/difficultai/pull/7).

## Failure reproduced

After installing the repository's pinned requirements, constructing the original
realtime assistant raised:

```text
TypeError: RealtimeModel.__init__() got an unexpected keyword argument 'instructions'
```

The installed 1.3.12 SDKs also lack the referenced `VoiceAssistant`,
`agents.silero`, `RealtimeSTT`, and `RealtimeTTS`. Existing scenario/evaluator
tests passed without exercising these runtime paths.

## Repair

- Use the pinned SDK's `AgentSession` with `Agent` instructions and awaited
  startup. Both realtime and STT/LLM/TTS session constructors run locally.
- Use committed conversation events with synchronous SDK listeners. Forward
  transcripts to the existing web contract, and update instructions after
  collecting scenario metadata. Dispatch metadata falls back to room metadata.
- Close the session and finalize its scorecard once across normal completion
  and job shutdown. Provider failures are raised and stored as failed sessions.
- Write a unique, atomic scorecard file per session. Room names are retained
  as data and never used in filenames; repeated names cannot overwrite results.
- Keep optional Opik tracing disabled until its destination is configured.
- Add a credential-free Python CI job and document explicit `VOICE_MODE`
  selection. Automatic provider failover is not implemented.

The migration follows [LiveKit's supported 1.x interfaces](https://docs.livekit.io/reference/migration-guides/v0-migration/python/),
checked against the installed, pinned package sources rather than assuming the
latest documentation matches every signature.

## Local verification

Python 3.12.14; `livekit-agents` and `livekit-plugins-openai` 1.3.12.

```bash
OPIK_DISABLED=1 DOTENV_DISABLED=1 python -m unittest discover -p 'test_*.py' -v
OPIK_DISABLED=1 DOTENV_DISABLED=1 python -m apps.livekit_agent --help
actionlint .github/workflows/python-tests.yml
```

52 tests passed: the existing 43 plus 9 runtime/observability cases. Worker CLI
imports and workflow validation passed. Real SDK session/provider constructors
were exercised with a dummy key; service I/O was replaced for lifecycle tests.
The local managed proxy required the optional `httpx[socks]` transport extra.

The tests verify transcript forwarding, current SDK events, metadata fallback
and updates, failure records, shutdown idempotence, and preservation of multiple
sessions for the same room. Temporary test records were removed afterwards.

## Acceptance still required

No live room, paid provider call, deployment, customer acceptance, payment, or
revenue was demonstrated. Live barge-in, audio quality, credentials, provider
access, and metadata timing during a realtime conversation remain unverified.
Scorecard storage is local; retention across replacement requires a persistent
volume and an operator-managed backup policy. Authenticated customer retrieval
is outside this repair.

Next acceptance step: run a short owner session with configured LiveKit/OpenAI
credentials, end it, restart the worker, and verify the transcript and scorecard
remain readable from the configured persistent volume.

# Repo Rescue owner pilot: web repair

Date: 2026-10-06. Baseline: `8c8e558374cc639abe4b0fe627cf7bc5787d471b`.
The owner authorized this internal pilot. No customer sale, payment, or revenue
is represented by these tests.

## Reproduced and repaired

Nine component regressions failed against the original `App.jsx` and pass with
the repair. The tests render the actual app and replace the LiveKit Room with
an event-emitting fake; they never connect to a service.

1. Microphone denial disconnects the room and permits a clean retry.
2. Rejected tokens release the partially initialized room.
3. Early transcripts survive successful connection setup.
4. A connection completing after unmount cannot start the microphone.
5. Microphone setup completing after unmount is disconnected again.
6. Events from a previous room cannot change the current session's state.
7. A token for a different room is rejected before publishing microphone audio.
8. Connection setup can be canceled without a late microphone start.
9. Remote audio can attach while setup is still in progress.

The existing Pages workflow built successfully but failed during Configure
Pages: [run 29208702045](https://github.com/wildhash/difficultai/actions/runs/29208702045).
The repaired workflow tests/builds pull requests with read-only permissions.
Pages setup and publication run separately, only on `main`; Pages still needs
to be configured in repository settings. No deployment was performed in this
pilot.

## Local evidence

Node 24.19.0; Python 3.12.14. CI uses Node 20.

```bash
npm ci --prefix apps/web/demo
npm test --prefix apps/web/demo
GITHUB_PAGES=true npm run build --prefix apps/web/demo
actionlint .github/workflows/deploy-pages.yml
python -m unittest test_agents test_difficult_ai test_livekit_agent
```

- Web component tests: 9/9 passed after the repair (0/9 before).
- Pages build: passed; the existing bundle-size warning remains.
- Workflow syntax: passed actionlint 1.7.7.
- Existing Python tests: 43/43 passed using the pinned requirements. These
  test scenario/evaluator/legacy text logic, not live voice startup.

## Remaining voice-worker blocker

Freshly installed `livekit-agents==1.3.12` has `AgentSession` and `Agent`, but
does not have the `agents.VoiceAssistant` or `agents.silero` interfaces used by
the worker. `livekit-plugins-openai==1.3.12` also lacks its referenced
`RealtimeSTT` and `RealtimeTTS`. The current worker therefore needs an SDK
migration independently of this web repair.

A complete acceptance run still needs a LiveKit room and agent, a short-lived
participant token, provider credentials, permissioned audio, transcript and
scorecard verification, and a durable location for session records. A green
web build and mocked component tests do not establish any of those outcomes.

## Observability (Opik)

`difficultai.observability` provides an optional Opik tracer used by the LiveKit agent to emit:

- A session-level trace per room session
- Spans for key operations (LLM/STT/TTS)
- Error spans when exceptions occur

### Environment variables

- `OPIK_DISABLED`: set to `1`/`true`/`yes` to disable tracing entirely
- `OPIK_API_KEY`: Opik Cloud API key
- `OPIK_URL_OVERRIDE`: URL for a self-hosted Opik instance
- `OPIK_PROJECT`: Opik project name (default: `difficultai`)
- `OPIK_WORKSPACE`: Opik workspace (default: `default`)

### Usage

The primary entrypoint is `get_tracer()`:

```py
from difficultai.observability import get_tracer

tracer = get_tracer()
if tracer.enabled:
    tracer.start_session_trace(
        livekit_room=room_name,
        session_id=session_id,
        participant_identity=participant_identity,
        scenario=scenario,
    )
```

### Concurrency

The tracer stores the active trace in a `contextvars.ContextVar` so concurrent async tasks do not overwrite one another.

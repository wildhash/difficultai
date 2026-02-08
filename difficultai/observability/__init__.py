"""Observability module for DifficultAI with Opik integration."""

from .opik_tracing import (
    OpikTracer,
    get_opik_config,
    get_tracer,
    is_opik_enabled,
    trace_llm_call,
    trace_session,
    trace_stt_call,
    trace_tts_call,
)

__all__ = [
    'OpikTracer',
    'get_opik_config',
    'get_tracer',
    'is_opik_enabled',
    'trace_llm_call',
    'trace_session',
    'trace_stt_call',
    'trace_tts_call',
]

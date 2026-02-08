"""Observability module for DifficultAI with Opik integration."""

from .opik_tracing import (
    OpikTracer,
    is_opik_enabled,
    get_opik_config,
    trace_session,
    trace_llm_call,
    trace_stt_call,
    trace_tts_call,
)

__all__ = [
    'OpikTracer',
    'is_opik_enabled',
    'get_opik_config',
    'trace_session',
    'trace_llm_call',
    'trace_stt_call',
    'trace_tts_call',
]

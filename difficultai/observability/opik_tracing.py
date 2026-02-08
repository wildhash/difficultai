"""
Opik Tracing Integration for DifficultAI

This module provides observability for DifficultAI using Opik.
It traces session lifecycle, LLM calls, STT/TTS operations, and errors.

Environment Variables:
    OPIK_API_KEY: API key for Opik Cloud (required for cloud)
    OPIK_URL_OVERRIDE: Override Opik URL (for self-hosted)
    OPIK_PROJECT: Project name (default: "difficultai")
    OPIK_WORKSPACE: Workspace name (default: "default")
    OPIK_DISABLED: Set to "1" or "true" to disable Opik tracing

Trace Structure:
    - Session-level traces include: livekit_room, session_id, participant_identity,
      scenario, role/persona, difficulty
    - Span-level traces include: stt, llm, tts, tool_calls, errors
"""

import os
import logging
import time
import warnings
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

_current_trace: ContextVar[Optional[Any]] = ContextVar("opik_current_trace", default=None)


def is_opik_enabled() -> bool:
    """Check if Opik tracing is enabled."""
    disabled = os.getenv("OPIK_DISABLED", "").lower() in ("1", "true", "yes")
    return not disabled


def get_opik_config() -> Dict[str, Any]:
    """Get Opik configuration from environment variables."""
    return {
        "api_key": os.getenv("OPIK_API_KEY"),
        "url_override": os.getenv("OPIK_URL_OVERRIDE"),
        "project_name": os.getenv("OPIK_PROJECT", "difficultai"),
        "workspace": os.getenv("OPIK_WORKSPACE", "default"),
    }


class OpikTracer:
    """
    Centralized Opik tracing manager for DifficultAI.
    
    This class handles all Opik tracing operations including:
    - Session-level traces
    - LLM call traces
    - STT/TTS traces
    - Error tracking
    
    Uses Opik's OpenAI integration when available (track_openai).
    """
    
    def __init__(self):
        """Initialize OpikTracer."""
        self.enabled = is_opik_enabled()
        self.config = get_opik_config()
        self.client = None
        self.openai_client = None
        
        if self.enabled:
            self._initialize_opik()
        else:
            logger.info("Opik tracing is disabled (OPIK_DISABLED=1)")
    
    def _initialize_opik(self):
        """Initialize Opik client and OpenAI tracking."""
        try:
            import opik
            
            configure_kwargs: Dict[str, Any] = {}
            if self.config["api_key"]:
                configure_kwargs["api_key"] = self.config["api_key"]
            if self.config.get("workspace"):
                configure_kwargs["workspace"] = self.config["workspace"]
            if self.config["url_override"]:
                configure_kwargs["url"] = self.config["url_override"]

            if configure_kwargs:
                opik.configure(**configure_kwargs)

            self.client = opik.Opik(project_name=self.config["project_name"])
            
            # Enable OpenAI tracking if OpenAI is available
            try:
                from opik.integrations.openai import track_openai
                import openai
                
                self.openai_client = track_openai(
                    openai.Client(),
                    project_name=self.config["project_name"],
                )
                logger.info("✓ Opik OpenAI integration enabled")
            except ImportError:
                logger.info("OpenAI SDK not tracked (import failed)")
            
            logger.info(f"✓ Opik tracing enabled (project: {self.config['project_name']})")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Opik: {e}")
            self.enabled = False
            self.client = None
    
    def start_session_trace(
        self,
        livekit_room: str,
        session_id: str,
        participant_identity: str,
        scenario: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Start a session-level trace.
        
        Args:
            livekit_room: LiveKit room name
            session_id: Unique session identifier
            participant_identity: Participant identity
            scenario: Scenario configuration dict
            
        Returns:
            Opik trace object or None if tracing is disabled
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            import opik

            existing_trace = _current_trace.get()
            if existing_trace is not None:
                logger.warning(
                    "Opik trace already active in this context; resetting before starting a new one"
                )
                self.reset_trace()
            
            safe_scenario: Dict[str, Any] = scenario or {}

            # Extract scenario details
            persona = safe_scenario.get("persona_type", "unknown")
            role = safe_scenario.get("role", "unknown")
            difficulty = safe_scenario.get("difficulty", 0.5)
            company = safe_scenario.get("company", "unknown")
            
            # Create trace with rich metadata
            trace = self.client.trace(
                name=f"DifficultAI Session: {livekit_room}",
                input={
                    "livekit_room": livekit_room,
                    "session_id": session_id,
                    "participant_identity": participant_identity,
                    "scenario": safe_scenario,
                },
                metadata={
                    "livekit_room": livekit_room,
                    "session_id": session_id,
                    "participant_identity": participant_identity,
                    "persona": persona,
                    "role": role,
                    "difficulty": difficulty,
                    "company": company,
                    "scenario_type": "voice_conversation",
                },
                tags=["difficultai", "livekit", str(persona).lower()],
            )
            
            _current_trace.set(trace)
            logger.info(f"Started Opik trace: {trace.id}")
            return trace
            
        except Exception as e:
            logger.error(f"Failed to start session trace: {e}")
            _current_trace.set(None)
            return None

    def has_active_trace(self) -> bool:
        """Return True if a trace is currently active in this async context."""
        return self.enabled and _current_trace.get() is not None

    def reset_trace(self):
        """Best-effort cleanup of any active trace in this async context."""
        trace = _current_trace.get()
        if not trace:
            return

        try:
            trace.end()
        except Exception as e:
            logger.error(f"Failed to end stale Opik trace during reset: {e}")
        finally:
            _current_trace.set(None)
    
    def end_session_trace(self, output: Optional[Dict[str, Any]] = None):
        """End the current session trace."""
        trace = _current_trace.get()

        if not self.enabled or not trace:
            return

        try:
            if output:
                trace.update(output=output)
            trace.end()
            logger.info("Ended Opik trace")
        except Exception as e:
            logger.error(f"Failed to end session trace: {e}")
        finally:
            _current_trace.set(None)

    def log_scorecard_feedback_scores(
        self,
        scorecard: Dict[str, Any],
        category_name: str = "scorecard",
    ) -> None:
        """Log scorecard dimensions as Opik feedback scores for the current trace.

        This makes scorecard results easy to aggregate and compare in Opik.
        """

        trace = _current_trace.get()
        if not self.enabled or not self.client or not trace:
            return

        try:
            scores = (scorecard or {}).get("scores") or {}
            if not isinstance(scores, dict) or not scores:
                return

            feedback_scores = []
            total = 0.0
            count = 0

            for key, value in scores.items():
                try:
                    f_value = float(value)
                except (TypeError, ValueError):
                    continue

                feedback_scores.append(
                    {
                        "id": trace.id,
                        "name": f"{category_name}.{key}",
                        "value": f_value,
                        "category_name": category_name,
                    }
                )

                total += f_value
                count += 1

            if count > 0:
                feedback_scores.append(
                    {
                        "id": trace.id,
                        "name": f"{category_name}.overall",
                        "value": total / count,
                        "category_name": category_name,
                    }
                )

            if feedback_scores:
                self.client.log_traces_feedback_scores(feedback_scores)

        except Exception as e:
            logger.error(f"Failed to log scorecard feedback scores: {e}")
    
    @contextmanager
    def trace_llm_span(
        self,
        model: str,
        messages: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing LLM calls.
        
        Args:
            model: Model name (e.g., "gpt-4", "gpt-4-realtime")
            messages: Optional chat messages
            metadata: Additional metadata
            
        Yields:
            Span object for additional logging
            
        Example:
            with tracer.trace_llm_span("gpt-4", messages) as span:
                response = llm.chat(messages)
                span.update(output=response)
        """
        trace = _current_trace.get()
        if not self.enabled or not trace:
            yield None
            return

        merged_metadata = {
            "model": model,
            **(metadata or {}),
        }

        try:
            span = trace.span(
                name="llm_call",
                type="llm",
                input={"messages": messages} if messages else {},
                metadata=merged_metadata,
            )

            start_time = time.time()

            try:
                yield span
            finally:
                duration = time.time() - start_time
                final_metadata: Dict[str, Any] = {
                    **merged_metadata,
                    "duration_seconds": duration,
                }
                span_metadata = getattr(span, "metadata", None)
                if isinstance(span_metadata, dict):
                    final_metadata = {
                        **span_metadata,
                        **final_metadata,
                    }

                span.update(metadata=final_metadata)
                span.end()

        except Exception as e:
            logger.error(f"Failed to trace LLM span: {e}")
            yield None
    
    @contextmanager
    def trace_stt_span(
        self,
        provider: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing STT (Speech-to-Text) calls.
        
        Args:
            provider: STT provider (e.g., "deepgram", "openai-whisper", "realtime")
            metadata: Additional metadata
            
        Yields:
            Span object for additional logging
        """
        trace = _current_trace.get()
        if not self.enabled or not trace:
            yield None
            return

        merged_metadata = {
            "provider": provider,
            "operation": "speech_to_text",
            **(metadata or {}),
        }

        try:
            span = trace.span(
                name="stt_call",
                type="tool",
                metadata=merged_metadata,
            )

            start_time = time.time()

            try:
                yield span
            finally:
                duration = time.time() - start_time
                final_metadata: Dict[str, Any] = {
                    **merged_metadata,
                    "duration_seconds": duration,
                }
                span_metadata = getattr(span, "metadata", None)
                if isinstance(span_metadata, dict):
                    final_metadata = {
                        **span_metadata,
                        **final_metadata,
                    }

                span.update(metadata=final_metadata)
                span.end()

        except Exception as e:
            logger.error(f"Failed to trace STT span: {e}")
            yield None
    
    @contextmanager
    def trace_tts_span(
        self,
        provider: str,
        voice: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing TTS (Text-to-Speech) calls.
        
        Args:
            provider: TTS provider (e.g., "openai", "realtime")
            voice: Voice name if applicable
            metadata: Additional metadata
            
        Yields:
            Span object for additional logging
        """
        trace = _current_trace.get()
        if not self.enabled or not trace:
            yield None
            return

        merged_metadata = {
            "provider": provider,
            "operation": "text_to_speech",
            **(metadata or {}),
        }
        if voice:
            merged_metadata["voice"] = voice

        try:
            span = trace.span(
                name="tts_call",
                type="tool",
                metadata=merged_metadata,
            )

            start_time = time.time()

            try:
                yield span
            finally:
                duration = time.time() - start_time
                final_metadata: Dict[str, Any] = {
                    **merged_metadata,
                    "duration_seconds": duration,
                }
                span_metadata = getattr(span, "metadata", None)
                if isinstance(span_metadata, dict):
                    final_metadata = {
                        **span_metadata,
                        **final_metadata,
                    }

                span.update(metadata=final_metadata)
                span.end()

        except Exception as e:
            logger.error(f"Failed to trace TTS span: {e}")
            yield None
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an error to the current trace.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
        """
        trace = _current_trace.get()
        if not self.enabled or not trace:
            return
        
        try:
            error_data = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            }
            
            # Create error span
            span = trace.span(
                name="error",
                type="tool",
                metadata=error_data,
            )
            span.end()
            
            logger.error(f"Logged error to Opik trace: {error}")
            
        except Exception as e:
            logger.error(f"Failed to log error to trace: {e}")


# Global tracer instance
_global_tracer: Optional[OpikTracer] = None


def get_tracer() -> OpikTracer:
    """Get or create the global OpikTracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = OpikTracer()
    return _global_tracer


def trace_session(func: Callable) -> Callable:
    warnings.warn(
        "trace_session is deprecated; use get_tracer().start_session_trace()/end_session_trace instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


def trace_llm_call(model: str, messages: Optional[list] = None):
    warnings.warn(
        "trace_llm_call is deprecated; use OpikTracer.trace_llm_span instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace_llm_span(model, messages):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def trace_stt_call(provider: str):
    warnings.warn(
        "trace_stt_call is deprecated; use OpikTracer.trace_stt_span instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace_stt_span(provider):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def trace_tts_call(provider: str, voice: Optional[str] = None):
    warnings.warn(
        "trace_tts_call is deprecated; use OpikTracer.trace_tts_span instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace_tts_span(provider, voice=voice):
                return await func(*args, **kwargs)

        return wrapper

    return decorator

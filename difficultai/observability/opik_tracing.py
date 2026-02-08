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
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


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
        self.current_trace = None
        
        if self.enabled:
            self._initialize_opik()
        else:
            logger.info("Opik tracing is disabled (OPIK_DISABLED=1)")
    
    def _initialize_opik(self):
        """Initialize Opik client and OpenAI tracking."""
        try:
            import opik
            
            # Configure Opik
            configure_kwargs = {
                "project_name": self.config["project_name"],
            }
            
            if self.config["api_key"]:
                configure_kwargs["api_key"] = self.config["api_key"]
            
            if self.config["url_override"]:
                configure_kwargs["url"] = self.config["url_override"]
                
            opik.configure(**configure_kwargs)
            
            self.client = opik.Opik()
            
            # Enable OpenAI tracking if OpenAI is available
            try:
                from opik.integrations.openai import track_openai
                import openai
                
                # Track OpenAI calls automatically
                openai_client = track_openai(openai.Client())
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
            
            # Extract scenario details
            persona = scenario.get("persona_type", "unknown")
            role = scenario.get("role", "unknown")
            difficulty = scenario.get("difficulty", 0.5)
            company = scenario.get("company", "unknown")
            
            # Create trace with rich metadata
            trace = self.client.trace(
                name=f"DifficultAI Session: {livekit_room}",
                input={
                    "livekit_room": livekit_room,
                    "session_id": session_id,
                    "participant_identity": participant_identity,
                    "scenario": scenario,
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
                tags=["difficultai", "livekit", persona.lower()],
            )
            
            self.current_trace = trace
            logger.info(f"Started Opik trace: {trace.id}")
            return trace
            
        except Exception as e:
            logger.error(f"Failed to start session trace: {e}")
            return None
    
    def end_session_trace(self, output: Optional[Dict[str, Any]] = None):
        """
        End the current session trace.
        
        Args:
            output: Optional output data (e.g., scorecard, final metrics)
        """
        if not self.enabled or not self.current_trace:
            return
        
        try:
            if output:
                self.current_trace.update(output=output)
            self.current_trace.end()
            logger.info("Ended Opik trace")
            self.current_trace = None
        except Exception as e:
            logger.error(f"Failed to end session trace: {e}")
    
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
        if not self.enabled or not self.current_trace:
            yield None
            return
        
        try:
            span = self.current_trace.span(
                name="llm_call",
                type="llm",
                input={"messages": messages} if messages else {},
                metadata={
                    "model": model,
                    **(metadata or {}),
                },
            )
            
            start_time = time.time()
            
            try:
                yield span
            finally:
                duration = time.time() - start_time
                span.update(
                    metadata={
                        **span.metadata,
                        "duration_seconds": duration,
                    }
                )
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
        if not self.enabled or not self.current_trace:
            yield None
            return
        
        try:
            span = self.current_trace.span(
                name="stt_call",
                type="tool",
                metadata={
                    "provider": provider,
                    "operation": "speech_to_text",
                    **(metadata or {}),
                },
            )
            
            start_time = time.time()
            
            try:
                yield span
            finally:
                duration = time.time() - start_time
                span.update(
                    metadata={
                        **span.metadata,
                        "duration_seconds": duration,
                    }
                )
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
        if not self.enabled or not self.current_trace:
            yield None
            return
        
        try:
            span_metadata = {
                "provider": provider,
                "operation": "text_to_speech",
                **(metadata or {}),
            }
            
            if voice:
                span_metadata["voice"] = voice
            
            span = self.current_trace.span(
                name="tts_call",
                type="tool",
                metadata=span_metadata,
            )
            
            start_time = time.time()
            
            try:
                yield span
            finally:
                duration = time.time() - start_time
                span.update(
                    metadata={
                        **span.metadata,
                        "duration_seconds": duration,
                    }
                )
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
        if not self.enabled or not self.current_trace:
            return
        
        try:
            error_data = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            }
            
            # Create error span
            span = self.current_trace.span(
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


# Convenience functions for common operations

def trace_session(func: Callable) -> Callable:
    """
    Decorator for tracing a complete session.
    
    The decorated function should accept 'ctx' (JobContext) as first argument.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tracer = get_tracer()
        
        # Try to extract context from args
        ctx = None
        for arg in args:
            if hasattr(arg, 'room') and hasattr(arg, 'job'):
                ctx = arg
                break
        
        if ctx and tracer.enabled:
            # Extract session info
            room_name = ctx.room.name if hasattr(ctx, 'room') else "unknown"
            session_id = ctx.job.id if hasattr(ctx.job, 'id') else "unknown"
            
            # Start trace
            tracer.start_session_trace(
                livekit_room=room_name,
                session_id=session_id,
                participant_identity="participant",
                scenario={},
            )
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            if tracer.enabled:
                tracer.end_session_trace()
    
    return wrapper


def trace_llm_call(model: str, messages: Optional[list] = None):
    """
    Decorator for tracing LLM calls.
    
    Usage:
        @trace_llm_call("gpt-4")
        async def call_llm(messages):
            return await llm.chat(messages)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.trace_llm_span(model, messages):
                result = await func(*args, **kwargs)
                return result
        
        return wrapper
    return decorator


def trace_stt_call(provider: str):
    """
    Decorator for tracing STT calls.
    
    Usage:
        @trace_stt_call("deepgram")
        async def transcribe_audio(audio):
            return await stt.transcribe(audio)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.trace_stt_span(provider):
                result = await func(*args, **kwargs)
                return result
        
        return wrapper
    return decorator


def trace_tts_call(provider: str, voice: Optional[str] = None):
    """
    Decorator for tracing TTS calls.
    
    Usage:
        @trace_tts_call("openai", voice="marin")
        async def synthesize_speech(text):
            return await tts.synthesize(text)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.trace_tts_span(provider, voice):
                result = await func(*args, **kwargs)
                return result
        
        return wrapper
    return decorator

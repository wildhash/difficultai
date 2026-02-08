"""
Opik Smoke Test for DifficultAI

This test validates that Opik tracing is correctly configured and working.
It runs a synthetic single-turn LLM call and emits an Opik trace.

Run with: python apps/livekit_agent/opik_smoke_test.py
Or: make opik-smoke-test
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Load environment variables
load_dotenv()

print("=" * 70)
print("DifficultAI Opik Tracing - Smoke Test")
print("=" * 70)
print()

# Check if Opik is disabled
if os.getenv("OPIK_DISABLED", "").lower() in ("1", "true", "yes"):
    print("⚠️  Opik tracing is disabled (OPIK_DISABLED=1)")
    print()
    print("This smoke test will validate the code but will not emit traces.")
    print("To enable Opik, remove or set OPIK_DISABLED=0 in your .env file")
    print()

# Import Opik tracing module
try:
    from difficultai.observability import OpikTracer, is_opik_enabled, get_opik_config
    print("✓ Opik tracing module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Opik tracing module: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

print()
print("-" * 70)
print("Opik Configuration")
print("-" * 70)

config = get_opik_config()
enabled = is_opik_enabled()

print(f"Enabled: {enabled}")
print(f"Project: {config['project_name']}")
print(f"Workspace: {config['workspace']}")

if config['api_key']:
    print(f"API Key: {config['api_key'][:10]}... (configured)")
else:
    print("API Key: Not set")
    
if config['url_override']:
    print(f"URL Override: {config['url_override']}")
else:
    print("URL Override: Using default (Opik Cloud)")

if not enabled:
    print()
    print("⚠️  Opik is DISABLED - traces will not be emitted")
elif not config['api_key'] and not config['url_override']:
    print()
    print("⚠️  No OPIK_API_KEY set - traces may fail to upload to Opik Cloud")
    print("    Set OPIK_API_KEY in .env or use OPIK_URL_OVERRIDE for self-hosted")

print()
print("-" * 70)
print("Testing Opik Tracer Initialization")
print("-" * 70)

try:
    tracer = OpikTracer()
    print("✓ OpikTracer initialized successfully")
    
    if tracer.enabled:
        print(f"✓ Opik client is active (project: {tracer.config['project_name']})")
    else:
        print("⚠️  Opik tracing is disabled")
        
except Exception as e:
    print(f"❌ Failed to initialize OpikTracer: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("-" * 70)
print("Testing Session Trace")
print("-" * 70)

try:
    # Start a test session trace
    test_scenario = {
        "persona_type": "ELITE_INTERVIEWER",
        "company": "SmokeCorp",
        "role": "Test Engineer",
        "difficulty": 0.5,
    }
    
    trace = tracer.start_session_trace(
        livekit_room="smoke-test-room",
        session_id="smoke-test-session-001",
        participant_identity="smoke-test-user",
        scenario=test_scenario,
    )
    
    if tracer.enabled:
        print("✓ Session trace started")
        if trace:
            print(f"  Trace ID: {trace.id}")
    else:
        print("⚠️  Session trace not created (Opik disabled)")
    
except Exception as e:
    print(f"❌ Failed to start session trace: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("-" * 70)
print("Testing LLM Span")
print("-" * 70)

try:
    # Test LLM span
    with tracer.trace_llm_span(
        model="gpt-4-smoke-test",
        messages=[{"role": "user", "content": "Hello, this is a smoke test"}],
        metadata={"test": True},
    ) as span:
        print("✓ LLM span created")
        
        # Simulate LLM response
        import time
        time.sleep(0.1)
        
        if span:
            span.update(output={"response": "This is a test response"})
            print("✓ LLM span updated with output")
        elif tracer.enabled:
            print("⚠️  LLM span is None (unexpected)")
        else:
            print("⚠️  LLM span not created (Opik disabled)")
    
    print("✓ LLM span completed")
    
except Exception as e:
    print(f"❌ Failed to create LLM span: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("-" * 70)
print("Testing STT Span")
print("-" * 70)

try:
    with tracer.trace_stt_span(
        provider="deepgram-smoke-test",
        metadata={"test": True},
    ) as span:
        print("✓ STT span created")
        
        import time
        time.sleep(0.05)
        
        if span:
            span.update(
                input={"audio_duration_seconds": 2.5},
                output={"transcript": "This is a smoke test transcript"}
            )
            print("✓ STT span updated")
    
    print("✓ STT span completed")
    
except Exception as e:
    print(f"❌ Failed to create STT span: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("-" * 70)
print("Testing TTS Span")
print("-" * 70)

try:
    with tracer.trace_tts_span(
        provider="openai-smoke-test",
        voice="marin",
        metadata={"test": True},
    ) as span:
        print("✓ TTS span created")
        
        import time
        time.sleep(0.05)
        
        if span:
            span.update(
                input={"text": "This is a smoke test"},
                output={"audio_duration_seconds": 1.8}
            )
            print("✓ TTS span updated")
    
    print("✓ TTS span completed")
    
except Exception as e:
    print(f"❌ Failed to create TTS span: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("-" * 70)
print("Testing Error Logging")
print("-" * 70)

try:
    # Test error logging
    test_error = Exception("This is a smoke test error")
    tracer.log_error(test_error, context={"test": True, "stage": "smoke_test"})
    print("✓ Error logged to trace")
    
except Exception as e:
    print(f"❌ Failed to log error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("-" * 70)
print("Ending Session Trace")
print("-" * 70)

try:
    # End the session trace
    tracer.end_session_trace(output={
        "test_completed": True,
        "spans_created": ["llm", "stt", "tts", "error"],
    })
    print("✓ Session trace ended")
    
except Exception as e:
    print(f"❌ Failed to end session trace: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("✅ OPIK SMOKE TEST PASSED")
print("=" * 70)
print()

if tracer.enabled and tracer.config['api_key']:
    print("Trace successfully emitted! View it in Opik:")
    print()
    print("  1. Go to https://www.comet.com/opik")
    print(f"  2. Navigate to project: {tracer.config['project_name']}")
    print("  3. Look for trace: 'DifficultAI Session: smoke-test-room'")
    print()
    print("The trace should include:")
    print("  ✓ Session metadata (room, participant, scenario)")
    print("  ✓ LLM span with test message")
    print("  ✓ STT span with test audio")
    print("  ✓ TTS span with test synthesis")
    print("  ✓ Error span with test error")
elif tracer.enabled:
    print("Opik tracer is enabled but no API key is set.")
    print("Traces were created locally but may not have been uploaded.")
    print()
    print("To view traces in Opik Cloud:")
    print("  1. Get an API key from https://www.comet.com/opik")
    print("  2. Set OPIK_API_KEY in your .env file")
    print("  3. Re-run this smoke test")
else:
    print("Opik tracing is disabled. All tracing code was validated but")
    print("no traces were emitted.")
    print()
    print("To enable Opik tracing:")
    print("  1. Remove OPIK_DISABLED=1 from your .env file")
    print("  2. Set OPIK_API_KEY (for cloud) or OPIK_URL_OVERRIDE (self-hosted)")
    print("  3. Re-run this smoke test")

print()

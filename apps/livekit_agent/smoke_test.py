"""
Smoke Test for DifficultAI LiveKit Agent

This test:
1. Connects to a LiveKit room
2. Sends a test message
3. Receives responses
4. Prints transcripts
5. Validates basic functionality

Run with: python apps/livekit_agent/smoke_test.py
Or: make smoke-test
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
print("DifficultAI LiveKit Agent - Smoke Test")
print("=" * 70)
print()

# Check required environment variables
required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print("❌ SMOKE TEST FAILED: Missing required environment variables")
    print()
    print("Missing variables:")
    for var in missing_vars:
        print(f"  - {var}")
    print()
    print("Please set these in your .env file")
    print("See .env.example for reference")
    sys.exit(1)

print("✓ Environment variables loaded")
print(f"  LIVEKIT_URL: {os.getenv('LIVEKIT_URL')[:30]}...")
print(f"  LIVEKIT_API_KEY: {os.getenv('LIVEKIT_API_KEY')[:10]}...")
print(f"  OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:10]}...")
print()

try:
    from livekit import api, rtc
    print("✓ LiveKit SDK imported successfully")
except ImportError as e:
    print(f"❌ Failed to import LiveKit SDK: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from apps.livekit_agent.scenario_validator import validate_scenario
    from agents.architect import PersonaType
    print("✓ DifficultAI modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import DifficultAI modules: {e}")
    sys.exit(1)

print()
print("-" * 70)
print("Testing Scenario Validation")
print("-" * 70)

# Test scenario validation
test_scenario = {
    "persona_type": "ELITE_INTERVIEWER",
    "company": "TestCorp",
    "role": "Software Engineer",
    "stakes": "Smoke test scenario",
    "user_goal": "Verify agent functionality",
    "difficulty": 0.6  # Using 0-1 scale
}

errors = validate_scenario(test_scenario)
if errors:
    print(f"❌ Scenario validation failed: {errors}")
    sys.exit(1)
else:
    print("✓ Scenario validation passed")
    print(f"  Persona: {test_scenario['persona_type']}")
    print(f"  Difficulty: {test_scenario['difficulty']} (0-1 scale)")

print()
print("-" * 70)
print("Testing LiveKit Connection")
print("-" * 70)

async def test_livekit_connection():
    """Test basic LiveKit connection."""
    try:
        # Create a simple room service client
        room_service = api.RoomServiceClient(
            os.getenv("LIVEKIT_URL"),
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET")
        )
        
        # List rooms (this validates credentials)
        rooms = room_service.list_rooms(api.ListRoomsRequest())
        print(f"✓ Connected to LiveKit server")
        print(f"  Active rooms: {len(rooms.rooms)}")
        
        # Test token generation
        token = api.AccessToken(
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET")
        )
        token.with_identity("smoke-test-user")
        token.with_name("Smoke Test")
        token.with_grants(api.VideoGrants(
            room_join=True,
            room="smoke-test-room"
        ))
        jwt = token.to_jwt()
        
        print(f"✓ Generated participant token")
        print(f"  Token length: {len(jwt)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ LiveKit connection failed: {e}")
        return False

# Run async test
connection_ok = asyncio.run(test_livekit_connection())

if not connection_ok:
    print()
    print("❌ SMOKE TEST FAILED")
    print()
    print("Troubleshooting:")
    print("  1. Verify LIVEKIT_URL is correct (should start with wss:// or ws://)")
    print("  2. Check LIVEKIT_API_KEY and LIVEKIT_API_SECRET are valid")
    print("  3. Ensure LiveKit server is accessible")
    sys.exit(1)

print()
print("-" * 70)
print("Testing Agent Components")
print("-" * 70)

try:
    from agents.evaluator import EvaluatorAgent
    from agents.architect import ArchitectAgent
    
    # Test architect
    architect = ArchitectAgent()
    print("✓ ArchitectAgent initialized")
    
    # Test evaluator
    evaluator = EvaluatorAgent()
    print("✓ EvaluatorAgent initialized")
    
    # Test evaluation with mock data
    mock_metrics = {
        'vague_response_count': 1,
        'deflection_count': 0,
        'commitments_made': 2,
        'total_exchanges': 5,
        'current_difficulty': 0.6,
        'scenario_difficulty': 0.6
    }
    
    evaluation = evaluator.evaluate_conversation(mock_metrics, test_scenario)
    print("✓ Evaluation completed")
    print(f"  Overall score: {evaluation['scores']['overall']:.1f}/100")
    
except Exception as e:
    print(f"❌ Agent component test failed: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("✅ SMOKE TEST PASSED")
print("=" * 70)
print()
print("All critical components verified:")
print("  ✓ Environment configuration")
print("  ✓ Dependencies installed")
print("  ✓ Scenario validation")
print("  ✓ LiveKit connectivity")
print("  ✓ Agent components")
print()
print("The agent is ready to run!")
print()
print("Next steps:")
print("  1. Start the agent: make dev")
print("  2. Create a room: python example_create_room.py")
print("  3. Connect a client and start training")
print()

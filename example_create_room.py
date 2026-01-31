"""
Example: Creating a room with scenario metadata for DifficultAI LiveKit agent.

This script demonstrates how to create a LiveKit room with scenario configuration
that the DifficultAI agent will use to conduct a training conversation.
"""

import os
import json
from dotenv import load_dotenv

# Note: This requires livekit-api package
# Install with: pip install livekit-api

try:
    from livekit import api
except ImportError:
    print("Error: livekit-api not installed")
    print("Install with: pip install livekit-api")
    exit(1)

# Load environment variables
load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")


def create_training_room(
    room_name: str,
    persona_type: str = "ELITE_INTERVIEWER",
    company: str = "TechCorp",
    role: str = "Senior Software Engineer",
    stakes: str = "Final round interview for $250k position",
    user_goal: str = "Demonstrate technical expertise and secure job offer",
    difficulty: int = 3,
    voice: str = "marin"
):
    """
    Create a LiveKit room with DifficultAI scenario configuration.
    
    Args:
        room_name: Unique room name
        persona_type: Type of scenario (ANGRY_CUSTOMER, ELITE_INTERVIEWER, etc.)
        company: Company name
        role: User's role
        stakes: What's at stake
        user_goal: What user wants to achieve
        difficulty: Difficulty level 1-5
        voice: Voice name for TTS
    
    Returns:
        Room object
    """
    # Create scenario metadata
    scenario = {
        "persona_type": persona_type,
        "company": company,
        "role": role,
        "stakes": stakes,
        "user_goal": user_goal,
        "difficulty": difficulty,
        "voice": voice
    }
    
    # Create room service client
    room_service = api.RoomServiceClient(
        LIVEKIT_URL,
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET
    )
    
    # Create room with scenario metadata
    try:
        room = room_service.create_room(
            api.CreateRoomRequest(
                name=room_name,
                metadata=json.dumps(scenario)
            )
        )
        print(f"✓ Room created: {room.name}")
        print(f"✓ Scenario: {persona_type} - {company} - {role}")
        print(f"✓ Difficulty: {difficulty}/5")
        return room
    except Exception as e:
        print(f"✗ Error creating room: {e}")
        return None


def generate_participant_token(room_name: str, participant_identity: str, participant_name: str):
    """
    Generate a token for a participant to join the room.
    
    Args:
        room_name: Room name to join
        participant_identity: Unique participant ID
        participant_name: Display name
        
    Returns:
        JWT token string
    """
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(participant_identity)
    token.with_name(participant_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True
    ))
    
    return token.to_jwt()


def main():
    """Run example scenarios."""
    print("=" * 60)
    print("DifficultAI LiveKit Room Creation Examples")
    print("=" * 60)
    print()
    
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        print("✗ Error: Missing LiveKit credentials in .env")
        print("  Please set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")
        return
    
    # Example 1: Technical Interview
    print("Example 1: Elite Technical Interview")
    print("-" * 60)
    room1 = create_training_room(
        room_name="interview-001",
        persona_type="ELITE_INTERVIEWER",
        company="Google",
        role="Senior Software Engineer",
        stakes="L5 position with $250k total compensation",
        user_goal="Demonstrate deep systems knowledge and secure offer",
        difficulty=4,
        voice="marin"
    )
    
    if room1:
        # Generate token for a user
        token = generate_participant_token(
            room_name="interview-001",
            participant_identity="user-123",
            participant_name="John Doe"
        )
        print(f"✓ Participant token generated")
        print(f"  Token: {token[:50]}...")
        print()
    
    # Example 2: Customer Escalation
    print("Example 2: Angry Customer Escalation")
    print("-" * 60)
    room2 = create_training_room(
        room_name="customer-escalation-001",
        persona_type="ANGRY_CUSTOMER",
        company="Enterprise Solutions Corp",
        role="Customer Success Manager",
        stakes="Saving $2M annual contract threatening to cancel",
        user_goal="Calm customer and create resolution timeline",
        difficulty=3,
        voice="nova"
    )
    
    if room2:
        token = generate_participant_token(
            room_name="customer-escalation-001",
            participant_identity="user-456",
            participant_name="Jane Smith"
        )
        print(f"✓ Participant token generated")
        print()
    
    # Example 3: Investor Pitch
    print("Example 3: Skeptical Investor Pitch")
    print("-" * 60)
    room3 = create_training_room(
        room_name="investor-pitch-001",
        persona_type="SKEPTICAL_INVESTOR",
        company="StartupXYZ",
        role="CEO / Founder",
        stakes="Securing $3M seed funding to extend runway",
        user_goal="Convince investor of market opportunity and team capability",
        difficulty=5,
        voice="echo"
    )
    
    if room3:
        token = generate_participant_token(
            room_name="investor-pitch-001",
            participant_identity="user-789",
            participant_name="Alex Johnson"
        )
        print(f"✓ Participant token generated")
        print()
    
    print("=" * 60)
    print("Rooms created successfully!")
    print()
    print("Next steps:")
    print("1. Make sure DifficultAI agent is running:")
    print("   python apps/livekit_agent/agent.py dev")
    print()
    print("2. Connect to a room using the LiveKit SDK or web client")
    print("   Use the generated token for authentication")
    print()
    print("3. Have your training conversation!")
    print("=" * 60)


if __name__ == "__main__":
    main()

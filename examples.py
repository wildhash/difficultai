"""
Example scenarios demonstrating Difficult AI in action.

This script shows various conversation patterns and how the AI responds.
"""

from difficult_ai import DifficultAI
from unittest.mock import patch, MagicMock


def mock_openai_response(content):
    """Create a mock OpenAI response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def scenario_1_vague_responses():
    """Demonstrate AI escalation with vague responses."""
    print("\n" + "=" * 60)
    print("SCENARIO 1: User Gives Vague Responses")
    print("=" * 60 + "\n")
    
    with patch('difficult_ai.OpenAI') as mock_openai:
        agent = DifficultAI(api_key="test_key")
        mock_client = MagicMock()
        agent.client = mock_client
        
        # First vague response - difficulty level 1
        print("User: Maybe I'll work on the project sometime")
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Sometime? That's not a timeline. When EXACTLY will you start? Give me a specific date and time."
        )
        response = agent.chat("Maybe I'll work on the project sometime")
        print(f"AI (Difficulty {agent.difficulty_level}): {response}")
        print(f"Stats: Vague count = {agent.vague_response_count}\n")
        
        # Second vague response - difficulty increases
        print("User: Probably next week, I think")
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "STOP. 'Probably' and 'I think' are not commitments. I need a concrete answer: Which day next week, what time, and what specific action will you take?"
        )
        response = agent.chat("Probably next week, I think")
        print(f"AI (Difficulty {agent.difficulty_level}): {response}")
        print(f"Stats: Vague count = {agent.vague_response_count}\n")


def scenario_2_deflection():
    """Demonstrate AI response to deflection."""
    print("\n" + "=" * 60)
    print("SCENARIO 2: User Deflects Questions")
    print("=" * 60 + "\n")
    
    with patch('difficult_ai.OpenAI') as mock_openai:
        agent = DifficultAI(api_key="test_key")
        mock_client = MagicMock()
        agent.client = mock_client
        
        print("User: Let's talk about the budget first")
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "No. You're deflecting. I asked about your progress, not the budget. Answer the question: What have you accomplished?"
        )
        response = agent.chat("Let's talk about the budget first")
        print(f"AI (Difficulty {agent.difficulty_level}): {response}")
        print(f"Stats: Deflection count = {agent.deflection_count}\n")


def scenario_3_concrete_commitment():
    """Demonstrate AI response to concrete commitments."""
    print("\n" + "=" * 60)
    print("SCENARIO 3: User Makes Concrete Commitment")
    print("=" * 60 + "\n")
    
    with patch('difficult_ai.OpenAI') as mock_openai:
        agent = DifficultAI(api_key="test_key")
        mock_client = MagicMock()
        agent.client = mock_client
        
        print("User: I will deliver 10 completed units by Monday at 9am")
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Good. That's specific. 10 units, Monday, 9am. I'm holding you to that. What's your backup plan if something goes wrong?"
        )
        response = agent.chat("I will deliver 10 completed units by Monday at 9am")
        print(f"AI (Difficulty {agent.difficulty_level}): {response}")
        print(f"Stats: Commitments = {len(agent.commitments_made)}")
        if agent.commitments_made:
            print(f"Tracked: {agent.commitments_made[0]}\n")


def scenario_4_interruption():
    """Demonstrate AI response to user interruption."""
    print("\n" + "=" * 60)
    print("SCENARIO 4: User Interrupts the AI")
    print("=" * 60 + "\n")
    
    with patch('difficult_ai.OpenAI') as mock_openai:
        agent = DifficultAI(api_key="test_key")
        mock_client = MagicMock()
        agent.client = mock_client
        
        print("User: Wait, let me explain")
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Go ahead. I'm listening."
        )
        response = agent.chat("Wait, let me explain")
        print(f"AI: {response}")
        print(f"(AI detected interruption and stopped to listen)\n")


def scenario_5_difficulty_progression():
    """Demonstrate difficulty progression over time."""
    print("\n" + "=" * 60)
    print("SCENARIO 5: Difficulty Progression")
    print("=" * 60 + "\n")
    
    with patch('difficult_ai.OpenAI') as mock_openai:
        agent = DifficultAI(api_key="test_key")
        mock_client = MagicMock()
        agent.client = mock_client
        
        # Start at difficulty 1
        print(f"Initial Difficulty Level: {agent.difficulty_level}")
        
        # Multiple vague responses increase difficulty
        for i in range(3):
            agent._update_difficulty({"is_vague": True, "is_deflecting": False, "is_concrete": False})
            print(f"After vague response {i+1}: Difficulty = {agent.difficulty_level}")
        
        # Multiple deflections also increase difficulty
        for i in range(2):
            agent._update_difficulty({"is_vague": False, "is_deflecting": True, "is_concrete": False})
            print(f"After deflection {i+1}: Difficulty = {agent.difficulty_level}")
        
        print(f"\nFinal Difficulty Level: {agent.difficulty_level}/5")
        print(f"Vague responses: {agent.vague_response_count}")
        print(f"Deflections: {agent.deflection_count}\n")


def main():
    """Run all example scenarios."""
    print("\n" + "=" * 60)
    print("DIFFICULT AI - EXAMPLE SCENARIOS")
    print("=" * 60)
    print("\nThese examples demonstrate how Difficult AI responds to")
    print("different user behaviors and conversation patterns.\n")
    
    scenario_1_vague_responses()
    scenario_2_deflection()
    scenario_3_concrete_commitment()
    scenario_4_interruption()
    scenario_5_difficulty_progression()
    
    print("\n" + "=" * 60)
    print("For interactive testing, run: python difficult_ai.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

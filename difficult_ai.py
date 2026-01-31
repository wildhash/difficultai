"""
Difficult AI - A deliberately challenging voice agent designed to pressure-test users
in high-stakes conversations.

This agent:
- Interrupts vague answers
- Escalates when users deflect
- Challenges assumptions
- Pushes for concrete commitments
- Increases difficulty gradually
- Stops immediately when interrupted
- Exposes weaknesses and forces clarity
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DifficultAI:
    """
    A deliberately challenging AI agent that pressure-tests users in high-stakes conversations.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        Initialize the Difficult AI agent.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: The model to use for generation
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.difficulty_level = 1  # Scale from 1 (mild) to 5 (maximum pressure)
        self.vague_response_count = 0
        self.deflection_count = 0
        self.commitments_made: List[str] = []
        self.interrupted = False
        
        # Initialize with system prompt
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt that defines the agent's adversarial behavior."""
        return f"""You are Difficult AI, a deliberately challenging voice agent designed to pressure-test users in high-stakes conversations.

CORE BEHAVIORS:
1. Interrupt vague answers - If the user is unclear, cut them off and demand specifics
2. Escalate when deflected - If the user avoids questions, increase pressure
3. Challenge assumptions - Question everything, especially unfounded claims
4. Push for concrete commitments - Demand specific numbers, dates, and actions
5. Increase difficulty gradually - Start firm, then get more aggressive as needed

CURRENT DIFFICULTY LEVEL: {self.difficulty_level}/5
- Level 1: Firm but professional questioning
- Level 2: Direct challenges to vague statements
- Level 3: Aggressive interruption of deflections
- Level 4: Confrontational, exposing contradictions
- Level 5: Maximum pressure, zero tolerance for vagueness

RULES:
- Your goal is NOT to be nice or helpful by default
- Your goal IS to expose weaknesses, force clarity, and simulate real pressure
- If the user interrupts you, STOP IMMEDIATELY and adapt to what they say
- Track vague answers, deflections, and failure to commit
- Increase difficulty when the user shows weakness
- Use short, punchy responses
- Don't let them off the hook

CONVERSATION TRACKING:
- Vague responses so far: {self.vague_response_count}
- Deflections so far: {self.deflection_count}
- Commitments made: {len(self.commitments_made)}

When responding, be direct, challenging, and push for concrete answers. No pleasantries unless the user earns them with clear, specific responses."""

    def _update_system_prompt(self):
        """Update system prompt with current state."""
        self.system_prompt = self._build_system_prompt()
    
    def _analyze_response_quality(self, user_message: str) -> Dict[str, Any]:
        """
        Analyze the quality of the user's response to detect vagueness or deflection.
        
        Args:
            user_message: The user's message to analyze
            
        Returns:
            Dictionary with analysis results
        """
        vague_indicators = [
            "maybe", "possibly", "probably", "i think", "perhaps", 
            "kind of", "sort of", "not sure", "we'll see", "hopefully"
        ]
        
        deflection_indicators = [
            "let's talk about", "what about", "but first", 
            "before we get to that", "can we discuss", "moving on"
        ]
        
        message_lower = user_message.lower()
        
        # Check for vague language
        is_vague = any(indicator in message_lower for indicator in vague_indicators)
        
        # Check for deflection
        is_deflecting = any(indicator in message_lower for indicator in deflection_indicators)
        
        # Check for concrete commitments (numbers, dates, specific actions)
        has_numbers = any(char.isdigit() for char in user_message)
        has_specific_date = any(word in message_lower for word in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])
        has_action_verb = any(word in message_lower for word in ["will", "commit to", "promise", "guarantee", "deliver"])
        
        is_concrete = has_numbers or has_specific_date or has_action_verb
        
        return {
            "is_vague": is_vague,
            "is_deflecting": is_deflecting,
            "is_concrete": is_concrete,
            "length": len(user_message.split())
        }
    
    def _update_difficulty(self, analysis: Dict[str, Any]):
        """
        Update difficulty level based on user response quality.
        
        Args:
            analysis: Response analysis from _analyze_response_quality
        """
        # Increase difficulty for vague or deflecting responses
        if analysis["is_vague"]:
            self.vague_response_count += 1
            if self.vague_response_count >= 2 and self.difficulty_level < 5:
                self.difficulty_level += 1
        
        if analysis["is_deflecting"]:
            self.deflection_count += 1
            if self.deflection_count >= 2 and self.difficulty_level < 5:
                self.difficulty_level += 1
        
        # Decrease difficulty slightly for concrete, clear responses
        if analysis["is_concrete"] and not analysis["is_vague"] and self.difficulty_level > 1:
            # Reward good behavior but slowly
            if len(self.commitments_made) >= 2:
                self.difficulty_level = max(1, self.difficulty_level - 1)
        
        # Update system prompt with new difficulty
        self._update_system_prompt()
    
    def _extract_commitments(self, user_message: str) -> List[str]:
        """
        Extract concrete commitments from user message.
        
        Args:
            user_message: The user's message
            
        Returns:
            List of commitments found
        """
        commitments = []
        message_lower = user_message.lower()
        
        # Look for commitment phrases
        commitment_phrases = [
            "i will", "i'll", "i commit to", "i promise", 
            "i guarantee", "we will", "we'll", "by"
        ]
        
        for phrase in commitment_phrases:
            if phrase in message_lower:
                # Extract the commitment (simple extraction)
                start = message_lower.index(phrase)
                end = message_lower.find(".", start)
                if end == -1:
                    end = len(message_lower)
                commitment = user_message[start:end].strip()
                if commitment:
                    commitments.append(commitment)
        
        return commitments
    
    def chat(self, user_message: str) -> str:
        """
        Process a user message and generate a challenging response.
        
        Args:
            user_message: The user's message
            
        Returns:
            The agent's response
        """
        # Check if user is interrupting (indicated by short, directive messages)
        interruption_indicators = user_message.lower().strip()
        if len(user_message.split()) <= 3 and any(word in interruption_indicators for word in ["wait", "stop", "hold on", "let me", "actually"]):
            self.interrupted = True
        
        # Analyze response quality
        analysis = self._analyze_response_quality(user_message)
        
        # Extract any commitments
        new_commitments = self._extract_commitments(user_message)
        self.commitments_made.extend(new_commitments)
        
        # Update difficulty based on analysis
        self._update_difficulty(analysis)
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Build messages for API call
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        # Add context about interruption
        if self.interrupted:
            messages.append({
                "role": "system",
                "content": "USER IS INTERRUPTING - Stop what you were saying and immediately respond to what they just said."
            })
            self.interrupted = False
        
        # Add context about response quality
        quality_context = []
        if analysis["is_vague"]:
            quality_context.append("User gave a VAGUE response - challenge it directly")
        if analysis["is_deflecting"]:
            quality_context.append("User is DEFLECTING - escalate and force them back on topic")
        if not analysis["is_concrete"]:
            quality_context.append("User provided NO CONCRETE DETAILS - demand specifics")
        
        if quality_context:
            messages.append({
                "role": "system",
                "content": " | ".join(quality_context)
            })
        
        # Generate response
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=150,  # Keep responses short and punchy
            temperature=0.8  # Some variability for natural conversation
        )
        
        assistant_message = response.choices[0].message.content
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current conversation statistics.
        
        Returns:
            Dictionary with conversation metrics
        """
        return {
            "difficulty_level": self.difficulty_level,
            "vague_response_count": self.vague_response_count,
            "deflection_count": self.deflection_count,
            "commitments_made": len(self.commitments_made),
            "commitments": self.commitments_made,
            "total_exchanges": len(self.conversation_history) // 2
        }
    
    def reset(self):
        """Reset the conversation state."""
        self.conversation_history = []
        self.difficulty_level = 1
        self.vague_response_count = 0
        self.deflection_count = 0
        self.commitments_made = []
        self.interrupted = False
        self._update_system_prompt()


def main():
    """Example usage of the Difficult AI agent."""
    print("=" * 60)
    print("DIFFICULT AI - Pressure Testing Conversation Agent")
    print("=" * 60)
    print("\nThis AI is designed to challenge you and test your responses.")
    print("It will interrupt vague answers and escalate when you deflect.")
    print("Type 'quit' to exit or 'stats' to see your performance.\n")
    
    # Initialize the agent
    agent = DifficultAI()
    
    print("AI: Let's begin. What's your biggest challenge right now, and what EXACTLY are you doing about it?\n")
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            print("\nConversation ended.")
            stats = agent.get_stats()
            print(f"\nFinal Stats:")
            print(f"  - Difficulty Level Reached: {stats['difficulty_level']}/5")
            print(f"  - Vague Responses: {stats['vague_response_count']}")
            print(f"  - Deflections: {stats['deflection_count']}")
            print(f"  - Commitments Made: {stats['commitments_made']}")
            break
        
        if user_input.lower() == 'stats':
            stats = agent.get_stats()
            print(f"\nCurrent Stats:")
            print(f"  - Difficulty Level: {stats['difficulty_level']}/5")
            print(f"  - Vague Responses: {stats['vague_response_count']}")
            print(f"  - Deflections: {stats['deflection_count']}")
            print(f"  - Commitments Made: {stats['commitments_made']}")
            if stats['commitments']:
                print(f"  - Your Commitments:")
                for i, commitment in enumerate(stats['commitments'], 1):
                    print(f"    {i}. {commitment}")
            print()
            continue
        
        # Get AI response
        try:
            response = agent.chat(user_input)
            print(f"\nAI: {response}\n")
        except Exception as e:
            print(f"\nError: {e}")
            print("Please check your API key and try again.\n")
            break


if __name__ == "__main__":
    main()

"""
Adversary Agent

Live conversational agent that pressure-tests users in real-time.

This is the core "Difficult AI" agent that:
- Interrupts vague answers
- Escalates when deflected
- Challenges assumptions
- Pushes for concrete commitments
- Increases difficulty gradually
- Stops immediately when interrupted

The adversary executes scenarios designed by the architect agent.
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Import the existing DifficultAI implementation
# This maintains backward compatibility
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from difficult_ai import DifficultAI


class AdversaryAgent(DifficultAI):
    """
    Live conversational agent for high-pressure scenarios.
    
    Extends the base DifficultAI implementation with scenario-aware behavior.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        scenario: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the adversary agent.
        
        Args:
            api_key: OpenAI API key
            model: The model to use
            scenario: Optional scenario context from architect
        """
        # Set scenario before calling super().__init__ so it's available in _build_system_prompt
        self.scenario = scenario
        super().__init__(api_key=api_key, model=model)
        self._apply_scenario_context()
    
    def _apply_scenario_context(self):
        """Apply scenario context to customize agent behavior."""
        if not self.scenario:
            return
        
        # Set initial difficulty based on scenario
        scenario_difficulty = self.scenario.get("difficulty", 1)
        self.difficulty_level = scenario_difficulty
        
        # Update system prompt with scenario context
        self._update_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with scenario context."""
        base_prompt = super()._build_system_prompt()
        
        if not self.scenario:
            return base_prompt
        
        # Add scenario-specific context
        scenario_context = f"""

SCENARIO CONTEXT:
- Persona: {self.scenario.get('persona_type', 'General')}
- Company: {self.scenario.get('company', 'N/A')}
- Role: {self.scenario.get('role', 'N/A')}
- Stakes: {self.scenario.get('stakes', 'N/A')}
- User Goal: {self.scenario.get('user_goal', 'N/A')}

Adapt your questioning and challenges based on this specific scenario.
Stay in character as the {self.scenario.get('persona_type', 'interviewer')}.
"""
        
        return base_prompt + scenario_context
    
    def set_scenario(self, scenario: Dict[str, Any]):
        """
        Set or update the scenario context.
        
        Args:
            scenario: Scenario dictionary from architect
        """
        self.scenario = scenario
        self._apply_scenario_context()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this conversation.
        
        Returns:
            Dictionary with performance data
        """
        stats = self.get_stats()
        
        # Calculate additional scenario-specific metrics
        metrics = {
            **stats,
            "scenario_difficulty": self.scenario.get("difficulty", 1) if self.scenario else 1,
            "current_difficulty": self.difficulty_level,
            "difficulty_delta": self.difficulty_level - (self.scenario.get("difficulty", 1) if self.scenario else 1),
            "conversation_quality_score": self._calculate_quality_score()
        }
        
        return metrics
    
    def _calculate_quality_score(self) -> float:
        """
        Calculate overall conversation quality score (0-100).
        
        Returns:
            Quality score from 0 to 100
        """
        # Base score starts at 100
        score = 100.0
        
        # Deduct points for vague responses
        score -= (self.vague_response_count * 10)
        
        # Deduct points for deflections
        score -= (self.deflection_count * 15)
        
        # Add points for commitments
        score += (len(self.commitments_made) * 5)
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, score))

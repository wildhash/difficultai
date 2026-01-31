"""
Architect Agent

Designs interview scenarios and conversation structures based on:
- Persona type (e.g., ANGRY_CUSTOMER, ELITE_INTERVIEWER)
- Company and role context
- Difficulty level
- User goals and stakes

The architect creates the blueprint that other agents execute.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PersonaType(Enum):
    """Supported persona types for scenarios."""
    ANGRY_CUSTOMER = "ANGRY_CUSTOMER"
    ELITE_INTERVIEWER = "ELITE_INTERVIEWER"
    TOUGH_NEGOTIATOR = "TOUGH_NEGOTIATOR"
    SKEPTICAL_INVESTOR = "SKEPTICAL_INVESTOR"
    DEMANDING_CLIENT = "DEMANDING_CLIENT"


@dataclass
class Scenario:
    """
    Scenario contract that defines a high-pressure conversation.
    
    This structure is shared across all agents (research → adversary → evaluator).
    
    Canonical ScenarioConfig fields:
    - persona: PersonaType enum (ANGRY_CUSTOMER, ELITE_INTERVIEWER, etc.)
    - difficulty: float 0-1 (0 = easy, 1 = maximum pressure)
    - company: str
    - role: str
    - goals: str (user_goal)
    """
    persona_type: PersonaType  # Also referred to as "persona"
    company: str
    role: str
    stakes: str
    user_goal: str  # Also referred to as "goals"
    difficulty: float  # 0-1 scale (0 = easy, 1 = maximum pressure)
    source_docs: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary."""
        return {
            "persona_type": self.persona_type.value,
            "persona": self.persona_type.value,  # Alias for consistency
            "company": self.company,
            "role": self.role,
            "stakes": self.stakes,
            "user_goal": self.user_goal,
            "goals": self.user_goal,  # Alias for consistency
            "difficulty": self.difficulty,
            "source_docs": self.source_docs or []
        }


class ArchitectAgent:
    """
    Designs interview and scenario structures.
    
    The architect agent creates customized scenarios based on user requirements,
    ensuring each conversation has clear objectives, appropriate difficulty,
    and well-defined success criteria.
    """
    
    def __init__(self):
        """Initialize the architect agent."""
        self.scenarios: List[Scenario] = []
    
    def design_scenario(
        self,
        persona_type: PersonaType,
        company: str,
        role: str,
        stakes: str,
        user_goal: str,
        difficulty: int = 3,
        source_docs: Optional[List[str]] = None
    ) -> Scenario:
        """
        Design a new scenario for a high-pressure conversation.
        
        Args:
            persona_type: The type of persona to simulate
            company: Target company name
            role: Target role/position
            stakes: What's at stake in this conversation
            user_goal: What the user is trying to achieve
            difficulty: Difficulty level (1-5)
            source_docs: Optional source documents for context
            
        Returns:
            A designed Scenario object
        """
        if not 1 <= difficulty <= 5:
            raise ValueError("Difficulty must be between 1 and 5")
        
        scenario = Scenario(
            persona_type=persona_type,
            company=company,
            role=role,
            stakes=stakes,
            user_goal=user_goal,
            difficulty=difficulty,
            source_docs=source_docs
        )
        
        self.scenarios.append(scenario)
        return scenario
    
    def get_scenario_template(self, persona_type: PersonaType) -> Dict[str, Any]:
        """
        Get a template for a specific persona type.
        
        Args:
            persona_type: The persona type to get a template for
            
        Returns:
            Template dictionary with suggested structure
        """
        templates = {
            PersonaType.ANGRY_CUSTOMER: {
                "description": "Frustrated customer demanding immediate resolution",
                "key_behaviors": [
                    "Express frustration and urgency",
                    "Demand specific timelines",
                    "Question competence if vague",
                    "Escalate when deflected"
                ],
                "success_criteria": [
                    "Clear resolution timeline provided",
                    "Specific action items committed",
                    "Customer concerns acknowledged"
                ]
            },
            PersonaType.ELITE_INTERVIEWER: {
                "description": "Senior interviewer testing technical and cultural fit",
                "key_behaviors": [
                    "Ask probing technical questions",
                    "Challenge assumptions",
                    "Test depth of knowledge",
                    "Evaluate communication clarity"
                ],
                "success_criteria": [
                    "Clear, confident answers",
                    "Demonstrated expertise",
                    "Good problem-solving approach"
                ]
            },
            PersonaType.TOUGH_NEGOTIATOR: {
                "description": "Experienced negotiator seeking best deal",
                "key_behaviors": [
                    "Push for concessions",
                    "Question value propositions",
                    "Test boundaries",
                    "Seek leverage"
                ],
                "success_criteria": [
                    "Clear value articulation",
                    "Strategic concessions",
                    "Maintained boundaries"
                ]
            },
            PersonaType.SKEPTICAL_INVESTOR: {
                "description": "Investor questioning business fundamentals",
                "key_behaviors": [
                    "Demand data and metrics",
                    "Challenge assumptions",
                    "Question market fit",
                    "Test business acumen"
                ],
                "success_criteria": [
                    "Data-driven responses",
                    "Clear market understanding",
                    "Realistic projections"
                ]
            },
            PersonaType.DEMANDING_CLIENT: {
                "description": "High-value client with strict requirements",
                "key_behaviors": [
                    "Set high expectations",
                    "Demand guarantees",
                    "Test reliability",
                    "Require detailed planning"
                ],
                "success_criteria": [
                    "Specific deliverables outlined",
                    "Realistic commitments made",
                    "Risk mitigation addressed"
                ]
            }
        }
        
        return templates.get(persona_type, {})
    
    def validate_scenario(self, scenario: Scenario) -> List[str]:
        """
        Validate a scenario for completeness and coherence.
        
        Args:
            scenario: The scenario to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        if not scenario.company:
            issues.append("Company name is required")
        
        if not scenario.role:
            issues.append("Role is required")
        
        if not scenario.stakes:
            issues.append("Stakes must be defined")
        
        if not scenario.user_goal:
            issues.append("User goal must be specified")
        
        if not 1 <= scenario.difficulty <= 5:
            issues.append("Difficulty must be between 1 and 5")
        
        return issues

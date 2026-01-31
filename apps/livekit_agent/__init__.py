"""
LiveKit Agent Runtime

This is a first-class agent runtime for DifficultAI, not a background worker.

The LiveKit agent handles real-time voice interactions, managing the flow
between the architect, researcher, adversary, and evaluator agents.
"""

import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can import from the parent directory
sys.path.insert(0, os.path.dirname(parent_dir))

from agents import ArchitectAgent, ResearcherAgent, AdversaryAgent, EvaluatorAgent
from agents.architect import PersonaType


class LiveKitAgentRuntime:
    """
    First-class agent runtime for real-time voice interactions.
    
    This orchestrates the full agent workflow:
    1. Architect designs the scenario
    2. Researcher gathers context
    3. Adversary runs the live conversation
    4. Evaluator scores and provides feedback
    """
    
    def __init__(self):
        """Initialize the LiveKit agent runtime."""
        self.architect = ArchitectAgent()
        self.researcher = ResearcherAgent()
        self.adversary = None  # Initialized per session
        self.evaluator = EvaluatorAgent()
    
    def setup_scenario(
        self,
        persona_type: PersonaType,
        company: str,
        role: str,
        stakes: str,
        user_goal: str,
        difficulty: int = 3,
        source_docs: list = None
    ):
        """
        Set up a new scenario using the architect and researcher.
        
        Args:
            persona_type: Type of persona to simulate
            company: Company name
            role: Role/position
            stakes: What's at stake
            user_goal: User's objective
            difficulty: Difficulty level (1-5)
            source_docs: Optional source documents
            
        Returns:
            Configured scenario
        """
        # Design the scenario
        scenario = self.architect.design_scenario(
            persona_type=persona_type,
            company=company,
            role=role,
            stakes=stakes,
            user_goal=user_goal,
            difficulty=difficulty,
            source_docs=source_docs
        )
        
        # Research company and role
        company_context = self.researcher.research_company(company, source_docs)
        role_context = self.researcher.research_role(role, company_context)
        
        # Generate context summary
        context_summary = self.researcher.generate_context_summary(
            company_context,
            role_context
        )
        
        print(f"Scenario prepared:\n{context_summary}\n")
        
        return scenario
    
    def start_conversation(self, scenario_dict: dict, api_key: str = None):
        """
        Start a live conversation with the adversary agent.
        
        Args:
            scenario_dict: Scenario configuration
            api_key: OpenAI API key
            
        Returns:
            Initialized adversary agent
        """
        self.adversary = AdversaryAgent(
            api_key=api_key,
            scenario=scenario_dict
        )
        
        print(f"Starting conversation as {scenario_dict.get('persona_type', 'interviewer')}...\n")
        
        return self.adversary
    
    def complete_conversation(self):
        """
        Complete the conversation and generate evaluation.
        
        Returns:
            Evaluation results
        """
        if not self.adversary:
            raise RuntimeError("No active conversation to evaluate")
        
        # Get performance metrics from adversary
        metrics = self.adversary.get_performance_metrics()
        
        # Get scenario context
        scenario = self.adversary.scenario
        
        # Evaluate performance
        evaluation = self.evaluator.evaluate_conversation(
            metrics=metrics,
            scenario=scenario
        )
        
        # Generate and print report
        report = self.evaluator.get_summary_report(evaluation)
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)
        
        return evaluation


def main():
    """Example usage of the LiveKit agent runtime."""
    print("=" * 60)
    print("DIFFICULT AI - LiveKit Agent Runtime")
    print("=" * 60)
    print()
    
    # Initialize runtime
    runtime = LiveKitAgentRuntime()
    
    # Set up a scenario
    print("Setting up scenario...")
    scenario = runtime.setup_scenario(
        persona_type=PersonaType.ELITE_INTERVIEWER,
        company="TechCorp",
        role="Senior Software Engineer",
        stakes="High-stakes technical interview for dream job",
        user_goal="Demonstrate technical expertise and problem-solving skills",
        difficulty=3
    )
    
    print("Scenario ready. In a real LiveKit integration, the conversation would start now.")
    print(f"Persona: {scenario.persona_type.value}")
    print(f"Difficulty: {scenario.difficulty}/5")
    print()
    
    # Note: In a real implementation, this would connect to LiveKit
    # and handle real-time voice interaction
    print("Note: This is the agent runtime. For interactive testing,")
    print("use the existing difficult_ai.py script.")


if __name__ == "__main__":
    main()

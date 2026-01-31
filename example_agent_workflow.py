"""
Example: Full Agent Workflow

This example demonstrates the complete DifficultAI agent workflow:
1. Architect designs the scenario
2. Researcher gathers context
3. Adversary runs the conversation (simulated)
4. Evaluator provides feedback
"""

from agents import ArchitectAgent, ResearcherAgent, AdversaryAgent, EvaluatorAgent
from agents.architect import PersonaType


def demonstrate_full_workflow():
    """Demonstrate the complete agent workflow."""
    print("=" * 70)
    print("DIFFICULT AI - COMPLETE AGENT WORKFLOW DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Step 1: Architect designs the scenario
    print("STEP 1: ARCHITECT - Designing Scenario")
    print("-" * 70)
    
    architect = ArchitectAgent()
    scenario = architect.design_scenario(
        persona_type=PersonaType.ELITE_INTERVIEWER,
        company="TechCorp",
        role="Senior Software Engineer",
        stakes="Final round interview for $250k position",
        user_goal="Demonstrate technical expertise and secure job offer",
        difficulty=3
    )
    
    print(f"Persona Type: {scenario.persona_type.value}")
    print(f"Company: {scenario.company}")
    print(f"Role: {scenario.role}")
    print(f"Stakes: {scenario.stakes}")
    print(f"User Goal: {scenario.user_goal}")
    print(f"Difficulty: {scenario.difficulty}/5")
    
    # Validate scenario
    issues = architect.validate_scenario(scenario)
    print(f"Validation: {'✓ Passed' if not issues else '✗ Failed'}")
    print()
    
    # Step 2: Researcher gathers context
    print("STEP 2: RESEARCHER - Gathering Context")
    print("-" * 70)
    
    researcher = ResearcherAgent()
    
    # Research company
    company_context = researcher.research_company("TechCorp")
    print(f"Company Industry: {company_context.industry}")
    print(f"Company Culture: {company_context.culture}")
    print(f"Company Values: {', '.join(company_context.key_values or [])}")
    
    # Research role
    role_context = researcher.research_role("Senior Software Engineer", company_context)
    print(f"Role Level: {role_context.level}")
    print(f"Key Skills: {', '.join(role_context.key_skills)}")
    
    # Generate summary
    context_summary = researcher.generate_context_summary(company_context, role_context)
    print("\nContext Summary:")
    print(context_summary)
    print()
    
    # Step 3: Adversary runs conversation (simulated)
    print("STEP 3: ADVERSARY - Running Conversation (Simulated)")
    print("-" * 70)
    
    # Note: In a real scenario, this would connect to OpenAI
    # For this demo, we'll simulate the conversation metrics
    from unittest.mock import MagicMock
    
    # Create a mock adversary
    adversary = MagicMock()
    adversary.scenario = scenario.to_dict()
    adversary.vague_response_count = 1
    adversary.deflection_count = 0
    adversary.commitments_made = [
        "I will complete the technical assessment by Friday",
        "I can start within 2 weeks"
    ]
    adversary.difficulty_level = 3
    adversary.conversation_history = [
        {"role": "user", "content": "Tell me about your experience"},
        {"role": "assistant", "content": "Can you be more specific?"},
        {"role": "user", "content": "I have 5 years working on distributed systems"},
        {"role": "assistant", "content": "Good. What specific technologies?"},
        {"role": "user", "content": "Kubernetes, Docker, and I will complete the assessment by Friday"},
        {"role": "assistant", "content": "When can you start?"},
        {"role": "user", "content": "I can start within 2 weeks"},
    ]
    
    # Get metrics
    metrics = {
        "vague_response_count": adversary.vague_response_count,
        "deflection_count": adversary.deflection_count,
        "commitments_made": len(adversary.commitments_made),
        "total_exchanges": len(adversary.conversation_history) // 2,
        "current_difficulty": adversary.difficulty_level,
        "scenario_difficulty": scenario.difficulty
    }
    
    print(f"Conversation Exchanges: {metrics['total_exchanges']}")
    print(f"Vague Responses: {metrics['vague_response_count']}")
    print(f"Deflections: {metrics['deflection_count']}")
    print(f"Commitments Made: {metrics['commitments_made']}")
    print(f"Final Difficulty: {metrics['current_difficulty']}/5")
    print()
    
    # Step 4: Evaluator provides feedback
    print("STEP 4: EVALUATOR - Analyzing Performance")
    print("-" * 70)
    
    evaluator = EvaluatorAgent()
    evaluation = evaluator.evaluate_conversation(
        metrics=metrics,
        scenario=scenario.to_dict(),
        transcript=adversary.conversation_history
    )
    
    # Display evaluation report
    report = evaluator.get_summary_report(evaluation)
    print(report)
    print()
    
    # Summary
    print("=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print()
    print("The agent workflow successfully:")
    print("  1. ✓ Designed a customized scenario")
    print("  2. ✓ Gathered relevant context")
    print("  3. ✓ Simulated a high-pressure conversation")
    print("  4. ✓ Evaluated performance with actionable feedback")
    print()
    print("This demonstrates how DifficultAI transforms from a single chatbot")
    print("into an agentic workforce that can scale without refactors.")
    print()


def demonstrate_scenario_contract():
    """Demonstrate the scenario contract in action."""
    print("=" * 70)
    print("SCENARIO CONTRACT DEMONSTRATION")
    print("=" * 70)
    print()
    
    print("The scenario contract allows all agents to reason over the same object:")
    print()
    
    # Create different scenarios
    scenarios = [
        {
            "name": "Technical Interview",
            "persona": PersonaType.ELITE_INTERVIEWER,
            "company": "Google",
            "role": "Senior SWE",
            "stakes": "L5 position with $250k comp",
            "goal": "Demonstrate systems expertise",
            "difficulty": 4
        },
        {
            "name": "Customer Escalation",
            "persona": PersonaType.ANGRY_CUSTOMER,
            "company": "Enterprise Corp",
            "role": "CSM",
            "stakes": "$2M contract at risk",
            "goal": "Calm customer and create recovery plan",
            "difficulty": 3
        },
        {
            "name": "Investor Pitch",
            "persona": PersonaType.SKEPTICAL_INVESTOR,
            "company": "StartupXYZ",
            "role": "CEO",
            "stakes": "$3M seed funding",
            "goal": "Convince investor of opportunity",
            "difficulty": 4
        }
    ]
    
    architect = ArchitectAgent()
    
    for s in scenarios:
        scenario = architect.design_scenario(
            persona_type=s["persona"],
            company=s["company"],
            role=s["role"],
            stakes=s["stakes"],
            user_goal=s["goal"],
            difficulty=s["difficulty"]
        )
        
        print(f"Scenario: {s['name']}")
        print(f"  Persona: {scenario.persona_type.value}")
        print(f"  Company: {scenario.company}")
        print(f"  Stakes: {scenario.stakes}")
        print(f"  Difficulty: {scenario.difficulty}/5")
        
        # Get template
        template = architect.get_scenario_template(scenario.persona_type)
        print(f"  Behaviors: {len(template.get('key_behaviors', []))} defined")
        print(f"  Success Criteria: {len(template.get('success_criteria', []))} defined")
        print()
    
    print("All scenarios follow the same contract structure, making them")
    print("interchangeable across the architect → adversary → evaluator pipeline.")
    print()


if __name__ == "__main__":
    # Run full workflow demo
    demonstrate_full_workflow()
    
    # Run scenario contract demo
    print("\n\n")
    demonstrate_scenario_contract()

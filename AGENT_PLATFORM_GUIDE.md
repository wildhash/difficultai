# Getting Started with the Agent Platform

This guide helps you understand and use the new DifficultAI agent platform.

## Quick Start

### 1. Simple Usage (Legacy - Still Works)

For basic conversations, the original interface still works:

```python
from difficult_ai import DifficultAI

agent = DifficultAI()
response = agent.chat("I'm thinking about maybe working on this project")
print(response)  # AI will challenge the vague response
```

### 2. Agent Platform Usage (New)

For full control over scenarios, context, and evaluation:

```python
from agents import ArchitectAgent, ResearcherAgent, AdversaryAgent, EvaluatorAgent
from agents.architect import PersonaType

# Step 1: Design a scenario
architect = ArchitectAgent()
scenario = architect.design_scenario(
    persona_type=PersonaType.ELITE_INTERVIEWER,
    company="Google",
    role="Senior Software Engineer",
    stakes="L5 position with $250k compensation",
    user_goal="Demonstrate technical expertise and secure offer",
    difficulty=4
)

# Step 2: Research context
researcher = ResearcherAgent()
company_context = researcher.research_company("Google")
role_context = researcher.research_role("Senior Software Engineer", company_context)

# Step 3: Run conversation
adversary = AdversaryAgent(scenario=scenario.to_dict())
response = adversary.chat("I have experience with distributed systems")
# ... continue conversation ...

# Step 4: Evaluate performance
evaluator = EvaluatorAgent()
metrics = adversary.get_performance_metrics()
evaluation = evaluator.evaluate_conversation(metrics, scenario.to_dict())

# Get feedback
report = evaluator.get_summary_report(evaluation)
print(report)
```

### 3. LiveKit Runtime (Production)

For production voice applications:

```python
from apps.livekit_agent import LiveKitAgentRuntime
from agents.architect import PersonaType

runtime = LiveKitAgentRuntime()

# Setup
scenario = runtime.setup_scenario(
    persona_type=PersonaType.ANGRY_CUSTOMER,
    company="MyCompany",
    role="Customer Success Manager",
    stakes="$2M contract at risk",
    user_goal="Retain customer and create resolution plan",
    difficulty=3
)

# Start conversation (connects to LiveKit in production)
adversary = runtime.start_conversation(scenario.to_dict(), api_key="sk-...")

# After conversation completes
evaluation = runtime.complete_conversation()
```

## Understanding the Agent Roles

### Architect Agent
**Purpose:** Designs scenarios with specific goals and difficulty levels

**When to use:**
- Creating custom training scenarios
- Adjusting difficulty levels
- Defining success criteria

**Example:**
```python
from agents import ArchitectAgent
from agents.architect import PersonaType

architect = ArchitectAgent()

# Design a tough negotiation scenario
scenario = architect.design_scenario(
    persona_type=PersonaType.TOUGH_NEGOTIATOR,
    company="BigCorp",
    role="Account Manager",
    stakes="$500k contract renewal with 30% price increase",
    user_goal="Maintain pricing while retaining customer",
    difficulty=4
)

# Get template for scenario type
template = architect.get_scenario_template(PersonaType.TOUGH_NEGOTIATOR)
print(template['key_behaviors'])  # See expected AI behaviors
```

### Researcher Agent
**Purpose:** Gathers company and role context to make scenarios realistic

**When to use:**
- Before starting conversations
- When you have company documents
- To customize context

**Example:**
```python
from agents import ResearcherAgent

researcher = ResearcherAgent()

# Research context
company = researcher.research_company("TechCorp", source_docs=["company_info.pdf"])
role = researcher.research_role("Product Manager", company)

# Get talking points
points = researcher.extract_talking_points(company, role)
print(points)  # Use in conversation prep
```

### Adversary Agent
**Purpose:** Runs the actual challenging conversation

**When to use:**
- For live training sessions
- When you need scenario-aware behavior
- To track performance metrics

**Example:**
```python
from agents import AdversaryAgent

# Create with scenario context
scenario = {
    "persona_type": "SKEPTICAL_INVESTOR",
    "company": "StartupXYZ",
    "role": "CEO",
    "difficulty": 5
}

adversary = AdversaryAgent(scenario=scenario)

# Conversation
response1 = adversary.chat("Our TAM is $10B")
response2 = adversary.chat("We have 50% month-over-month growth")

# Get metrics
metrics = adversary.get_performance_metrics()
print(f"Quality Score: {metrics['conversation_quality_score']}/100")
```

### Evaluator Agent
**Purpose:** Analyzes performance and provides actionable feedback

**When to use:**
- After conversations complete
- To track improvement over time
- To identify specific weaknesses

**Example:**
```python
from agents import EvaluatorAgent

evaluator = EvaluatorAgent()

# Evaluate
evaluation = evaluator.evaluate_conversation(
    metrics=adversary.get_performance_metrics(),
    scenario=scenario
)

# See scores
scores = evaluation['scores']
print(f"Clarity: {scores['clarity']}/100")
print(f"Confidence: {scores['confidence']}/100")
print(f"Commitment: {scores['commitment']}/100")
print(f"Overall: {scores['overall']}/100")

# Get feedback
feedback = evaluation['feedback']
print("Strengths:", feedback['strengths'])
print("Weaknesses:", feedback['weaknesses'])
print("Recommendations:", feedback['recommendations'])
```

## Scenario Contract

All agents work with the same scenario object. See [docs/scenario_contract.md](docs/scenario_contract.md) for details.

**Key fields:**
- `persona_type`: Type of AI personality (ANGRY_CUSTOMER, ELITE_INTERVIEWER, etc.)
- `company`: Target company name
- `role`: User's role in the scenario
- `stakes`: What's at risk
- `user_goal`: What success looks like
- `difficulty`: 1-5 scale
- `source_docs`: Optional context documents

## Testing

Run tests to verify everything works:

```bash
# Test all components
python -m unittest discover -p "test_*.py"

# Test specific agent
python -m unittest test_agents.TestArchitectAgent -v

# See full workflow demo
python example_agent_workflow.py
```

## Common Patterns

### Pattern 1: Quick Training Session
```python
from difficult_ai import DifficultAI

agent = DifficultAI()
# Just start chatting - good for quick practice
```

### Pattern 2: Custom Scenario
```python
from agents import ArchitectAgent, AdversaryAgent

# Design custom scenario
architect = ArchitectAgent()
scenario = architect.design_scenario(...)

# Run with that scenario
adversary = AdversaryAgent(scenario=scenario.to_dict())
```

### Pattern 3: Full Pipeline with Evaluation
```python
from apps.livekit_agent import LiveKitAgentRuntime

runtime = LiveKitAgentRuntime()
scenario = runtime.setup_scenario(...)
adversary = runtime.start_conversation(scenario.to_dict())
# ... conversation ...
evaluation = runtime.complete_conversation()
```

## Migration from Old Code

If you have existing code using `difficult_ai.py`, no changes needed:

```python
# This still works exactly as before
from difficult_ai import DifficultAI

agent = DifficultAI()
response = agent.chat("user message")
```

To upgrade to the new platform, wrap in AdversaryAgent:

```python
# New platform-aware version
from agents import AdversaryAgent

# Works the same, but scenario-aware
adversary = AdversaryAgent(scenario=scenario_dict)
response = adversary.chat("user message")
```

## Next Steps

1. Try the simple example: `python difficult_ai.py`
2. Run the workflow demo: `python example_agent_workflow.py`
3. Read the scenario contract: `docs/scenario_contract.md`
4. Create your first custom scenario using ArchitectAgent
5. Evaluate a full conversation using all 4 agents

## Support

- Full docs: `README.md`
- Quick start: `QUICKSTART.md`
- Restructuring info: `RESTRUCTURING.md`
- Scenario schema: `docs/scenario_contract.md`

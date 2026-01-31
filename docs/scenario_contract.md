# Scenario Contract

This document defines the scenario contract that all agents in DifficultAI use to reason over the same conversation structure.

## Purpose

The scenario contract provides a standardized way to define high-pressure conversation scenarios. This contract is shared across the entire agent workflow:

- **Architect** → designs scenarios using this contract
- **Researcher** → enriches scenarios with context
- **Adversary** → executes scenarios in real-time
- **Evaluator** → scores performance against scenario goals

## Schema

```typescript
Scenario {
  persona_type: "ANGRY_CUSTOMER" | "ELITE_INTERVIEWER" | "TOUGH_NEGOTIATOR" | "SKEPTICAL_INVESTOR" | "DEMANDING_CLIENT"
  company: string
  role: string
  stakes: string
  user_goal: string
  difficulty: 1–5
  source_docs?: [pdf | text]
}
```

## Field Definitions

### persona_type
**Type:** Enum (string)  
**Required:** Yes

The type of persona the AI will simulate. Supported values:

- `ANGRY_CUSTOMER` - Frustrated customer demanding immediate resolution
- `ELITE_INTERVIEWER` - Senior interviewer testing technical and cultural fit
- `TOUGH_NEGOTIATOR` - Experienced negotiator seeking best deal
- `SKEPTICAL_INVESTOR` - Investor questioning business fundamentals
- `DEMANDING_CLIENT` - High-value client with strict requirements

Each persona type has specific behaviors and success criteria defined in the architect agent.

### company
**Type:** String  
**Required:** Yes

The name of the company in context. This could be:
- The company the user is interviewing with
- The company the user represents
- The customer's company

Examples: `"TechCorp"`, `"Acme Industries"`, `"Global Solutions Inc."`

### role
**Type:** String  
**Required:** Yes

The role or position relevant to the scenario. This defines:
- What position the user is interviewing for
- What role the user is playing in the conversation
- Expected competencies and responsibilities

Examples: `"Senior Software Engineer"`, `"Account Manager"`, `"Product Manager"`

### stakes
**Type:** String  
**Required:** Yes

What's at stake in this conversation. This defines the importance and consequences.

Examples:
- `"Final round interview for dream job with $200k compensation"`
- `"Saving $1M customer account that's threatening to leave"`
- `"Securing $5M Series A funding"`

### user_goal
**Type:** String  
**Required:** Yes

What the user is trying to achieve in this conversation. This defines success criteria.

Examples:
- `"Demonstrate technical expertise and get job offer"`
- `"Retain customer and create recovery plan"`
- `"Secure funding commitment"`

### difficulty
**Type:** Integer (1-5)  
**Required:** Yes

The difficulty level of the scenario:

- **1** - Warm-up: Firm but professional, good for practice
- **2** - Standard: Direct challenges, typical interview pressure
- **3** - Challenging: Aggressive questioning, high-stakes scenarios
- **4** - Expert: Confrontational, exposing weaknesses
- **5** - Elite: Maximum pressure, zero tolerance for vagueness

### source_docs
**Type:** Array of strings (file paths or text)  
**Required:** No

Optional source documents to provide additional context. These could include:
- Company information PDFs
- Job descriptions
- Product documentation
- Background research

The researcher agent uses these to enrich the scenario context.

## Example Scenarios

### Example 1: Technical Interview

```json
{
  "persona_type": "ELITE_INTERVIEWER",
  "company": "Google",
  "role": "Senior Software Engineer - Infrastructure",
  "stakes": "Final round interview for L5 position with $250k total comp",
  "user_goal": "Demonstrate deep systems knowledge and get offer",
  "difficulty": 4,
  "source_docs": ["google_infrastructure_overview.pdf"]
}
```

### Example 2: Customer Escalation

```json
{
  "persona_type": "ANGRY_CUSTOMER",
  "company": "Enterprise Solutions Corp",
  "role": "Customer Success Manager",
  "stakes": "Saving $2M annual contract that's threatening to cancel",
  "user_goal": "Calm customer, identify root cause, commit to resolution timeline",
  "difficulty": 3,
  "source_docs": []
}
```

### Example 3: Investor Pitch

```json
{
  "persona_type": "SKEPTICAL_INVESTOR",
  "company": "StartupXYZ",
  "role": "CEO / Founder",
  "stakes": "Securing $3M seed funding to extend runway",
  "user_goal": "Convince investor of market opportunity and team capability",
  "difficulty": 4,
  "source_docs": ["pitch_deck.pdf", "market_research.txt"]
}
```

### Example 4: Salary Negotiation

```json
{
  "persona_type": "TOUGH_NEGOTIATOR",
  "company": "TechCorp",
  "role": "Software Engineer",
  "stakes": "Negotiating compensation for accepted offer - gap of $40k from expectations",
  "user_goal": "Secure additional $30k base salary or equivalent equity",
  "difficulty": 3,
  "source_docs": []
}
```

## Usage in Code

### Creating a Scenario (Architect)

```python
from agents import ArchitectAgent
from agents.architect import PersonaType

architect = ArchitectAgent()

scenario = architect.design_scenario(
    persona_type=PersonaType.ELITE_INTERVIEWER,
    company="TechCorp",
    role="Senior Software Engineer",
    stakes="Final round interview for dream job",
    user_goal="Demonstrate technical expertise",
    difficulty=3,
    source_docs=["job_description.pdf"]
)

# Convert to dictionary for sharing with other agents
scenario_dict = scenario.to_dict()
```

### Using in Adversary

```python
from agents import AdversaryAgent

adversary = AdversaryAgent(
    api_key="sk-...",
    scenario=scenario_dict
)

# The adversary adapts its behavior based on scenario
response = adversary.chat("I have 5 years of experience...")
```

### Using in Evaluator

```python
from agents import EvaluatorAgent

evaluator = EvaluatorAgent()

evaluation = evaluator.evaluate_conversation(
    metrics=adversary.get_performance_metrics(),
    scenario=scenario_dict
)

# Evaluator judges performance against scenario goals
print(evaluator.get_summary_report(evaluation))
```

## Validation

The architect agent provides validation for scenarios:

```python
issues = architect.validate_scenario(scenario)

if issues:
    print("Scenario validation failed:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("Scenario is valid")
```

## Design Principles

1. **Shared Understanding** - All agents work with the same scenario object
2. **Explicit Goals** - Clear success criteria for evaluation
3. **Context-Aware** - Enough information for realistic simulation
4. **Difficulty Calibrated** - Consistent difficulty scaling across scenarios
5. **Extensible** - Easy to add new persona types and fields

## Future Enhancements

Potential additions to the contract:

- `duration`: Expected conversation length
- `key_questions`: Pre-defined critical questions
- `success_metrics`: Quantitative success thresholds
- `industry_context`: Industry-specific knowledge requirements
- `personality_traits`: Fine-grained persona customization

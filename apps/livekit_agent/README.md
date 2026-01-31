# LiveKit Agent

This directory contains the LiveKit agent runtime - a first-class agent runtime for real-time voice interactions, not a background worker.

## Purpose

The LiveKit agent orchestrates the full DifficultAI workflow:

1. **Architect** designs the scenario
2. **Researcher** gathers context
3. **Adversary** runs the live conversation
4. **Evaluator** scores and provides feedback

## Usage

```python
from apps.livekit_agent import LiveKitAgentRuntime
from agents.architect import PersonaType

runtime = LiveKitAgentRuntime()

# Set up scenario
scenario = runtime.setup_scenario(
    persona_type=PersonaType.ELITE_INTERVIEWER,
    company="TechCorp",
    role="Senior Software Engineer",
    stakes="Technical interview for dream job",
    user_goal="Demonstrate expertise",
    difficulty=3
)

# Start conversation (with LiveKit integration)
adversary = runtime.start_conversation(scenario.to_dict())

# ... conversation happens ...

# Evaluate performance
evaluation = runtime.complete_conversation()
```

## Integration

This runtime is designed to integrate with LiveKit for real-time voice interactions. In production, it would:

- Connect to LiveKit rooms
- Handle voice input/output
- Stream conversation state
- Provide real-time feedback

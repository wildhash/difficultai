# Difficult AI

DifficultAI is not a chatbot. It is an agentic LiveKit system that designs, runs, and evaluates high-pressure conversations in real time.

Voice-first adversarial AI that pressure-tests users in high-stakes conversations using real-time interruption, escalation, and measurable performance scoring.

## Overview

Difficult AI is a deliberately challenging conversational agent designed to simulate high-pressure interactions. Unlike typical helpful AI assistants, Difficult AI:

- **Interrupts vague answers** - Demands specificity and concrete details
- **Escalates when deflected** - Increases pressure when users avoid questions
- **Challenges assumptions** - Questions unfounded claims and weak reasoning
- **Pushes for concrete commitments** - Requires specific numbers, dates, and actions
- **Increases difficulty gradually** - Adapts pressure based on user performance
- **Stops on interruption** - Immediately adapts when the user interrupts

## Architecture

DifficultAI is built as an **agent platform**, not just a single chatbot. The system consists of four specialized agents that work together:

### Agent Workforce

```
agents/
├── architect.py      # Designs interview scenarios and conversation structures
├── researcher.py     # Gathers company and role context
├── adversary.py      # Live conversational agent (the "Difficult AI")
└── evaluator.py      # Scores performance and provides feedback
```

This agentic architecture allows the system to:
1. **Design** customized scenarios based on role, company, and difficulty
2. **Research** context to make conversations realistic
3. **Execute** high-pressure conversations in real-time
4. **Evaluate** performance with structured feedback

### LiveKit Integration

The `apps/livekit_agent/` runtime orchestrates the agent workflow for real-time voice interactions:

```python
from apps.livekit_agent import LiveKitAgentRuntime
from agents.architect import PersonaType

runtime = LiveKitAgentRuntime()

# Set up scenario
scenario = runtime.setup_scenario(
    persona_type=PersonaType.ELITE_INTERVIEWER,
    company="TechCorp",
    role="Senior Software Engineer",
    stakes="Final round interview",
    user_goal="Get job offer",
    difficulty=3
)

# Run conversation → get evaluation
```

See [docs/scenario_contract.md](docs/scenario_contract.md) for the full scenario specification.

## Repository Structure

```
difficultai/
├── agents/                    # Agent workforce
│   ├── architect.py          # Designs interview scenarios
│   ├── researcher.py         # Gathers company + role context
│   ├── adversary.py          # Live conversational agent
│   └── evaluator.py          # Scoring + feedback
├── apps/                     
│   └── livekit_agent/        # LiveKit agent runtime (not a background worker)
├── docs/
│   └── scenario_contract.md  # Scenario schema specification
├── difficult_ai.py           # Core adversarial agent implementation
├── examples.py               # Simple usage examples
├── example_agent_workflow.py # Complete agent workflow demo
└── tests/                    # Test suites
```

This structure makes the agent roles explicit and allows scaling from a single agent to an agentic workforce without refactors.

## Purpose

This agent is designed for:
- **Sales training** - Practice handling difficult prospects
- **Interview preparation** - Prepare for challenging questions
- **Presentation practice** - Test your ability to defend ideas under pressure
- **Negotiation training** - Develop skills in high-stakes conversations
- **Leadership development** - Build confidence in confrontational situations

## Installation

1. Clone the repository:
```bash
git clone https://github.com/wildhash/difficultai.git
cd difficultai
```

2. Install dependencies (one command):
```bash
make install
```

Or manually:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials (see below)
```

## Quick Start (One Command)

```bash
make dev
```

This starts the LiveKit agent in development mode. Make sure you have:
- Configured `.env` with LiveKit and OpenAI credentials
- Installed dependencies with `make install`

## Usage

### Voice-to-Voice LiveKit Agent (Production Ready)

**One-command start:**

```bash
make dev
```

Or alternatively:
```bash
# Using Python module
python -m apps.livekit_agent dev

# Or directly
python apps/livekit_agent/agent.py dev
```

#### Quick Start with LiveKit Cloud (Recommended for Testing)

1. **Get LiveKit Cloud credentials** (Free tier available):
   - Sign up at [https://cloud.livekit.io](https://cloud.livekit.io)
   - Create a new project
   - Get your credentials from Project Settings:
     - `LIVEKIT_URL` (format: `wss://your-project.livekit.cloud`)
     - `LIVEKIT_API_KEY` (starts with `API`)
     - `LIVEKIT_API_SECRET`

2. **Get OpenAI API key**:
   - Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Create a new API key
   - Ensure you have access to the Realtime API (or the agent will automatically fallback to STT->LLM->TTS)

3. **Configure `.env`**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```bash
   OPENAI_API_KEY=sk-...
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=APIxxxxx
   LIVEKIT_API_SECRET=xxxxx
   DEFAULT_VOICE=marin
   ```

4. **Run the agent**:
   ```bash
   make dev
   ```

5. **Test using LiveKit Agents Playground**:
   - Go to [LiveKit Cloud Agents Playground](https://cloud.livekit.io/agents)
   - Open the web client: `apps/web/index.html` in your browser
   - Fill in scenario details and click "Copy Scenario JSON"
   - Paste the JSON in the Playground's room metadata field
   - Click "Start Session" in the Playground
   - Start speaking - the agent will respond with voice
   - The agent will:
     - Ask 3-6 questions based on the scenario and difficulty
     - Support barge-in (interrupt anytime)
     - Generate a scorecard at the end with 6 scores (1-10) and 3 coaching points

#### Testing with Custom Web Client

1. Open `apps/web/index.html` in your browser
2. Fill in the scenario configuration
3. Click "Copy Scenario JSON"
4. Use the JSON with LiveKit Agents Playground or your own backend

See [apps/web/README.md](apps/web/README.md) for detailed web client instructions.

#### Smoke Test (Verify Setup)

```bash
make smoke-test
```

The smoke test verifies:
- ✓ Environment variables are set
- ✓ Dependencies are installed
- ✓ Scenario validation works
- ✓ LiveKit server is accessible
- ✓ Agent components are functional

#### Architecture: Voice-to-Voice with Realtime API + Fallback

DifficultAI prioritizes **OpenAI's Realtime API** for native voice-to-voice conversation:

**Primary Mode (Realtime API):**
- ✓ Native voice-to-voice (no STT→LLM→TTS pipeline)
- ✓ Lower latency (no transcription overhead)
- ✓ Natural prosody and timing
- ✓ Built-in barge-in support (interruption handling)

**Automatic Fallback (if Realtime unavailable):**
- ✓ STT: Deepgram or OpenAI Whisper
- ✓ LLM: OpenAI GPT-4
- ✓ TTS: OpenAI TTS
- ✓ Same barge-in support maintained

**Key Features:**
- **Barge-in Support**: Interrupt the agent anytime while it's speaking
- **Question Plan**: Agent generates 3-6 questions based on scenario and difficulty
- **Scorecard**: End-of-session evaluation with 6 scores (1-10) + 3 coaching points

**Scorecard Format:**
```
SCORES (1-10 scale):
  Clarity:        8.5/10
  Confidence:     7.2/10
  Commitment:     6.8/10
  Adaptability:   7.5/10
  Composure:      8.1/10
  Effectiveness:  7.6/10

COACHING POINTS:
  1. Focus on specificity: Replace vague language with concrete numbers...
  2. Address questions directly: Avoid deflecting or changing topics...
  3. Make concrete commitments: Include specific timelines...
```

#### Scenario Configuration

**Canonical ScenarioConfig:**
```json
{
  "persona": "ELITE_INTERVIEWER",
  "difficulty": 0.8,
  "company": "TechCorp",
  "role": "Senior SWE",
  "goals": "Get job offer"
}
```

**Difficulty Scale:** 0-1 (float)
- 0.0 = Easy, professional questioning
- 0.5 = Moderate, challenging questions
- 1.0 = Maximum pressure, confrontational

See [docs/scenario_contract.md](docs/scenario_contract.md) for full specification.

See [apps/livekit_agent/README.md](apps/livekit_agent/README.md) for deployment and advanced configuration.

### Interactive Mode (Development)

Run the agent in interactive text mode for testing:

```bash
python difficult_ai.py
```

This starts a conversation where the AI will challenge your responses. Type your answers and see how the AI responds based on your clarity and specificity.

Commands:
- Type your response normally to continue the conversation
- Type `stats` to see your current performance metrics
- Type `quit` to exit and see final statistics

### Agent Workflow Demo

See the complete agent workflow in action:

```bash
python example_agent_workflow.py
```

This demonstrates:
- Architect designing scenarios
- Researcher gathering context
- Adversary running conversations
- Evaluator providing feedback

### Programmatic Usage

```python
from difficult_ai import DifficultAI

# Initialize the agent
agent = DifficultAI()

# Have a conversation
response = agent.chat("I'm working on improving our sales process")
print(response)

# Check your performance
stats = agent.get_stats()
print(f"Difficulty Level: {stats['difficulty_level']}/5")
print(f"Commitments Made: {stats['commitments_made']}")
```

### Example Scenarios

Run example scenarios to see how the AI behaves:

```bash
python examples.py
```

This demonstrates various conversation patterns and the AI's responses.

## How It Works

### Difficulty Levels

The agent operates on a 5-level difficulty scale:

1. **Level 1** - Firm but professional questioning
2. **Level 2** - Direct challenges to vague statements
3. **Level 3** - Aggressive interruption of deflections
4. **Level 4** - Confrontational, exposing contradictions
5. **Level 5** - Maximum pressure, zero tolerance for vagueness

### Response Analysis

The agent analyzes each user response for:

- **Vagueness** - Detects words like "maybe," "probably," "kind of"
- **Deflection** - Identifies attempts to change the subject
- **Concreteness** - Looks for specific numbers, dates, and commitments
- **Interruptions** - Recognizes when the user needs to interject

### Escalation Logic

Difficulty increases when:
- User gives 2+ vague responses
- User deflects 2+ times
- User fails to provide concrete details

Difficulty decreases when:
- User makes multiple concrete commitments
- User provides specific, clear answers consistently

### Commitment Tracking

The agent tracks commitments containing phrases like:
- "I will..."
- "I'll..."
- "I commit to..."
- "I promise..."
- "I guarantee..."
- "By [date/time]..."

## Performance Metrics

The agent tracks:
- **Difficulty Level** - Current pressure level (1-5)
- **Vague Responses** - Count of unclear answers
- **Deflections** - Count of topic changes/avoidances
- **Commitments Made** - Specific promises extracted from responses
- **Total Exchanges** - Number of back-and-forth exchanges

## Testing

Run the test suite:

```bash
python -m pytest test_difficult_ai.py -v
```

Or using unittest:

```bash
python -m unittest test_difficult_ai.py -v
```

## API Reference

### DifficultAI Class

#### Methods

- `__init__(api_key=None, model="gpt-4")` - Initialize the agent
- `chat(user_message: str) -> str` - Process a message and get a response
- `get_stats() -> Dict` - Get current performance statistics
- `reset()` - Reset conversation state

#### Properties

- `difficulty_level` - Current difficulty (1-5)
- `vague_response_count` - Number of vague responses detected
- `deflection_count` - Number of deflections detected
- `commitments_made` - List of commitments tracked
- `conversation_history` - Full conversation log

## Configuration

The agent can be customized by modifying:
- **Model** - Change the OpenAI model (default: gpt-4)
- **Temperature** - Adjust response variability (default: 0.8)
- **Max Tokens** - Control response length (default: 150)

## Examples

### Example 1: Vague Response

```
You: Maybe I'll work on it next week
AI: "Maybe"? That's not a plan. Give me a specific day and time.
```

### Example 2: Concrete Commitment

```
You: I will deliver 5 units by Friday at 2pm
AI: Good. That's specific. I'm holding you to that. What's your backup plan?
```

### Example 3: Deflection

```
You: Let's talk about the budget first
AI: No. You're deflecting. Answer my question: What's your progress?
```

## License

This project is open source and available for educational and training purposes.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Disclaimer

This AI is designed to be challenging and confrontational for training purposes. It is not suitable for general conversation or customer-facing applications. Use responsibly and in appropriate training contexts only.

# DifficultAI LiveKit Agent

This directory contains the production LiveKit agent implementation for DifficultAI - a voice-to-voice conversational agent that conducts high-pressure training conversations using OpenAI's Realtime API.

## Overview

The LiveKit agent provides:
- **Voice-to-voice interaction** using OpenAI Realtime API
- **Per-session configuration** via LiveKit job metadata
- **Dynamic persona adaptation** based on scenario type
- **In-memory transcript tracking** for performance analysis
- **End-of-call scorecard** using EvaluatorAgent

## Architecture

The agent orchestrates the full DifficultAI workflow:
1. **Scenario Setup** - Loads configuration from metadata or collects it conversationally
2. **Architect** - Designs the conversation structure
3. **Adversary** - Conducts the high-pressure conversation
4. **Evaluator** - Generates performance scorecard

## Files

- `agent.py` - Main LiveKit agent implementation
- `scenario_validator.py` - Scenario validation utilities
- `__init__.py` - Legacy runtime wrapper (deprecated, use agent.py)

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Optional
DEEPGRAM_API_KEY=your_deepgram_key  # For STT fallback
DEFAULT_VOICE=marin  # Options: alloy, echo, fable, onyx, nova, shimmer, marin
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running Locally

### Development Mode

Run the agent locally for testing:

```bash
python apps/livekit_agent/agent.py dev
```

This starts the agent in development mode, connecting to your LiveKit server.

### Testing with LiveKit CLI

```bash
# Start the agent
python apps/livekit_agent/agent.py dev

# In another terminal, connect a client
# Use LiveKit web client or SDK to connect to the room
```

## Deployment

### LiveKit Cloud

1. **Create a LiveKit Cloud account** at https://cloud.livekit.io

2. **Set up your agent**:
   ```bash
   # Build and deploy using LiveKit Cloud CLI
   livekit-cli deploy create \
     --name difficultai-agent \
     --runtime python \
     --entrypoint apps/livekit_agent/agent.py
   ```

3. **Configure environment variables** in the LiveKit Cloud dashboard

### Self-Hosted LiveKit Server

1. **Deploy LiveKit server** following https://docs.livekit.io/deploy/

2. **Run the agent** as a service:
   ```bash
   # Using systemd or docker-compose
   python apps/livekit_agent/agent.py start
   ```

## Scenario Configuration

### Via Metadata (Recommended)

When creating a room, pass scenario configuration as JSON metadata:

```python
import livekit
from livekit import api

# Create room with metadata
room_service = api.RoomServiceClient()
room = room_service.create_room(
    api.CreateRoomRequest(
        name="training-session-123",
        metadata=json.dumps({
            "persona_type": "ELITE_INTERVIEWER",
            "company": "TechCorp",
            "role": "Senior Software Engineer",
            "stakes": "Final round interview for $250k position",
            "user_goal": "Demonstrate technical expertise and secure job offer",
            "difficulty": 4,
            "voice": "marin"
        })
    )
)
```

### Conversational Collection

If metadata is not provided, the agent will ask the user for:
1. **persona_type** - Type of scenario (ANGRY_CUSTOMER, ELITE_INTERVIEWER, etc.)
2. **company** - Company name
3. **role** - User's role in the scenario
4. **stakes** - What's at stake
5. **user_goal** - What the user wants to achieve
6. **difficulty** - Difficulty level 1-5
7. **voice** (optional) - Voice preference

## Scenario Types

The agent supports these persona types:

- **ANGRY_CUSTOMER** - Frustrated customer demanding immediate resolution
- **ELITE_INTERVIEWER** - Senior interviewer testing technical and cultural fit
- **TOUGH_NEGOTIATOR** - Experienced negotiator seeking best deal
- **SKEPTICAL_INVESTOR** - Investor questioning business fundamentals
- **DEMANDING_CLIENT** - High-value client with strict requirements

See `docs/scenario_contract.md` for full schema documentation.

## Scorecard

At the end of each conversation, the agent generates a detailed scorecard with:

- **Performance Scores** (0-100 for each dimension):
  - Clarity - How clear and specific were responses
  - Confidence - Confidence level demonstrated
  - Commitment - Quality of commitments made
  - Adaptability - Ability to adapt under pressure
  - Overall - Combined performance score

- **Feedback**:
  - Strengths identified
  - Weaknesses to improve
  - Specific recommendations
  - Key moments to review

Scorecards are saved to `scorecard_{room_name}.json` and logged.

## Development

### Testing

Run unit tests:
```bash
python -m unittest test_livekit_agent -v
```

### Debugging

Enable debug logging:
```bash
export LIVEKIT_LOG_LEVEL=debug
python apps/livekit_agent/agent.py dev
```

## Troubleshooting

### Connection Issues

- Verify `LIVEKIT_URL` is correct (should start with `wss://` or `ws://`)
- Check API credentials are valid
- Ensure firewall allows WebSocket connections

### Audio Issues

- Verify `OPENAI_API_KEY` is valid and has Realtime API access
- Check voice name is valid (alloy, echo, fable, onyx, nova, shimmer, marin)
- Test with different audio devices

### Scenario Validation Errors

- Ensure all required fields are provided in metadata
- Check persona_type is one of the supported values
- Verify difficulty is between 1-5

## API Reference

### DifficultAIAgent

Main agent class handling the LiveKit session.

```python
class DifficultAIAgent:
    """DifficultAI voice agent using LiveKit and OpenAI Realtime API."""
    
    async def entrypoint(self):
        """Main agent entrypoint."""
```

### scenario_validator

Utilities for validating scenario configuration.

```python
def validate_scenario(scenario: Dict[str, Any]) -> List[str]:
    """Validate scenario against contract, returns list of errors."""

def is_scenario_complete(scenario: Dict[str, Any]) -> bool:
    """Check if scenario has all required fields."""

def get_missing_fields(scenario: Dict[str, Any]) -> List[str]:
    """Get list of missing required fields."""
```

## Resources

- [LiveKit Documentation](https://docs.livekit.io)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [DifficultAI Scenario Contract](../../docs/scenario_contract.md)

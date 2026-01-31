# Difficult AI - Quick Start Guide

## What is Difficult AI?

Difficult AI is a deliberately challenging conversational agent that simulates high-pressure interactions. It's designed to help you practice:
- Defending your ideas under scrutiny
- Providing clear, concrete answers
- Staying on topic under pressure
- Making and honoring commitments

## Quick Start Options

### Option 1: Voice-to-Voice Agent (Production)

For real-time voice training with LiveKit:

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Set Up Environment
```bash
cp .env.example .env
# Edit .env with your credentials:
# - OPENAI_API_KEY (required)
# - LIVEKIT_URL (required, e.g., wss://your-project.livekit.cloud)
# - LIVEKIT_API_KEY (required)
# - LIVEKIT_API_SECRET (required)
# - DEFAULT_VOICE (optional, default: marin)
```

#### 3. Run the Voice Agent
```bash
python apps/livekit_agent/agent.py dev
```

The agent will:
- Connect to your LiveKit server
- Wait for voice connections
- Conduct high-pressure training conversations
- Generate performance scorecards

**Get LiveKit Credentials:**
- Sign up at https://cloud.livekit.io (free tier available)
- Create a project and get your URL, API key, and secret

**Connect a Client:**
- Use LiveKit web SDK or mobile app
- Join a room with optional scenario metadata
- Have your voice conversation
- Receive detailed scorecard at the end

See [apps/livekit_agent/README.md](apps/livekit_agent/README.md) for full documentation.

### Option 2: Interactive Text Mode (Development)

For quick text-based testing:

#### 1. Install Dependencies
```bash
pip install openai python-dotenv
```

#### 2. Set Up API Key
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

#### 3. Run Interactive Mode
```bash
python difficult_ai.py
```

## How the AI Works

### The AI Will:
- ✓ Challenge vague answers ("maybe", "probably", "I think")
- ✓ Call out deflections ("let's talk about X instead")
- ✓ Demand concrete details (numbers, dates, specific actions)
- ✓ Increase pressure when you're unclear
- ✓ Track your commitments
- ✓ Stop immediately if you interrupt

### Difficulty Levels (1-5):
1. **Firm**: Professional questioning
2. **Direct**: Challenges vague statements
3. **Aggressive**: Interrupts deflections
4. **Confrontational**: Exposes contradictions
5. **Maximum**: Zero tolerance for vagueness

## Tips for Success

### DO:
- Be specific with numbers and dates
- Use action verbs ("I will", "I commit to")
- Answer the question asked
- Admit when you don't know
- Make realistic commitments

### DON'T:
- Use vague language ("maybe", "probably")
- Deflect to different topics
- Make commitments you can't keep
- Get defensive
- Give up easily

## Example Conversation

```
AI: What's your biggest challenge and what are you doing about it?
You: Well, I'm having trouble with time management
AI: That's vague. What SPECIFICALLY is the problem? Give me an example.
You: I miss deadlines by 2-3 days on average
AI: Better. Now, what EXACTLY will you do to fix this? Be specific.
You: I will use a calendar and set reminders
AI: When will you START? What's the first reminder you'll set?
You: I'll set up my calendar today at 3pm with reminders for all tasks
AI: Good. That's a commitment. I'm holding you to 3pm today.
```

## Commands

While running `python difficult_ai.py`:
- Type normally to respond
- Type `stats` to see performance metrics
- Type `quit` to exit and see final results

## Understanding Your Stats

After a conversation, you'll see:
- **Difficulty Level**: How much pressure the AI applied (1-5)
- **Vague Responses**: How many times you were unclear
- **Deflections**: How many times you changed topics
- **Commitments**: What specific promises you made

## Practice Scenarios

Run example scenarios to see the AI in action:
```bash
python examples.py
```

This shows:
- How the AI responds to vague answers
- What happens when you deflect
- How it reacts to concrete commitments
- Interruption handling
- Difficulty progression over time

## Advanced Usage

### Programmatic API
```python
from difficult_ai import DifficultAI

agent = DifficultAI()
response = agent.chat("I think I might start working on it")
print(response)

# Check stats
stats = agent.get_stats()
print(f"Difficulty: {stats['difficulty_level']}/5")
```

### Custom Configuration
```python
agent = DifficultAI(
    api_key="your-key",
    model="gpt-4"  # or "gpt-3.5-turbo" for faster/cheaper
)
```

## Troubleshooting

### "No module named 'openai'"
```bash
pip install -r requirements.txt
```

### "Invalid API key"
- Check your `.env` file has `OPENAI_API_KEY=sk-...`
- Verify the key is valid at platform.openai.com

### Tests failing
```bash
python -m unittest test_difficult_ai.py -v
```

## Best Practices

1. **Warm up**: Start with the examples to see patterns
2. **Be honest**: The AI detects deflection - don't try to game it
3. **Practice regularly**: Like any skill, pressure handling improves with practice
4. **Review stats**: Use them to identify your weak points
5. **Embrace discomfort**: The AI is SUPPOSED to be challenging

## When to Use Difficult AI

### Good For:
- Sales pitch practice
- Interview preparation
- Presentation rehearsal
- Negotiation training
- Leadership development
- Building mental toughness

### Not For:
- Casual conversation
- Customer support practice
- Emotional support
- Brainstorming sessions
- Team collaboration

## Next Steps

1. Try the interactive mode: `python difficult_ai.py`
2. See examples: `python examples.py`
3. Review the code: `difficult_ai.py`
4. Read full docs: `README.md`
5. Run tests: `python -m unittest test_difficult_ai.py`

---

Remember: **The AI is deliberately difficult**. That's the point. If you feel pressured, you're using it correctly!

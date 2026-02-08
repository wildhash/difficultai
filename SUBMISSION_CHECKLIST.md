# DifficultAI Hackathon Submission Checklist

## Project Overview

**DifficultAI** is a voice-first adversarial training agent built on LiveKit with production-grade observability via Opik.

- **Repository**: https://github.com/wildhash/difficultai
- **Demo**: Included web application for voice interaction
- **Tech Stack**: LiveKit Agents, OpenAI Realtime API, React, Opik

## Submission Components

### ✅ 1. Production-Ready Voice Agent

- [x] LiveKit Agents runtime with OpenAI Realtime API
- [x] Automatic fallback to STT→LLM→TTS if Realtime unavailable
- [x] Barge-in support (user can interrupt agent)
- [x] Scenario-based conversations (5 persona types)
- [x] Dynamic difficulty scaling (0-1 scale)
- [x] Question planning (3-6 questions based on difficulty)
- [x] End-of-session scorecard (6 metrics + 3 coaching points)

### ✅ 2. Opik Observability Integration

- [x] **Session-level traces** with metadata:
  - LiveKit room name
  - Session ID
  - Participant identity
  - Scenario configuration (persona, company, role, difficulty)
  - Complete conversation transcript
  - Final evaluation scorecard

- [x] **Span-level traces**:
  - STT (Speech-to-Text) operations
  - LLM (Language Model) calls with prompts/responses
  - TTS (Text-to-Speech) operations
  - Tool calls (if any)
  - Errors with context

- [x] **OpenAI SDK integration**:
  - Automatic prompt/response tracking via `track_openai`
  - Token usage tracking
  - Model and temperature metadata

- [x] **Configuration & Control**:
  - Environment variables: `OPIK_API_KEY`, `OPIK_URL_OVERRIDE`, `OPIK_PROJECT`, `OPIK_WORKSPACE`
  - Kill switch: `OPIK_DISABLED=1`
  - Cloud and self-hosted support

- [x] **Evaluation & experiments**:
  - Scorecard dimensions logged as Opik feedback scores on each session trace
  - Regression eval suite using Opik datasets + experiments: `make opik-eval-suite`

### ✅ 3. Web Demo Application

- [x] React + Vite web application
- [x] LiveKit Client SDK integration
- [x] **Features**:
  - Room joining with LiveKit credentials
  - Microphone audio publishing
  - Agent audio playback
  - Live transcripts display (placeholder - requires agent data channel implementation)
  - Start/Stop call controls
  - Scenario configuration UI
  - Copy scenario JSON for LiveKit Playground

- [x] **Documentation**:
  - Complete README with setup instructions
  - Token generation examples (Python, Node.js, CLI)
  - Production deployment guide
  - Troubleshooting section

### ✅ 4. Documentation & Scripts

- [x] **Main README updates**:
  - Opik setup instructions
  - Web demo quick start
  - View traces in Opik section
  - Repository structure with new modules

- [x] **Environment configuration**:
  - `.env.example` updated with Opik variables
  - Clear documentation for each variable
  - Cloud vs. self-hosted instructions

- [x] **Make targets**:
  - `make dev` - Start agent
  - `make smoke-test` - Validate agent setup
  - `make opik-smoke-test` - Validate Opik tracing
  - `make opik-eval-suite` - Run Opik scorecard evals (dataset + experiment)
  - `make install` - Install dependencies
  - `make clean` - Clean up temporary files

- [x] **Smoke tests**:
  - Agent smoke test (existing)
  - Opik smoke test (new) - validates tracing without running full agent

## Demo Flow

### Quick Demo (5 minutes)

1. **Setup**:
   ```bash
   git clone https://github.com/wildhash/difficultai.git
   cd difficultai
   cp .env.example .env
   # Edit .env with credentials
   make install
   ```

2. **Validate Opik**:
   ```bash
   make opik-smoke-test
   ```
   Expected output: ✅ All tracing components validated

3. **Start Agent**:
   ```bash
   make dev
   ```
   Expected output: Agent running, listening for connections

4. **Start Web Demo**:
   ```bash
   cd apps/web/demo
   npm install
   npm run dev
   ```
   Open `http://localhost:3000`

5. **Run Session**:
   - Configure scenario in web UI
   - Copy scenario JSON
   - Use LiveKit Agents Playground or generate token
   - Connect and speak
   - Observe Opik traces in real-time

6. **View Traces**:
   - Go to https://www.comet.com/opik
   - Navigate to "difficultai" project
   - See session trace with all metadata and spans

### Production Demo (10 minutes)

1. Deploy agent to LiveKit Cloud Agent Builder
2. Set environment variables in Cloud dashboard
3. Deploy web app to Vercel/Netlify
4. Create backend for token generation
5. Run full training session
6. Review Opik traces with scorecard data

## Technical Highlights

### 1. Opik Integration Architecture

```
┌────────────────────────┐
│  DifficultAI Agent     │
│  (Python/LiveKit)      │
└───────────┬────────────┘
            │
            │ Opik SDK
            │ (session/span traces)
            ▼
┌────────────────────────┐
│  Opik Platform         │
│  (Cloud or Self-Hosted)│
└────────────────────────┘
            │
            │ Web Dashboard
            ▼
┌────────────────────────┐
│  Developer View        │
│  - Session metadata    │
│  - LLM prompts/responses│
│  - Performance metrics │
│  - Error tracking      │
└────────────────────────┘
```

### 2. Trace Metadata Example

```json
{
  "trace_name": "DifficultAI Session: training-room-001",
  "metadata": {
    "livekit_room": "training-room-001",
    "session_id": "sess_abc123",
    "participant_identity": "user@example.com",
    "persona": "ELITE_INTERVIEWER",
    "role": "Senior Software Engineer",
    "difficulty": 0.7,
    "company": "TechCorp",
    "scenario_type": "voice_conversation"
  },
  "spans": [
    {
      "name": "llm_call",
      "type": "llm",
      "metadata": {
        "model": "gpt-4-realtime",
        "duration_seconds": 1.23
      }
    },
    {
      "name": "stt_call",
      "type": "tool",
      "metadata": {
        "provider": "deepgram",
        "duration_seconds": 0.45
      }
    }
  ],
  "output": {
    "scorecard": {
      "scores": {
        "clarity": 8.5,
        "confidence": 7.2,
        "overall": 78
      }
    },
    "transcript_length": 42
  }
}
```

### 3. Web Demo Features

- **Zero-backend testing**: Use LiveKit Agents Playground with JSON export
- **Production-ready**: Backend integration examples provided
- **Responsive UI**: Works on desktop and mobile
- **Real-time audio**: WebRTC with LiveKit Client SDK
- **Barge-in**: Interrupt agent anytime during speech

## What Was Instrumented

### Session Lifecycle
- **Trace start**: When participant joins room
- **Trace end**: When session completes, includes scorecard
- **Error logging**: Any exceptions during session

### Component Operations
1. **STT (Speech-to-Text)**:
   - Provider (Deepgram, OpenAI Whisper, Realtime)
   - Duration
   - Input/output metadata

2. **LLM (Language Model)**:
   - Model name (gpt-4, gpt-4-realtime)
   - Messages (prompts and responses)
   - Duration
   - Tokens (via OpenAI integration)

3. **TTS (Text-to-Speech)**:
   - Provider (OpenAI, Realtime)
   - Voice name
   - Duration
   - Input text

4. **Errors**:
   - Error type and message
   - Context (room, stage, operation)
   - Stack trace

## Environment Variables Reference

### Required (Agent)
```bash
OPENAI_API_KEY=sk-...
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxx
LIVEKIT_API_SECRET=xxxxx
```

### Optional (Opik)
```bash
OPIK_API_KEY=your_opik_api_key        # For Opik Cloud
OPIK_URL_OVERRIDE=http://localhost:5000  # For self-hosted
OPIK_PROJECT=difficultai               # Project name
OPIK_WORKSPACE=default                 # Workspace name
OPIK_DISABLED=1                        # To disable tracing
```

### Optional (Voice)
```bash
DEFAULT_VOICE=marin  # alloy, echo, fable, onyx, nova, shimmer, marin
```

## Testing Checklist

- [x] Opik traces appear in dashboard
- [x] Session metadata is complete (room, participant, scenario)
- [x] LLM spans include prompts and responses
- [x] STT/TTS spans have duration metrics
- [x] Errors are logged with context
- [x] Web demo connects to LiveKit
- [x] Voice audio works (both directions)
- [x] Scenario JSON export works
- [x] Smoke tests pass
- [x] Documentation is complete

## Future Enhancements

1. **Web Demo Transcripts**: Implement data channel for real-time transcripts
2. **Scorecard Display**: Show scorecard in web UI after session
3. **Recording Playback**: Add session recording retrieval
4. **Advanced Metrics**: Track more granular performance metrics in Opik
5. **Multi-turn Analysis**: Analyze conversation patterns across turns

## Resources

- **Main Documentation**: [README.md](README.md)
- **Web Demo Guide**: [apps/web/demo/README.md](apps/web/demo/README.md)
- **Opik Documentation**: https://www.comet.com/docs/opik
- **LiveKit Agents**: https://docs.livekit.io/agents/
- **Scenario Contract**: [docs/scenario_contract.md](docs/scenario_contract.md)

## Contact & Support

- GitHub Issues: https://github.com/wildhash/difficultai/issues
- Repository: https://github.com/wildhash/difficultai
- LiveKit Docs: https://docs.livekit.io
- Opik Docs: https://www.comet.com/docs/opik

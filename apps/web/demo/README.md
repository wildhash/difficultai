# DifficultAI Web Demo

A React-based web application for interacting with the DifficultAI voice training agent.

## Features

- 🎙️ **Voice-to-Voice Communication**: Connect to LiveKit rooms and speak with the AI agent
- 📝 **Live Transcripts**: See conversation transcripts in real-time
- 🎯 **Scenario Configuration**: Set up training scenarios with different personas and difficulties
- 🔄 **Barge-in Support**: Interrupt the agent anytime while it's speaking
- 📋 **Easy Setup**: Copy scenario JSON for use with LiveKit Agents Playground

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- DifficultAI agent running (see main README)
- LiveKit credentials

### Installation

```bash
cd apps/web/demo
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

### Build for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Usage

### Option 1: LiveKit Agents Playground (Easiest)

1. Open the web app at `http://localhost:3000`
2. Configure your scenario (persona, company, role, etc.)
3. Click "Copy Scenario JSON"
4. Go to [LiveKit Cloud Agents Playground](https://cloud.livekit.io/agents)
5. Paste the JSON as room metadata
6. Click "Start Session" and begin speaking

### Option 2: Direct Connection

1. Generate a LiveKit access token (see Token Generation below)
2. Open the web app at `http://localhost:3000`
3. Fill in:
   - LiveKit URL (e.g., `wss://your-project.livekit.cloud`)
   - Room Name
   - Access Token
4. Click "Connect & Start Session"
5. Start speaking - the agent will respond with voice

## Token Generation

To connect directly, you need a LiveKit access token. You can generate tokens using:

### Python (Recommended)

Create a simple token server:

```python
from livekit import api
import os

def generate_token(room_name, participant_name="user"):
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    )
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
    ))
    return token.to_jwt()

if __name__ == "__main__":
    room = input("Room name: ")
    print("\nAccess Token:")
    print(generate_token(room))
```

Run:
```bash
python generate_token.py
```

### JavaScript/Node.js

```javascript
import { AccessToken } from 'livekit-server-sdk';

const token = new AccessToken(
  process.env.LIVEKIT_API_KEY,
  process.env.LIVEKIT_API_SECRET,
  {
    identity: 'user',
    name: 'User Name',
  }
);

token.addGrant({
  roomJoin: true,
  room: 'my-room-name',
  canPublish: true,
  canSubscribe: true,
});

console.log(token.toJwt());
```

### LiveKit CLI

```bash
livekit-cli create-token \
  --api-key your-api-key \
  --api-secret your-api-secret \
  --join --room my-room-name \
  --identity user \
  --valid-for 24h
```

## Scenario Configuration

The web app generates scenario metadata in this format:

```json
{
  "persona_type": "ELITE_INTERVIEWER",
  "company": "TechCorp",
  "role": "Senior Software Engineer",
  "stakes": "Final round interview for $250k position",
  "user_goal": "Demonstrate technical expertise and secure job offer",
  "difficulty": 0.5
}
```

### Persona Types

- **ELITE_INTERVIEWER**: Senior interviewer testing technical and cultural fit
- **ANGRY_CUSTOMER**: Frustrated customer demanding immediate resolution
- **TOUGH_NEGOTIATOR**: Experienced negotiator seeking the best deal
- **SKEPTICAL_INVESTOR**: Investor questioning business fundamentals
- **DEMANDING_CLIENT**: High-value client with strict requirements

### Difficulty Levels (0-1 scale)

- **0.0-0.4**: Firm but professional
- **0.5-0.7**: Aggressive and challenging
- **0.8-1.0**: Confrontational and unforgiving

## Production Deployment

### Backend Requirements

For production, you need a backend service that:

1. Creates LiveKit rooms with scenario metadata
2. Generates participant tokens
3. (Optional) Stores session recordings
4. (Optional) Retrieves scorecards

Example backend (FastAPI):

```python
from fastapi import FastAPI
from livekit import api
import json
import os

app = FastAPI()

@app.post("/api/create-session")
async def create_session(scenario: dict):
    # Create room with scenario metadata
    room_service = api.RoomServiceClient(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    )
    
    room = room_service.create_room(
        api.CreateRoomRequest(
            name=f"session-{int(time.time())}",
            metadata=json.dumps(scenario)
        )
    )
    
    # Generate token
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    )
    token.with_identity("user")
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room.name,
        can_publish=True,
        can_subscribe=True,
    ))
    
    return {
        "token": token.to_jwt(),
        "room_name": room.name,
        "livekit_url": os.getenv("LIVEKIT_URL")
    }
```

### Environment Variables

Create a `.env.local` file in the demo directory:

```env
VITE_LIVEKIT_URL=wss://your-project.livekit.cloud
VITE_BACKEND_URL=http://localhost:8000
```

Access in code:
```javascript
const livekitUrl = import.meta.env.VITE_LIVEKIT_URL
```

## Browser Requirements

- Modern browser with WebRTC support (Chrome, Firefox, Safari, Edge)
- Microphone access required
- HTTPS required for production (localhost is exempt)

## Troubleshooting

### Microphone Not Working
- Check browser permissions (look for microphone icon in address bar)
- Ensure HTTPS is used (localhost is okay for development)
- Test microphone in browser settings

### Connection Failed
- Verify LIVEKIT_URL is correct (should start with `wss://`)
- Check LiveKit server is running
- Ensure API credentials are valid
- Check access token is not expired

### No Audio from Agent
- Check LiveKit agent is running
- Verify OpenAI API key is configured
- Check browser console for errors
- Ensure audio element is not muted

### Transcripts Not Showing
- Transcripts require custom data channel implementation
- Agent must send transcript data via room.localParticipant.publishData()
- This is a future enhancement

## Technology Stack

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **LiveKit Client SDK**: Real-time audio/video
- **CSS**: Styling (no external CSS frameworks)

## Architecture

```
┌─────────────────┐
│   React App     │
│  (This Demo)    │
└────────┬────────┘
         │ LiveKit Client SDK
         ▼
┌─────────────────┐
│  LiveKit Server │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DifficultAI     │
│ Agent (Python)  │
└─────────────────┘
```

## Contributing

See main repository [CONTRIBUTING.md](../../../CONTRIBUTING.md) for guidelines.

## License

Same as main DifficultAI repository.

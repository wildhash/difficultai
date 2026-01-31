# DifficultAI Web Client

A minimal reference web client for testing DifficultAI voice training sessions.

## Quick Start

### Option 1: LiveKit Agents Playground (Recommended for Testing)

1. Open the web client: `apps/web/index.html` in your browser
2. Fill in the scenario details (or use the pre-filled example)
3. Click "Copy Scenario JSON"
4. Go to [LiveKit Cloud Agents Playground](https://cloud.livekit.io/agents)
5. Paste the JSON as room metadata
6. Start the session and begin speaking

### Option 2: Self-Hosted Testing

1. Deploy the DifficultAI agent (see main README)
2. Set up a backend to create rooms and generate tokens
3. Update `LIVEKIT_URL` in `index.html`
4. Implement the `getToken()` function to call your backend
5. Open `index.html` in your browser and start a session

## Features

- **Scenario Configuration**: Set up persona, company, role, stakes, goal, and difficulty
- **JSON Export**: Copy scenario configuration as JSON for use with LiveKit
- **Pre-filled Example**: Default example scenario for quick testing
- **Responsive Design**: Works on desktop and mobile browsers

## Scenario Configuration

The web client generates scenario metadata in this format:

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

For production use, you need to:

1. **Backend Setup**: Create a backend service that:
   - Creates LiveKit rooms with scenario metadata
   - Generates participant tokens
   - Stores session recordings (optional)
   - Retrieves scorecards (optional)

2. **Update Configuration**:
   ```javascript
   const LIVEKIT_URL = 'wss://your-livekit-server.com';
   ```

3. **Implement Token Generation**:
   ```javascript
   async function getToken(scenario) {
       const response = await fetch('/api/create-session', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify(scenario)
       });
       const data = await response.json();
       return data.token;
   }
   ```

## Example Backend (Python/FastAPI)

```python
from fastapi import FastAPI
from livekit import api
import json

app = FastAPI()

@app.post("/api/create-session")
async def create_session(scenario: dict):
    # Create LiveKit room with scenario metadata
    room_service = api.RoomServiceClient()
    room = room_service.create_room(
        api.CreateRoomRequest(
            name=f"session-{datetime.now().timestamp()}",
            metadata=json.dumps(scenario)
        )
    )
    
    # Generate participant token
    token = api.AccessToken(
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET
    )
    token.add_grant(api.VideoGrant(
        room_join=True,
        room=room.name
    ))
    
    return {"token": token.to_jwt(), "room_name": room.name}
```

## Browser Requirements

- Modern browser with WebRTC support (Chrome, Firefox, Safari, Edge)
- Microphone access required
- HTTPS required for production (localhost exempt for development)

## Troubleshooting

### Microphone Not Working
- Check browser permissions
- Ensure HTTPS is used (localhost is okay)
- Test microphone in browser settings

### Connection Failed
- Verify LIVEKIT_URL is correct
- Check LiveKit server is running
- Ensure API credentials are valid

### No Audio from Agent
- Check LiveKit agent is running
- Verify OpenAI API key is configured
- Check browser console for errors

## Resources

- [LiveKit Client SDK](https://docs.livekit.io/client-sdk-js/)
- [DifficultAI Documentation](../../README.md)
- [LiveKit Agents](https://docs.livekit.io/agents/)

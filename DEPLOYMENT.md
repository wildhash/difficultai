# DifficultAI Deployment Guide

This guide covers deploying the DifficultAI LiveKit voice agent to production.

## Prerequisites

- OpenAI API key with Realtime API access
- LiveKit server (Cloud or self-hosted)
- Python 3.9+

## Owner-pilot deployment decision

The checked-in worker writes private scorecards to `SCORECARD_DIR`. LiveKit
Cloud agent containers provide ephemeral local storage, so deploying the worker
there does not establish scorecard retention across replacement. For the owner
pilot, run the worker container on infrastructure where the checked-in named
volume is retained. It can still connect to a LiveKit Cloud project for rooms
and media transport.

```bash
cp .env.example .env
# Fill in LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and OPENAI_API_KEY.
make owner-pilot-deploy
docker compose -f compose.owner-pilot.yml logs -f worker
```

`owner-pilot-deploy` fails before starting the service unless the Compose model,
image build, and credentialed LiveKit connectivity preflight all pass. It then
requires the worker to remain running. If that final check fails, it stops only
the worker and preserves the named scorecard volume. The connectivity check does
not verify OpenAI access, live audio, or owner acceptance.

The image runs `python -m apps.livekit_agent start` as an unprivileged user and
stores evidence at `/data/scorecards`, backed by the
`difficultai-scorecards` volume. Never commit `.env` or the volume contents.
The Python CI workflow runs `scripts/verify-worker-image.sh` through this exact
Compose service. It validates the Compose model, builds the image, confirms its
runtime user and CLI, runs the offline preflight inside the service, and proves
a fixture remains readable by a replacement container on its configured named
volume. The check uses an isolated Compose project and deletes its fixture
volume. This is deployment-contract evidence only; it does not establish a
running worker or retained live scorecard.
After a real completed session, retain its session ID and run:

```bash
make owner-pilot-replace SESSION_ID=<session-id>
```

The command requires a structurally valid scorecard before replacement, force
recreates only the worker without rebuilding or removing volumes, then verifies
the scorecard again and compares its unprinted SHA-256 fingerprint. This proves
that exact private file remained available across that replacement. Record owner
acceptance separately as described in the README.

Rollback the worker without deleting evidence:

```bash
docker compose -f compose.owner-pilot.yml down
git checkout <known-good-commit> -- Dockerfile compose.owner-pilot.yml
docker compose -f compose.owner-pilot.yml up -d --build
```

Do not add `--volumes` to `docker compose down`; that deletes the named volume.

## Option 1: LiveKit Cloud managed agent

LiveKit Cloud provides managed infrastructure for running agents.

### 1. Sign Up for LiveKit Cloud

1. Go to https://cloud.livekit.io
2. Create an account (free tier available)
3. Create a new project

### 2. Get Your Credentials

From your LiveKit Cloud dashboard:
- **LIVEKIT_URL**: Your WebSocket URL (e.g., `wss://your-project.livekit.cloud`)
- **LIVEKIT_API_KEY**: Your API key (starts with `API`)
- **LIVEKIT_API_SECRET**: Your API secret

### 3. Set Up Environment Variables

Create a `.env` file in your project root:

```bash
OPENAI_API_KEY=sk-your-openai-key
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxx
LIVEKIT_API_SECRET=xxxxx
DEFAULT_VOICE=marin
```

### 4. Deploy the Agent

#### Using the current LiveKit CLI

```bash
# Install and authenticate the `lk` CLI using LiveKit's official instructions.
lk cloud auth

# First deployment; this creates livekit.toml.
lk agent create --secrets-file .env

# Later versions.
lk agent deploy
```

#### Manual Deployment

1. Push your code to a Git repository
2. Connect the repository to LiveKit Cloud
3. Set environment variables in the dashboard
4. Deploy from the dashboard

### 5. Verify Deployment

```bash
# Check agent status
lk agent status

# View logs
lk agent logs
```

## Option 2: Self-Hosted

For full control, deploy on your own infrastructure.

### 1. Deploy LiveKit Server

Follow the official guide: https://docs.livekit.io/deploy/

Quick options:
- **Docker**: Use official Docker images
- **Kubernetes**: Use Helm charts
- **VM**: Binary installation on Linux/macOS

Example Docker Compose:

```yaml
version: '3.8'
services:
  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:7882/udp"
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
    command: --config /etc/livekit.yaml
```

### 2. Deploy the Agent

#### Using systemd (Linux)

Create `/etc/systemd/system/difficultai-agent.service`:

```ini
[Unit]
Description=DifficultAI LiveKit Agent
After=network.target

[Service]
Type=simple
User=difficultai
WorkingDirectory=/opt/difficultai
Environment="OPENAI_API_KEY=sk-..."
Environment="LIVEKIT_URL=ws://localhost:7880"
Environment="LIVEKIT_API_KEY=..."
Environment="LIVEKIT_API_SECRET=..."
ExecStart=/usr/bin/python3 apps/livekit_agent/agent.py start
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable difficultai-agent
sudo systemctl start difficultai-agent
sudo systemctl status difficultai-agent
```

#### Using Docker

Use the checked-in `Dockerfile`; it starts the supported module entrypoint as an
unprivileged user.

Build and run:
```bash
docker build -t difficultai-agent .
docker run -d \
  --name difficultai-agent \
  --env-file .env \
  --mount type=volume,src=difficultai-scorecards,dst=/data/scorecards \
  difficultai-agent
```

#### Using Docker Compose

Use `compose.owner-pilot.yml`. It connects to the `LIVEKIT_URL` in `.env`; a
separately hosted LiveKit server is required only when that URL is self-hosted.

### 3. Configure Reverse Proxy (Optional)

For production, use nginx or similar:

```nginx
server {
    listen 443 ssl;
    server_name voice.difficultai.com;

    location / {
        proxy_pass http://localhost:7880;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | Yes | OpenAI API key | `sk-...` |
| `LIVEKIT_URL` | Yes | LiveKit server URL | `wss://your-project.livekit.cloud` |
| `LIVEKIT_API_KEY` | Yes | LiveKit API key | `APIxxxxx` |
| `LIVEKIT_API_SECRET` | Yes | LiveKit API secret | `xxxxx` |
| `DEFAULT_VOICE` | No | Default voice name | `marin` (default) |
| `DEEPGRAM_API_KEY` | No | Deepgram API key for STT fallback | `xxxxx` |

## Monitoring

### Logs

View agent logs:
```bash
# LiveKit Cloud
lk agent logs

# systemd
sudo journalctl -u difficultai-agent -f

# Docker
docker logs -f difficultai-agent
```

### Metrics

Monitor:
- Agent uptime
- Room connections
- Conversation duration
- Scorecard generation rate
- Error rates

### Health Checks

The agent automatically reconnects if disconnected. Monitor for:
- OpenAI API errors
- LiveKit connection issues
- Out of memory errors

## Scaling

### Horizontal Scaling

After the owner pilot passes, run multiple self-hosted worker instances with:

```bash
docker compose -f compose.owner-pilot.yml up -d --scale worker=3
```

### Load Balancing

LiveKit automatically load-balances across agent instances.

## Troubleshooting

### Agent Won't Start

1. Check environment variables are set correctly
2. Verify OpenAI API key has Realtime API access
3. Confirm LiveKit credentials are valid
4. Check network connectivity to LiveKit server

### Connection Issues

1. Verify `LIVEKIT_URL` format (should start with `wss://` or `ws://`)
2. Check firewall allows WebSocket connections
3. Test LiveKit server is accessible: `curl $LIVEKIT_URL/health`

### Audio Issues

1. Verify OpenAI API key is valid
2. Check voice name is supported
3. Test with different audio codecs
4. Monitor OpenAI API rate limits

### Performance Issues

1. Monitor CPU/memory usage
2. Check OpenAI API latency
3. Verify network bandwidth
4. Consider scaling horizontally

## Security

### Best Practices

1. **Use HTTPS/WSS**: Always use secure connections in production
2. **Rotate Secrets**: Regularly rotate API keys and secrets
3. **Rate Limiting**: Configure rate limits on LiveKit server
4. **Access Control**: Use room tokens to control access
5. **Logging**: Enable audit logging for compliance

### Room Security

Generate secure room tokens for users:

```python
from livekit import api

token = api.AccessToken(api_key, api_secret)
token.with_identity("user123")
token.with_name("User Name")
token.with_grants(api.VideoGrants(
    room_join=True,
    room="training-session-123"
))

# Pass this token to your client
jwt = token.to_jwt()
```

## Backup and Recovery

### Scorecards

Scorecards are saved to `SCORECARD_DIR/scorecard_<session_id>.json` (default
directory: `scorecards`). Mount persistent storage at that directory. Set up:

1. **Regular backups**: Copy scorecard files to persistent storage
2. **Database integration**: Store in PostgreSQL/MongoDB for long-term retention
3. **S3 upload**: Upload to cloud storage for durability

Example backup script:
```bash
#!/bin/bash
# Backup scorecards to S3
aws s3 sync ./scorecards/ s3://difficultai-scorecards/ --exclude "*" --include "scorecard_*.json"
```

## Updates and Maintenance

### Updating the Agent

1. Pull latest code
2. Update dependencies: `pip install -r requirements.txt --upgrade`
3. Restart the agent service
4. Verify with test conversation

### Zero-Downtime Updates

For production:
1. Deploy new version to new instances
2. Migrate traffic gradually
3. Drain old instances
4. Remove old instances

## Cost Estimation

### LiveKit Cloud

- Free tier: Up to 1000 minutes/month
- Pro: $0.009/minute/participant
- Enterprise: Custom pricing

### OpenAI Realtime API

- Audio input: $0.06/minute
- Audio output: $0.24/minute
- Typical conversation: ~$0.30/minute

### Infrastructure

- VPS: $5-50/month (self-hosted)
- Cloud: Variable based on usage
- Bandwidth: Minimal cost

## Support

- LiveKit Docs: https://docs.livekit.io
- OpenAI Docs: https://platform.openai.com/docs
- DifficultAI Issues: https://github.com/wildhash/difficultai/issues

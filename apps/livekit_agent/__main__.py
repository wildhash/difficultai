"""
DifficultAI LiveKit Agent - Module entry point

Allows running the agent as a module:
    python -m apps.livekit_agent dev
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from livekit.agents import cli, WorkerOptions
from apps.livekit_agent.agent import entrypoint

if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

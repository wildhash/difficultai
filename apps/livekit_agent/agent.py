"""
DifficultAI LiveKit Voice Agent

Production-ready LiveKit agent using OpenAI Realtime API for voice-to-voice
high-pressure conversation training.
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, Optional
from dataclasses import asdict

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import openai

# Add parent directories to path for imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from agents.architect import PersonaType, Scenario, ArchitectAgent
from agents.evaluator import EvaluatorAgent
from apps.livekit_agent.scenario_validator import (
    validate_scenario,
    get_missing_fields,
    is_scenario_complete
)

logger = logging.getLogger(__name__)


class SessionState:
    """Manages state for a single conversation session."""
    
    def __init__(self):
        self.scenario: Optional[Dict[str, Any]] = {}
        self.transcript: list = []
        self.collecting_metadata = False
        self.current_question_field: Optional[str] = None
        self.session_started = False
        
    def add_transcript_entry(self, role: str, text: str):
        """Add entry to transcript."""
        self.transcript.append({
            "role": role,
            "content": text,
            "timestamp": asyncio.get_event_loop().time()
        })


class DifficultAIAgent:
    """
    DifficultAI voice agent using LiveKit and OpenAI Realtime API.
    
    This agent:
    1. Accepts scenario metadata from job context
    2. Collects missing metadata conversationally
    3. Conducts high-pressure conversation using configured persona
    4. Tracks transcript in-memory
    5. Generates end-of-call scorecard
    """
    
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.session = SessionState()
        self.architect = ArchitectAgent()
        self.evaluator = EvaluatorAgent()
        self.default_voice = os.getenv("DEFAULT_VOICE", "marin")
        
    async def entrypoint(self):
        """Main agent entrypoint."""
        logger.info("DifficultAI agent starting...")
        
        # Parse job metadata for scenario configuration
        await self._load_scenario_from_metadata()
        
        # Connect to the room
        await self.ctx.connect()
        logger.info(f"Connected to room: {self.ctx.room.name}")
        
        # Wait for participant
        participant = await self.ctx.wait_for_participant()
        logger.info(f"Participant joined: {participant.identity}")
        
        # Set up OpenAI Realtime model
        voice = self.session.scenario.get('voice', self.default_voice)
        model = openai.realtime.RealtimeModel(
            voice=voice,
            temperature=0.8,
            instructions=self._build_system_instructions(),
        )
        
        # Create assistant
        assistant = agents.VoiceAssistant(
            vad=agents.silero.VAD.load(),
            stt=openai.realtime.RealtimeSTT(),
            llm=model,
            tts=openai.realtime.RealtimeTTS(),
        )
        
        # Set up event handlers
        assistant.on("user_speech_committed", self._on_user_speech)
        assistant.on("agent_speech_committed", self._on_agent_speech)
        
        # Start the assistant
        assistant.start(self.ctx.room, participant)
        
        # Initial greeting
        await self._send_initial_message(assistant)
        
        # Wait for session to end
        await assistant.wait_for_completion()
        
        # Generate and send scorecard
        await self._generate_scorecard()
        
    async def _load_scenario_from_metadata(self):
        """Load scenario configuration from job metadata."""
        metadata = self.ctx.job.metadata
        
        if metadata:
            try:
                self.session.scenario = json.loads(metadata)
                logger.info(f"Loaded scenario from metadata: {self.session.scenario}")
            except json.JSONDecodeError:
                logger.warning("Failed to parse metadata as JSON")
                self.session.scenario = {}
        
        # Check if we need to collect metadata
        missing = get_missing_fields(self.session.scenario)
        if missing:
            logger.info(f"Missing scenario fields: {missing}")
            self.session.collecting_metadata = True
            self.session.current_question_field = missing[0]
        
    def _build_system_instructions(self) -> str:
        """Build system instructions for the Realtime model."""
        
        if self.session.collecting_metadata:
            # In metadata collection mode
            return self._build_metadata_collection_instructions()
        else:
            # In conversation mode with configured persona
            return self._build_persona_instructions()
    
    def _build_metadata_collection_instructions(self) -> str:
        """Instructions for collecting missing metadata."""
        return """You are DifficultAI's setup assistant. You need to collect scenario information from the user.

Be brief and direct. Ask ONE question at a time to collect the following information:
1. persona_type: What type of scenario? (ANGRY_CUSTOMER, ELITE_INTERVIEWER, TOUGH_NEGOTIATOR, SKEPTICAL_INVESTOR, DEMANDING_CLIENT)
2. company: What company is involved?
3. role: What is your role in this scenario?
4. stakes: What's at stake in this conversation?
5. user_goal: What are you trying to achieve?
6. difficulty: Difficulty level 1-5 (1=easy, 5=maximum pressure)

Keep responses short and conversational. Once you have all information, confirm and say "Let's begin the scenario."
"""
    
    def _build_persona_instructions(self) -> str:
        """Build instructions based on configured persona."""
        scenario = self.session.scenario
        persona = scenario.get('persona_type', 'ELITE_INTERVIEWER')
        difficulty = scenario.get('difficulty', 3)
        
        base_instruction = f"""You are DifficultAI, a deliberately challenging AI agent designed to pressure-test users in high-stakes conversations.

SCENARIO CONTEXT:
- Persona: {persona}
- Company: {scenario.get('company', 'N/A')}
- Role: {scenario.get('role', 'N/A')}
- Stakes: {scenario.get('stakes', 'N/A')}
- User Goal: {scenario.get('user_goal', 'N/A')}
- Difficulty Level: {difficulty}/5

CORE BEHAVIORS:
1. Interrupt vague answers - Demand specificity and concrete details
2. Escalate when deflected - Increase pressure when user avoids questions
3. Challenge assumptions - Question unfounded claims
4. Push for concrete commitments - Require specific numbers, dates, actions
5. Increase difficulty gradually based on user performance

YOUR GOAL: Expose weaknesses, force clarity, and simulate real pressure.

"""
        
        # Add persona-specific behaviors
        persona_behaviors = {
            'ANGRY_CUSTOMER': "Act as a frustrated customer demanding immediate resolution. Express urgency and frustration.",
            'ELITE_INTERVIEWER': "Act as a senior interviewer testing technical and cultural fit. Ask probing questions.",
            'TOUGH_NEGOTIATOR': "Act as an experienced negotiator seeking the best deal. Push for concessions.",
            'SKEPTICAL_INVESTOR': "Act as an investor questioning business fundamentals. Demand data and metrics.",
            'DEMANDING_CLIENT': "Act as a high-value client with strict requirements. Set high expectations."
        }
        
        if persona in persona_behaviors:
            base_instruction += f"\nPERSONA BEHAVIOR: {persona_behaviors[persona]}\n"
        
        base_instruction += f"""
DIFFICULTY LEVEL {difficulty}/5:
"""
        
        if difficulty <= 2:
            base_instruction += "- Be firm but professional\n- Give user time to respond\n"
        elif difficulty <= 4:
            base_instruction += "- Be aggressive and challenging\n- Interrupt weak responses\n- Demand immediate specifics\n"
        else:
            base_instruction += "- Be confrontational and unforgiving\n- Zero tolerance for vagueness\n- Maximum pressure\n- Expose every weakness\n"
        
        return base_instruction
    
    async def _send_initial_message(self, assistant):
        """Send initial greeting message."""
        if self.session.collecting_metadata:
            msg = "Hello! I'm DifficultAI. Before we start, I need to set up your scenario. What type of high-pressure conversation would you like to practice? Your options are: ANGRY_CUSTOMER, ELITE_INTERVIEWER, TOUGH_NEGOTIATOR, SKEPTICAL_INVESTOR, or DEMANDING_CLIENT."
        else:
            persona = self.session.scenario.get('persona_type', 'interviewer')
            msg = f"Let's begin. I'm your {persona.replace('_', ' ').lower()}. Are you ready?"
        
        await assistant.say(msg)
        self.session.add_transcript_entry("assistant", msg)
    
    async def _on_user_speech(self, text: str):
        """Handle user speech."""
        logger.info(f"User: {text}")
        self.session.add_transcript_entry("user", text)
        
        # If collecting metadata, process the response
        if self.session.collecting_metadata:
            await self._process_metadata_response(text)
    
    async def _on_agent_speech(self, text: str):
        """Handle agent speech."""
        logger.info(f"Agent: {text}")
        self.session.add_transcript_entry("assistant", text)
    
    async def _process_metadata_response(self, text: str):
        """Process user response when collecting metadata."""
        field = self.session.current_question_field
        
        if not field:
            return
        
        # Store the response
        if field == 'persona_type':
            # Try to match to a valid persona type
            text_upper = text.upper()
            for persona in PersonaType:
                if persona.value in text_upper:
                    self.session.scenario[field] = persona.value
                    break
        elif field == 'difficulty':
            # Extract number from text
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                diff = int(numbers[0])
                if 1 <= diff <= 5:
                    self.session.scenario[field] = diff
        else:
            self.session.scenario[field] = text
        
        # Check what's still missing
        missing = get_missing_fields(self.session.scenario)
        
        if missing:
            # Move to next field
            self.session.current_question_field = missing[0]
        else:
            # All metadata collected
            self.session.collecting_metadata = False
            self.session.current_question_field = None
            self.session.session_started = True
            logger.info(f"Metadata collection complete: {self.session.scenario}")
    
    async def _generate_scorecard(self):
        """Generate end-of-call scorecard using EvaluatorAgent."""
        logger.info("Generating scorecard...")
        
        # Prepare metrics from transcript
        metrics = self._analyze_transcript()
        
        # Use evaluator to generate scorecard
        evaluation = self.evaluator.evaluate_conversation(
            metrics=metrics,
            scenario=self.session.scenario,
            transcript=self.session.transcript
        )
        
        # Generate report
        report = self.evaluator.get_summary_report(evaluation)
        
        logger.info("=== SCORECARD ===")
        logger.info(report)
        
        # Save to file for persistence
        scorecard_file = f"scorecard_{self.ctx.room.name}.json"
        with open(scorecard_file, 'w') as f:
            json.dump({
                'scenario': self.session.scenario,
                'evaluation': evaluation,
                'transcript': self.session.transcript
            }, f, indent=2)
        
        logger.info(f"Scorecard saved to {scorecard_file}")
        
        return evaluation
    
    def _analyze_transcript(self) -> Dict[str, Any]:
        """Analyze transcript to extract metrics."""
        user_messages = [t for t in self.session.transcript if t['role'] == 'user']
        
        # Simple heuristic-based analysis
        vague_indicators = ['maybe', 'possibly', 'probably', 'i think', 'perhaps', 'kind of', 'sort of']
        deflection_indicators = ["let's talk about", "what about", "but first", "before we"]
        commitment_indicators = ['i will', "i'll", 'i commit', 'i promise', 'by']
        
        vague_count = 0
        deflection_count = 0
        commitment_count = 0
        
        for msg in user_messages:
            content = msg['content'].lower()
            if any(ind in content for ind in vague_indicators):
                vague_count += 1
            if any(ind in content for ind in deflection_indicators):
                deflection_count += 1
            if any(ind in content for ind in commitment_indicators):
                commitment_count += 1
        
        total_exchanges = len(user_messages)
        
        return {
            'vague_response_count': vague_count,
            'deflection_count': deflection_count,
            'commitments_made': commitment_count,
            'total_exchanges': total_exchanges,
            'current_difficulty': self.session.scenario.get('difficulty', 3),
            'scenario_difficulty': self.session.scenario.get('difficulty', 3)
        }


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the LiveKit agent."""
    await DifficultAIAgent(ctx).entrypoint()


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

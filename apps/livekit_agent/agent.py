"""DifficultAI voice worker for the pinned LiveKit Agents 1.x SDK.

VOICE_MODE=realtime (default) uses OpenAI speech-to-speech. VOICE_MODE=pipeline
selects STT -> LLM -> TTS explicitly; automatic provider failover is not claimed.
Committed turns are forwarded to the web demo and retained with a per-session
scorecard in SCORECARD_DIR. Live provider operation requires an acceptance run.
"""

import asyncio
import logging
import os
import json
import uuid
import tempfile
from typing import Dict, Any, Optional

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.llm import ChatMessage
from livekit.agents.voice.room_io import RoomOptions
from livekit.plugins import openai, silero

# Add parent directories to path for imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from agents.architect import PersonaType, ArchitectAgent
from agents.evaluator import EvaluatorAgent
from apps.livekit_agent.scenario_validator import get_missing_fields
from difficultai.observability import get_tracer

logger = logging.getLogger(__name__)


class SessionState:
    """Manages state for a single conversation session."""
    
    def __init__(self):
        self.scenario: Optional[Dict[str, Any]] = {}
        self.transcript: list = []
        self.collecting_metadata = False
        self.current_question_field: Optional[str] = None
        self.session_started = False
        self.question_plan: list = []  # Generated question plan (3-6 questions)
        self.questions_asked = 0  # Track questions asked
        
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
        self.opik_tracer = get_tracer()  # Initialize Opik tracer
        self.session_id = uuid.uuid4().hex
        self._voice_agent = None
        self._message_tasks = set()
        self._session_error = None
        
    async def entrypoint(self):
        """Run a LiveKit Agents 1.x session and finalize its evidence once."""
        await self.ctx.connect()
        await self._load_scenario_from_metadata()
        participant = await self.ctx.wait_for_participant()
        job_id = str(getattr(self.ctx.job, "id", "unknown"))
        if self.opik_tracer.enabled:
            self.opik_tracer.start_session_trace(
                livekit_room=self.ctx.room.name,
                session_id=self.session_id,
                participant_identity=participant.identity,
                scenario=self.session.scenario,
            )

        assistant = None
        closed = asyncio.Event()
        finalize_lock = asyncio.Lock()
        finalized = False

        async def finalize():
            nonlocal finalized
            async with finalize_lock:
                if finalized:
                    return
                # Drain pending metadata/transcript sends before persisting the snapshot.
                if self._message_tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*list(self._message_tasks), return_exceptions=True),
                            timeout=5,
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Timed out forwarding final transcript events")
                evaluation = await self._generate_scorecard()
                finalized = True
                if self.opik_tracer.enabled:
                    self.opik_tracer.log_scorecard_feedback_scores(evaluation)
                    self.opik_tracer.end_session_trace(output={
                        "status": "failed" if self._session_error else "completed",
                        "job_id": job_id,
                        "scorecard": evaluation,
                        "transcript_length": len(self.session.transcript),
                    })

        async def shutdown():
            try:
                if assistant is not None:
                    await assistant.aclose()
            finally:
                closed.set()
                await finalize()

        def on_close(event):
            if event.error is not None or event.reason.value == "error":
                self._session_error = "LiveKit session closed with a provider error"
            closed.set()

        try:
            mode = os.getenv("VOICE_MODE", "realtime").strip().lower()
            if mode == "realtime":
                assistant = await self._create_realtime_assistant()
            elif mode == "pipeline":
                assistant = await self._create_fallback_assistant()
            else:
                raise ValueError("VOICE_MODE must be 'realtime' or 'pipeline'")
            self._voice_agent = Agent(instructions=self._build_system_instructions())
            assistant.on("conversation_item_added", self._on_conversation_item_added)
            assistant.on("close", on_close)
            self.ctx.add_shutdown_callback(shutdown)
            await assistant.start(
                room=self.ctx.room,
                agent=self._voice_agent,
                room_options=RoomOptions(participant_identity=participant.identity),
                record=False,
            )
            await self._send_initial_message(assistant)
            await closed.wait()
            if self._session_error:
                raise RuntimeError(self._session_error)
        except Exception as error:
            self._session_error = str(error)
            if self.opik_tracer.enabled:
                self.opik_tracer.log_error(error, context={"stage": "voice_session"})
            raise
        finally:
            try:
                await shutdown()
            finally:
                self.ctx.shutdown(reason="voice session finished")

    async def _create_realtime_assistant(self):
        """Construct the pinned SDK's speech-to-speech session without legacy adapters."""
        return AgentSession(
            llm=openai.realtime.RealtimeModel(
                voice=self.session.scenario.get("voice", self.default_voice),
            ),
            allow_interruptions=True,
        )

    async def _create_fallback_assistant(self):
        """Construct the explicitly selected STT -> LLM -> TTS mode."""
        if os.getenv("DEEPGRAM_API_KEY"):
            from livekit.plugins import deepgram
            stt = deepgram.STT()
        else:
            stt = openai.STT()
        return AgentSession(
            vad=silero.VAD.load(),
            stt=stt,
            llm=openai.LLM(model="gpt-4", temperature=0.8),
            # The realtime voice selection is not necessarily valid for tts-1.
            tts=openai.TTS(voice=os.getenv("FALLBACK_TTS_VOICE", "alloy")),
            allow_interruptions=True,
        )

    def _on_conversation_item_added(self, event):
        """Record committed turns synchronously; the SDK requires sync listeners."""
        item = event.item
        if not isinstance(item, ChatMessage) or item.role not in ("user", "assistant"):
            return
        text = item.text_content
        if not text:
            return
        self.session.add_transcript_entry(item.role, text)
        task = asyncio.create_task(self._forward_conversation_item(item.role, text))
        self._message_tasks.add(task)
        task.add_done_callback(self._message_task_done)

    def _message_task_done(self, task):
        self._message_tasks.discard(task)
        if not task.cancelled() and (error := task.exception()) is not None:
            self._session_error = "Failed to process a conversation event"
            logger.error("Conversation event failed", exc_info=error)

    async def _forward_conversation_item(self, role, text):
        if role == "user" and self.session.collecting_metadata:
            await self._process_metadata_response(text)
            await self._voice_agent.update_instructions(self._build_system_instructions())
        # Keep the existing web demo's JSON data-channel contract.
        try:
            await self.ctx.room.local_participant.publish_data(
                json.dumps({"type": "transcript", "role": role, "text": text}).encode(),
                reliable=True,
            )
        except Exception:
            # The participant may already have left; the local transcript is retained.
            logger.warning("Could not forward transcript to the room", exc_info=True)

    async def _load_scenario_from_metadata(self):
        """Load scenario configuration from job metadata."""
        metadata = self.ctx.job.metadata or self.ctx.room.metadata
        
        if metadata:
            try:
                self.session.scenario = json.loads(metadata)
                if not isinstance(self.session.scenario, dict):
                    raise ValueError("Scenario metadata must be a JSON object")
                logger.info(f"Loaded scenario from metadata: {self.session.scenario}")
            except ValueError:
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
6. difficulty: Difficulty level 0-1 (0=easy, 0.5=moderate, 1=maximum pressure)

Keep responses short and conversational. Once you have all information, confirm and say "Let's begin the scenario."
"""
    
    def _build_persona_instructions(self) -> str:
        """Build instructions based on configured persona."""
        scenario = self.session.scenario
        persona = scenario.get('persona_type', 'ELITE_INTERVIEWER')
        # Support both 0-1 and legacy 1-5 difficulty scales
        difficulty = scenario.get('difficulty', 0.6)
        
        # Normalize to 0-1 if legacy 1-5 scale is used
        if difficulty > 1:
            difficulty = (difficulty - 1) / 4  # Convert 1-5 to 0-1
        
        # Generate question plan if not already done
        if not self.session.question_plan:
            self.session.question_plan = self._generate_question_plan(scenario, difficulty)
        
        base_instruction = f"""You are DifficultAI, a deliberately challenging AI agent designed to pressure-test users in high-stakes conversations.

SCENARIO CONTEXT:
- Persona: {persona}
- Company: {scenario.get('company', 'N/A')}
- Role: {scenario.get('role', 'N/A')}
- Stakes: {scenario.get('stakes', 'N/A')}
- User Goal: {scenario.get('user_goal', 'N/A')}
- Difficulty Level: {difficulty:.2f} (0=easy, 1=maximum pressure)

QUESTION PLAN (Ask these {len(self.session.question_plan)} questions during the conversation):
"""
        for i, question in enumerate(self.session.question_plan, 1):
            base_instruction += f"{i}. {question}\n"
        
        base_instruction += """
CORE BEHAVIORS:
1. Interrupt vague answers - Demand specificity and concrete details
2. Escalate when deflected - Increase pressure when user avoids questions
3. Challenge assumptions - Question unfounded claims
4. Push for concrete commitments - Require specific numbers, dates, actions
5. Follow the question plan while adapting based on user responses

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
DIFFICULTY LEVEL {difficulty:.2f} (0-1 scale):
"""
        
        if difficulty <= 0.4:
            base_instruction += "- Be firm but professional\n- Give user time to respond\n"
        elif difficulty <= 0.7:
            base_instruction += "- Be aggressive and challenging\n- Interrupt weak responses\n- Demand immediate specifics\n"
        else:
            base_instruction += "- Be confrontational and unforgiving\n- Zero tolerance for vagueness\n- Maximum pressure\n- Expose every weakness\n"
        
        return base_instruction
    
    def _generate_question_plan(self, scenario: Dict[str, Any], difficulty: float) -> list:
        """
        Generate a question plan (3-6 questions) based on scenario.
        
        Args:
            scenario: Scenario configuration
            difficulty: Difficulty level (0-1)
            
        Returns:
            List of 3-6 questions to ask during the conversation
            
        Examples:
            difficulty=0.0 → 3 questions
            difficulty=0.5 → 4 questions (int(3 + 0.5*3) = int(4.5) = 4)
            difficulty=1.0 → 6 questions
        """
        persona = scenario.get('persona_type', 'ELITE_INTERVIEWER')
        company = scenario.get('company', 'the company')
        role = scenario.get('role', 'this role')
        stakes = scenario.get('stakes', 'this situation')
        user_goal = scenario.get('user_goal', 'your objectives')
        
        # Number of questions based on difficulty (3-6 range)
        # Formula: 3 + (difficulty * 3) → 3.0 to 6.0, cast to int
        num_questions = int(3 + (difficulty * 3))  # 3 at difficulty=0, 6 at difficulty=1
        
        question_templates = {
            'ELITE_INTERVIEWER': [
                f"Tell me about your experience with {role} - what specific achievements can you point to?",
                f"Walk me through a time you failed. What went wrong and how did you recover?",
                f"Why {company}? What makes us different from your other options?",
                f"Where do you see yourself in 5 years? Be specific.",
                f"Give me an example of when you had to make a difficult decision with incomplete information.",
                f"What's your biggest weakness and what are you doing about it?",
            ],
            'ANGRY_CUSTOMER': [
                f"This is unacceptable. How are you going to fix this RIGHT NOW?",
                f"I've been waiting for weeks. What's your excuse this time?",
                f"Why should I believe you when you've already let me down?",
                f"What guarantee do I have that this won't happen again?",
                f"I'm talking to your competitors. Why shouldn't I switch?",
                f"Give me one reason not to cancel my contract today.",
            ],
            'TOUGH_NEGOTIATOR': [
                f"Your price is too high. What can you do about it?",
                f"I need concrete numbers. What's your best offer?",
                f"Your competitor offered better terms. Match it or lose the deal.",
                f"What's your walk-away point? I need to know we're in the same ballpark.",
                f"Show me the ROI. Why is this worth my investment?",
                f"What concessions can you make to close this today?",
            ],
            'SKEPTICAL_INVESTOR': [
                f"Your market size claims seem inflated. Show me the data.",
                f"What's your customer acquisition cost and why is it sustainable?",
                f"Who are your competitors and why will you win?",
                f"Your burn rate concerns me. When will you be profitable?",
                f"What happens if your key assumption is wrong?",
                f"Why are you the right team to execute this vision?",
            ],
            'DEMANDING_CLIENT': [
                f"I expect {stakes}. Can you deliver or should I look elsewhere?",
                f"Walk me through your quality assurance process. Convince me you won't drop the ball.",
                f"I need weekly updates. What's your communication plan?",
                f"What happens when things go wrong? Show me your contingency plan.",
                f"Your timeline seems optimistic. What if you're late?",
                f"I'm paying premium rates. What premium value am I getting?",
            ],
        }
        
        # Get templates for this persona, default to interviewer if not found
        templates = question_templates.get(persona, question_templates['ELITE_INTERVIEWER'])
        
        # Select questions based on number needed
        questions = templates[:num_questions]
        
        return questions
    
    async def _send_initial_message(self, assistant):
        """Send initial greeting message."""
        if self.session.collecting_metadata:
            msg = "Hello! I'm DifficultAI. Before we start, I need to set up your scenario. What type of high-pressure conversation would you like to practice? Your options are: ANGRY_CUSTOMER, ELITE_INTERVIEWER, TOUGH_NEGOTIATOR, SKEPTICAL_INVESTOR, or DEMANDING_CLIENT."
        else:
            persona = self.session.scenario.get('persona_type', 'interviewer')
            msg = f"Let's begin. I'm your {persona.replace('_', ' ').lower()}. Are you ready?"
        
        # generate_reply works for realtime and pipelined models; say requires TTS.
        await assistant.generate_reply(instructions=f"Greet the participant with: {msg}")
        # The committed conversation event records what was actually spoken.

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
            # Extract number from text and normalize to 0-1
            import re
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                diff = float(numbers[0])
                # If value is > 1, assume legacy 1-5 scale and convert
                if diff > 1:
                    diff = (diff - 1) / 4  # Convert 1-5 to 0-1
                # Clamp to 0-1 range
                diff = max(0.0, min(1.0, diff))
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
        
        # One unique, atomic file per session; room names never become paths.
        directory = Path(os.getenv("SCORECARD_DIR", "scorecards"))
        directory.mkdir(parents=True, exist_ok=True)
        scorecard_file = directory / f"scorecard_{self.session_id}.json"
        payload = {
            "session_id": self.session_id,
            "room": self.ctx.room.name,
            "job_id": str(getattr(self.ctx.job, "id", "unknown")),
            "status": "failed" if self._session_error else "completed",
            "error": self._session_error,
            "scenario": self.session.scenario,
            "evaluation": evaluation,
            "transcript": self.session.transcript,
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=directory, suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                json.dump(payload, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, scorecard_file)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        logger.info("Scorecard saved to %s", scorecard_file)

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

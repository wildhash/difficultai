"""
Difficult AI Agents

This module contains the core agent workforce that powers DifficultAI:
- Architect: Designs interview scenarios and conversation structures
- Researcher: Gathers company and role context
- Adversary: Live conversational agent that pressure-tests users
- Evaluator: Scores performance and provides feedback
"""

from .architect import ArchitectAgent
from .researcher import ResearcherAgent
from .adversary import AdversaryAgent
from .evaluator import EvaluatorAgent

__all__ = [
    "ArchitectAgent",
    "ResearcherAgent",
    "AdversaryAgent",
    "EvaluatorAgent",
]

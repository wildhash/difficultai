"""
Evaluator Agent

Scores performance and provides feedback on high-pressure conversations.

Responsibilities:
- Analyze conversation transcripts
- Score user performance across multiple dimensions
- Provide actionable feedback
- Identify strengths and weaknesses
- Generate improvement recommendations
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PerformanceScore:
    """Performance scoring across multiple dimensions (1-10 scale)."""
    clarity: float  # 1-10: How clear and specific were responses
    confidence: float  # 1-10: Confidence level demonstrated
    commitment: float  # 1-10: Quality of commitments made
    adaptability: float  # 1-10: Ability to adapt under pressure
    composure: float  # 1-10: Ability to stay calm under pressure
    effectiveness: float  # 1-10: Overall effectiveness in achieving goals
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "clarity": self.clarity,
            "confidence": self.confidence,
            "commitment": self.commitment,
            "adaptability": self.adaptability,
            "composure": self.composure,
            "effectiveness": self.effectiveness
        }


@dataclass
class Feedback:
    """Structured feedback for user performance."""
    coaching_points: List[str]  # Exactly 3 coaching bullets
    key_moments: List[str]  # Specific conversation moments to review


class EvaluatorAgent:
    """
    Scores and evaluates user performance in high-pressure scenarios.
    
    The evaluator analyzes conversations and provides structured feedback
    to help users improve their performance.
    """
    
    def __init__(self):
        """Initialize the evaluator agent."""
        self.evaluations: List[Dict[str, Any]] = []
    
    def evaluate_conversation(
        self,
        metrics: Dict[str, Any],
        scenario: Optional[Dict[str, Any]] = None,
        transcript: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a conversation and generate scores with feedback.
        
        Args:
            metrics: Performance metrics from adversary agent
            scenario: Original scenario context
            transcript: Optional conversation transcript
            
        Returns:
            Evaluation results with 6 scores (1-10) and 3 coaching bullets
        """
        # Calculate dimension scores (0-100 internally, will convert to 1-10)
        clarity_score = self._calculate_clarity_score(metrics)
        confidence_score = self._calculate_confidence_score(metrics)
        commitment_score = self._calculate_commitment_score(metrics)
        adaptability_score = self._calculate_adaptability_score(metrics)
        composure_score = self._calculate_composure_score(metrics)
        
        # Calculate effectiveness score based on overall performance
        effectiveness_score = (
            clarity_score * 0.25 +
            confidence_score * 0.2 +
            commitment_score * 0.25 +
            adaptability_score * 0.15 +
            composure_score * 0.15
        )
        
        # Convert from 0-100 scale to 1-10 scale
        scores = PerformanceScore(
            clarity=self._convert_to_10_scale(clarity_score),
            confidence=self._convert_to_10_scale(confidence_score),
            commitment=self._convert_to_10_scale(commitment_score),
            adaptability=self._convert_to_10_scale(adaptability_score),
            composure=self._convert_to_10_scale(composure_score),
            effectiveness=self._convert_to_10_scale(effectiveness_score)
        )
        
        # Generate feedback with exactly 3 coaching bullets
        feedback = self._generate_feedback(metrics, scores, scenario)
        
        evaluation = {
            "scores": scores.to_dict(),
            "feedback": {
                "coaching_points": feedback.coaching_points[:3],  # Ensure exactly 3
                "key_moments": feedback.key_moments
            },
            "metrics": metrics,
            "scenario": scenario
        }
        
        self.evaluations.append(evaluation)
        return evaluation
    
    def _convert_to_10_scale(self, score_100: float) -> float:
        """
        Convert a 0-100 score to 1-10 scale.
        
        Examples:
            0 → 1.0
            50 → 5.5
            100 → 10.0
        
        Formula: 1 + (score_100 / 100.0) * 9
        """
        # Map 0-100 to 1-10 (never give 0, minimum is 1)
        return max(1.0, min(10.0, 1 + (score_100 / 100.0) * 9))
    
    def _calculate_composure_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate composure score based on how well user maintained calm.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Composure score (0-100, will be converted to 1-10)
        """
        # Composure is inversely related to both vague responses and deflections
        vague_count = metrics.get("vague_response_count", 0)
        deflection_count = metrics.get("deflection_count", 0)
        total_exchanges = metrics.get("total_exchanges", 1)
        
        if total_exchanges == 0:
            return 100.0
        
        # Both vague responses and deflections indicate loss of composure
        stress_indicators = (vague_count + deflection_count) / total_exchanges
        score = 100.0 - (stress_indicators * 50)  # Less penalty than for clarity/confidence alone
        
        return max(0.0, min(100.0, score))
    
    def _calculate_clarity_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate clarity score based on vague response count.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Clarity score (0-100)
        """
        vague_count = metrics.get("vague_response_count", 0)
        total_exchanges = metrics.get("total_exchanges", 1)
        
        # Start at 100, deduct based on vague response ratio
        if total_exchanges == 0:
            return 100.0
        
        vague_ratio = vague_count / total_exchanges
        score = 100.0 - (vague_ratio * 100)
        
        return max(0.0, min(100.0, score))
    
    def _calculate_confidence_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on deflection patterns.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Confidence score (0-100)
        """
        deflection_count = metrics.get("deflection_count", 0)
        total_exchanges = metrics.get("total_exchanges", 1)
        
        if total_exchanges == 0:
            return 100.0
        
        deflection_ratio = deflection_count / total_exchanges
        score = 100.0 - (deflection_ratio * 100)
        
        return max(0.0, min(100.0, score))
    
    def _calculate_commitment_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate commitment score based on concrete commitments made.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Commitment score (0-100)
        """
        commitments = metrics.get("commitments_made", 0)
        total_exchanges = metrics.get("total_exchanges", 1)
        
        if total_exchanges == 0:
            return 0.0
        
        # Good ratio is at least 1 commitment per 3 exchanges
        target_ratio = 1 / 3
        actual_ratio = commitments / total_exchanges
        
        score = (actual_ratio / target_ratio) * 100
        
        return max(0.0, min(100.0, score))
    
    def _calculate_adaptability_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate adaptability score based on difficulty progression.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Adaptability score (0-100)
        """
        current_difficulty = metrics.get("current_difficulty", 1)
        scenario_difficulty = metrics.get("scenario_difficulty", 1)
        
        # If difficulty stayed same or decreased, that's good
        difficulty_delta = current_difficulty - scenario_difficulty
        
        if difficulty_delta <= 0:
            # Maintained or improved
            score = 100.0
        else:
            # Difficulty increased - deduct points
            score = 100.0 - (difficulty_delta * 20)
        
        return max(0.0, min(100.0, score))
    
    def _generate_feedback(
        self,
        metrics: Dict[str, Any],
        scores: PerformanceScore,
        scenario: Optional[Dict[str, Any]]
    ) -> Feedback:
        """
        Generate structured feedback with exactly 3 coaching points.
        
        Args:
            metrics: Performance metrics
            scores: Calculated scores (1-10 scale)
            scenario: Scenario context
            
        Returns:
            Structured feedback with 3 coaching bullets
        """
        coaching_candidates = []
        key_moments = []
        
        # Analyze clarity (1-10 scale)
        if scores.clarity < 5:
            coaching_candidates.append(("clarity", 
                "Focus on specificity: Replace vague language with concrete numbers, dates, and commitments"))
        elif scores.clarity >= 8:
            coaching_candidates.append(("clarity_strength",
                "Excellent clarity - maintain this level of specificity in future conversations"))
        
        # Analyze confidence (1-10 scale)
        if scores.confidence < 5:
            coaching_candidates.append(("confidence",
                "Address questions directly: Avoid deflecting or changing topics when challenged"))
        elif scores.confidence >= 8:
            coaching_candidates.append(("confidence_strength",
                "Strong confidence shown - keep facing difficult questions head-on"))
        
        # Analyze commitments (1-10 scale)
        if scores.commitment < 5:
            coaching_candidates.append(("commitment",
                "Make concrete commitments: Include specific timelines and measurable deliverables"))
        elif scores.commitment >= 8:
            coaching_candidates.append(("commitment_strength",
                "Great commitment quality - continue providing specific, actionable promises"))
        
        # Analyze adaptability (1-10 scale)
        if scores.adaptability < 5:
            coaching_candidates.append(("adaptability",
                "Improve under pressure: Practice maintaining performance when difficulty increases"))
        
        # Analyze composure (1-10 scale)
        if scores.composure < 5:
            coaching_candidates.append(("composure",
                "Stay calm and collected: Take a breath before responding when feeling pressured"))
        
        # Analyze effectiveness (1-10 scale)
        if scores.effectiveness < 5:
            coaching_candidates.append(("effectiveness",
                "Align responses with goals: Keep your objective in mind and steer toward it"))
        
        # Select top 3 coaching points prioritizing areas that need improvement
        # Sort by category to prioritize weaknesses over strengths
        coaching_candidates.sort(key=lambda x: (
            0 if "strength" not in x[0] else 1,  # Weaknesses first
            -scores.__dict__.get(x[0].replace("_strength", ""), 0)  # Lower scores first
        ))
        
        coaching_points = [text for _, text in coaching_candidates[:3]]
        
        # Ensure we have exactly 3 coaching points
        while len(coaching_points) < 3:
            coaching_points.append("Continue practicing high-pressure conversations to build resilience")
        
        # Add key moments
        if metrics.get("vague_response_count", 0) > 0:
            key_moments.append(f"Review {metrics['vague_response_count']} instances of vague language")
        
        if metrics.get("deflection_count", 0) > 0:
            key_moments.append(f"Examine {metrics['deflection_count']} deflection patterns")
        
        if metrics.get("commitments_made", 0) > 0:
            key_moments.append(f"Note {metrics['commitments_made']} successful commitments made")
        
        if not key_moments:
            key_moments.append("Review full transcript for improvement opportunities")
        
        return Feedback(
            coaching_points=coaching_points[:3],  # Ensure exactly 3
            key_moments=key_moments
        )
    
    def get_summary_report(self, evaluation: Dict[str, Any]) -> str:
        """
        Generate a text summary report of an evaluation.
        
        Args:
            evaluation: Evaluation results
            
        Returns:
            Formatted text report with 6 scores (1-10) and 3 coaching bullets
        """
        scores = evaluation["scores"]
        feedback = evaluation["feedback"]
        
        report = f"""
PERFORMANCE SCORECARD
=====================

SCORES (1-10 scale):
  Clarity:        {scores['clarity']:.1f}/10
  Confidence:     {scores['confidence']:.1f}/10
  Commitment:     {scores['commitment']:.1f}/10
  Adaptability:   {scores['adaptability']:.1f}/10
  Composure:      {scores['composure']:.1f}/10
  Effectiveness:  {scores['effectiveness']:.1f}/10

COACHING POINTS:
"""
        for i, point in enumerate(feedback["coaching_points"], 1):
            report += f"  {i}. {point}\n"
        
        if feedback["key_moments"]:
            report += "\nKEY MOMENTS TO REVIEW:\n"
            for moment in feedback["key_moments"]:
                report += f"  • {moment}\n"
        
        return report.strip()

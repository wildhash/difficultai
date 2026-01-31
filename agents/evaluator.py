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
    """Performance scoring across multiple dimensions."""
    clarity: float  # 0-100: How clear and specific were responses
    confidence: float  # 0-100: Confidence level demonstrated
    commitment: float  # 0-100: Quality of commitments made
    adaptability: float  # 0-100: Ability to adapt under pressure
    overall: float  # 0-100: Overall performance score
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "clarity": self.clarity,
            "confidence": self.confidence,
            "commitment": self.commitment,
            "adaptability": self.adaptability,
            "overall": self.overall
        }


@dataclass
class Feedback:
    """Structured feedback for user performance."""
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
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
            Evaluation results with scores and feedback
        """
        # Calculate dimension scores
        clarity_score = self._calculate_clarity_score(metrics)
        confidence_score = self._calculate_confidence_score(metrics)
        commitment_score = self._calculate_commitment_score(metrics)
        adaptability_score = self._calculate_adaptability_score(metrics)
        
        # Calculate overall score
        overall_score = (
            clarity_score * 0.3 +
            confidence_score * 0.2 +
            commitment_score * 0.3 +
            adaptability_score * 0.2
        )
        
        scores = PerformanceScore(
            clarity=clarity_score,
            confidence=confidence_score,
            commitment=commitment_score,
            adaptability=adaptability_score,
            overall=overall_score
        )
        
        # Generate feedback
        feedback = self._generate_feedback(metrics, scores, scenario)
        
        evaluation = {
            "scores": scores.to_dict(),
            "feedback": {
                "strengths": feedback.strengths,
                "weaknesses": feedback.weaknesses,
                "recommendations": feedback.recommendations,
                "key_moments": feedback.key_moments
            },
            "metrics": metrics,
            "scenario": scenario
        }
        
        self.evaluations.append(evaluation)
        return evaluation
    
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
        Generate structured feedback based on performance.
        
        Args:
            metrics: Performance metrics
            scores: Calculated scores
            scenario: Scenario context
            
        Returns:
            Structured feedback
        """
        strengths = []
        weaknesses = []
        recommendations = []
        key_moments = []
        
        # Analyze clarity
        if scores.clarity >= 80:
            strengths.append("Clear and specific communication")
        elif scores.clarity < 50:
            weaknesses.append("Frequent vague or unclear responses")
            recommendations.append("Practice giving specific answers with numbers and dates")
        
        # Analyze confidence
        if scores.confidence >= 80:
            strengths.append("Confident, direct responses without deflection")
        elif scores.confidence < 50:
            weaknesses.append("Tendency to deflect or avoid direct questions")
            recommendations.append("Face difficult questions head-on instead of changing topics")
        
        # Analyze commitments
        if scores.commitment >= 70:
            strengths.append("Strong concrete commitments made")
        elif scores.commitment < 40:
            weaknesses.append("Lack of specific commitments")
            recommendations.append("Make concrete commitments with specific timelines and deliverables")
        
        # Analyze adaptability
        if scores.adaptability >= 80:
            strengths.append("Maintained composure under pressure")
        elif scores.adaptability < 50:
            weaknesses.append("Performance degraded as pressure increased")
            recommendations.append("Practice staying calm and clear when challenged")
        
        # Add key moments
        if metrics.get("vague_response_count", 0) > 0:
            key_moments.append(f"Review moments with vague language ({metrics['vague_response_count']} instances)")
        
        if metrics.get("deflection_count", 0) > 0:
            key_moments.append(f"Examine deflection patterns ({metrics['deflection_count']} instances)")
        
        if metrics.get("commitments_made", 0) > 0:
            key_moments.append(f"Note successful commitments ({metrics['commitments_made']} made)")
        
        return Feedback(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            key_moments=key_moments
        )
    
    def get_summary_report(self, evaluation: Dict[str, Any]) -> str:
        """
        Generate a text summary report of an evaluation.
        
        Args:
            evaluation: Evaluation results
            
        Returns:
            Formatted text report
        """
        scores = evaluation["scores"]
        feedback = evaluation["feedback"]
        
        report = f"""
PERFORMANCE EVALUATION
=====================

Overall Score: {scores['overall']:.1f}/100

DIMENSION SCORES:
- Clarity: {scores['clarity']:.1f}/100
- Confidence: {scores['confidence']:.1f}/100
- Commitment: {scores['commitment']:.1f}/100
- Adaptability: {scores['adaptability']:.1f}/100

STRENGTHS:
"""
        for strength in feedback["strengths"]:
            report += f"  ✓ {strength}\n"
        
        report += "\nWEAKNESSES:\n"
        for weakness in feedback["weaknesses"]:
            report += f"  ✗ {weakness}\n"
        
        report += "\nRECOMMENDATIONS:\n"
        for i, rec in enumerate(feedback["recommendations"], 1):
            report += f"  {i}. {rec}\n"
        
        if feedback["key_moments"]:
            report += "\nKEY MOMENTS TO REVIEW:\n"
            for moment in feedback["key_moments"]:
                report += f"  • {moment}\n"
        
        return report.strip()

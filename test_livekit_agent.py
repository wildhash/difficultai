"""
Tests for LiveKit agent scenario validation and evaluator output.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from apps.livekit_agent.scenario_validator import (
    validate_scenario,
    get_missing_fields,
    is_scenario_complete
)
from agents.evaluator import EvaluatorAgent


class TestScenarioValidation(unittest.TestCase):
    """Test scenario validation functionality."""
    
    def test_valid_scenario(self):
        """Test validation of complete valid scenario."""
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Senior Software Engineer',
            'stakes': 'Job interview',
            'user_goal': 'Get hired',
            'difficulty': 0.6  # 0-1 scale
        }
        
        errors = validate_scenario(scenario)
        self.assertEqual(len(errors), 0, f"Valid scenario should have no errors, got: {errors}")
        self.assertTrue(is_scenario_complete(scenario))
    
    def test_valid_scenario_with_aliases(self):
        """Test validation with persona/goals aliases."""
        scenario = {
            'persona': 'ELITE_INTERVIEWER',  # Alias for persona_type
            'company': 'TechCorp',
            'role': 'Senior Software Engineer',
            'stakes': 'Job interview',
            'goals': 'Get hired',  # Alias for user_goal
            'difficulty': 0.8
        }
        
        errors = validate_scenario(scenario)
        self.assertEqual(len(errors), 0, f"Valid scenario with aliases should have no errors, got: {errors}")
        self.assertTrue(is_scenario_complete(scenario))
    
    def test_missing_required_fields(self):
        """Test validation catches missing required fields."""
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp'
            # Missing: role, stakes, user_goal, difficulty
        }
        
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        self.assertFalse(is_scenario_complete(scenario))
        
        missing = get_missing_fields(scenario)
        self.assertIn('role', missing)
        self.assertIn('stakes', missing)
    
    def test_invalid_persona_type(self):
        """Test validation catches invalid persona type."""
        scenario = {
            'persona_type': 'INVALID_PERSONA',
            'company': 'TechCorp',
            'role': 'Engineer',
            'stakes': 'Interview',
            'user_goal': 'Get hired',
            'difficulty': 0.5
        }
        
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('persona_type' in err for err in errors))
    
    def test_invalid_difficulty(self):
        """Test validation catches invalid difficulty values (0-1 scale)."""
        # Too high
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Engineer',
            'stakes': 'Interview',
            'user_goal': 'Get hired',
            'difficulty': 2.0  # > 1
        }
        
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('difficulty' in err for err in errors))
        
        # Negative
        scenario['difficulty'] = -0.1
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        
        # Non-numeric
        scenario['difficulty'] = 'medium'
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        
        # Valid values
        for valid_diff in [0.0, 0.5, 1.0, 0.75]:
            scenario['difficulty'] = valid_diff
            errors = validate_scenario(scenario)
            # Should have no difficulty-related errors (may have other errors)
            diff_errors = [e for e in errors if 'difficulty' in e]
            self.assertEqual(len(diff_errors), 0, f"Difficulty {valid_diff} should be valid")
    
    def test_get_missing_fields(self):
        """Test getting list of missing fields."""
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'difficulty': 0.6
        }
        
        missing = get_missing_fields(scenario)
        self.assertIn('company', missing)
        self.assertIn('role', missing)
        self.assertIn('stakes', missing)
        # Should not include persona_type or difficulty since they're present
        self.assertNotIn('persona_type', missing)
        self.assertNotIn('difficulty', missing)


class TestEvaluatorOutput(unittest.TestCase):
    """Test evaluator output schema and functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = EvaluatorAgent()
    
    def test_evaluator_output_schema(self):
        """Test that evaluator produces correct output schema."""
        metrics = {
            'vague_response_count': 2,
            'deflection_count': 1,
            'commitments_made': 3,
            'total_exchanges': 10,
            'current_difficulty': 0.6,  # 0-1 scale
            'scenario_difficulty': 0.6
        }
        
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Engineer',
            'difficulty': 0.6
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, scenario)
        
        # Check top-level structure
        self.assertIn('scores', evaluation)
        self.assertIn('feedback', evaluation)
        self.assertIn('metrics', evaluation)
        self.assertIn('scenario', evaluation)
        
        # Check scores structure - 6 scores in 1-10 scale
        scores = evaluation['scores']
        self.assertIn('clarity', scores)
        self.assertIn('confidence', scores)
        self.assertIn('commitment', scores)
        self.assertIn('adaptability', scores)
        self.assertIn('composure', scores)
        self.assertIn('effectiveness', scores)
        
        # Check all scores are 1-10
        for key, value in scores.items():
            self.assertGreaterEqual(value, 1.0, f"{key} score should be >= 1")
            self.assertLessEqual(value, 10.0, f"{key} score should be <= 10")
        
        # Check feedback structure - coaching_points and key_moments
        feedback = evaluation['feedback']
        self.assertIn('coaching_points', feedback)
        self.assertIn('key_moments', feedback)
        
        # Check all are lists
        self.assertIsInstance(feedback['coaching_points'], list)
        self.assertIsInstance(feedback['key_moments'], list)
        
        # Check exactly 3 coaching points
        self.assertEqual(len(feedback['coaching_points']), 3, "Should have exactly 3 coaching points")
    
    def test_evaluator_summary_report(self):
        """Test that evaluator generates summary report."""
        metrics = {
            'vague_response_count': 1,
            'deflection_count': 0,
            'commitments_made': 2,
            'total_exchanges': 5,
            'current_difficulty': 0.4,  # 0-1 scale
            'scenario_difficulty': 0.4
        }
        
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Engineer',
            'difficulty': 0.4
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, scenario)
        report = self.evaluator.get_summary_report(evaluation)
        
        # Check report contains expected sections
        self.assertIn('PERFORMANCE SCORECARD', report)
        self.assertIn('SCORES (1-10 scale)', report)
        self.assertIn('Clarity', report)
        self.assertIn('Confidence', report)
        self.assertIn('Commitment', report)
        self.assertIn('Adaptability', report)
        self.assertIn('Composure', report)
        self.assertIn('Effectiveness', report)
        self.assertIn('COACHING POINTS', report)
        self.assertIn('KEY MOMENTS', report)
        
        # Check that report has numbered coaching points (1., 2., 3.)
        self.assertIn('1.', report)
        self.assertIn('2.', report)
        self.assertIn('3.', report)
        
        # Check report is not empty
        self.assertGreater(len(report), 100)
    
    def test_evaluator_handles_edge_cases(self):
        """Test evaluator handles edge cases gracefully."""
        # Zero exchanges
        metrics = {
            'vague_response_count': 0,
            'deflection_count': 0,
            'commitments_made': 0,
            'total_exchanges': 0,
            'current_difficulty': 0.2,
            'scenario_difficulty': 0.2
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, {})
        self.assertIn('scores', evaluation)
        
        # Very high vague/deflection counts
        metrics = {
            'vague_response_count': 100,
            'deflection_count': 100,
            'commitments_made': 0,
            'total_exchanges': 100,
            'current_difficulty': 1.0,  # Maximum difficulty
            'scenario_difficulty': 0.2
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, {})
        # Scores should still be in valid range
        for score in evaluation['scores'].values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)


if __name__ == '__main__':
    unittest.main()

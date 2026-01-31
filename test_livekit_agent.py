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
            'difficulty': 3
        }
        
        errors = validate_scenario(scenario)
        self.assertEqual(len(errors), 0, f"Valid scenario should have no errors, got: {errors}")
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
        self.assertIn('user_goal', missing)
        self.assertIn('difficulty', missing)
    
    def test_invalid_persona_type(self):
        """Test validation catches invalid persona type."""
        scenario = {
            'persona_type': 'INVALID_PERSONA',
            'company': 'TechCorp',
            'role': 'Engineer',
            'stakes': 'Interview',
            'user_goal': 'Get hired',
            'difficulty': 3
        }
        
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('persona_type' in err for err in errors))
    
    def test_invalid_difficulty(self):
        """Test validation catches invalid difficulty values."""
        # Too high
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Engineer',
            'stakes': 'Interview',
            'user_goal': 'Get hired',
            'difficulty': 10
        }
        
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('difficulty' in err for err in errors))
        
        # Too low
        scenario['difficulty'] = 0
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
        
        # Non-numeric
        scenario['difficulty'] = 'medium'
        errors = validate_scenario(scenario)
        self.assertGreater(len(errors), 0)
    
    def test_get_missing_fields(self):
        """Test getting list of missing fields."""
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'difficulty': 3
        }
        
        missing = get_missing_fields(scenario)
        self.assertIn('company', missing)
        self.assertIn('role', missing)
        self.assertIn('stakes', missing)
        self.assertIn('user_goal', missing)
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
            'current_difficulty': 3,
            'scenario_difficulty': 3
        }
        
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Engineer',
            'difficulty': 3
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, scenario)
        
        # Check top-level structure
        self.assertIn('scores', evaluation)
        self.assertIn('feedback', evaluation)
        self.assertIn('metrics', evaluation)
        self.assertIn('scenario', evaluation)
        
        # Check scores structure
        scores = evaluation['scores']
        self.assertIn('clarity', scores)
        self.assertIn('confidence', scores)
        self.assertIn('commitment', scores)
        self.assertIn('adaptability', scores)
        self.assertIn('overall', scores)
        
        # Check all scores are 0-100
        for key, value in scores.items():
            self.assertGreaterEqual(value, 0.0, f"{key} score should be >= 0")
            self.assertLessEqual(value, 100.0, f"{key} score should be <= 100")
        
        # Check feedback structure
        feedback = evaluation['feedback']
        self.assertIn('strengths', feedback)
        self.assertIn('weaknesses', feedback)
        self.assertIn('recommendations', feedback)
        self.assertIn('key_moments', feedback)
        
        # Check all are lists
        self.assertIsInstance(feedback['strengths'], list)
        self.assertIsInstance(feedback['weaknesses'], list)
        self.assertIsInstance(feedback['recommendations'], list)
        self.assertIsInstance(feedback['key_moments'], list)
    
    def test_evaluator_summary_report(self):
        """Test that evaluator generates summary report."""
        metrics = {
            'vague_response_count': 1,
            'deflection_count': 0,
            'commitments_made': 2,
            'total_exchanges': 5,
            'current_difficulty': 2,
            'scenario_difficulty': 2
        }
        
        scenario = {
            'persona_type': 'ELITE_INTERVIEWER',
            'company': 'TechCorp',
            'role': 'Engineer',
            'difficulty': 2
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, scenario)
        report = self.evaluator.get_summary_report(evaluation)
        
        # Check report contains expected sections
        self.assertIn('PERFORMANCE EVALUATION', report)
        self.assertIn('Overall Score', report)
        self.assertIn('DIMENSION SCORES', report)
        self.assertIn('Clarity', report)
        self.assertIn('Confidence', report)
        self.assertIn('Commitment', report)
        self.assertIn('Adaptability', report)
        
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
            'current_difficulty': 1,
            'scenario_difficulty': 1
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, {})
        self.assertIn('scores', evaluation)
        
        # Very high vague/deflection counts
        metrics = {
            'vague_response_count': 100,
            'deflection_count': 100,
            'commitments_made': 0,
            'total_exchanges': 100,
            'current_difficulty': 5,
            'scenario_difficulty': 1
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics, {})
        # Scores should still be in valid range
        for score in evaluation['scores'].values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)


if __name__ == '__main__':
    unittest.main()

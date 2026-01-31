"""
Tests for the agent modules (architect, researcher, adversary, evaluator).
"""

import unittest
from agents import ArchitectAgent, ResearcherAgent, AdversaryAgent, EvaluatorAgent
from agents.architect import PersonaType, Scenario


class TestArchitectAgent(unittest.TestCase):
    """Test suite for Architect Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.architect = ArchitectAgent()
    
    def test_design_scenario(self):
        """Test scenario design."""
        scenario = self.architect.design_scenario(
            persona_type=PersonaType.ELITE_INTERVIEWER,
            company="TechCorp",
            role="Software Engineer",
            stakes="Job interview",
            user_goal="Get hired",
            difficulty=3
        )
        
        self.assertIsInstance(scenario, Scenario)
        self.assertEqual(scenario.company, "TechCorp")
        self.assertEqual(scenario.difficulty, 3)
    
    def test_validate_scenario(self):
        """Test scenario validation."""
        scenario = self.architect.design_scenario(
            persona_type=PersonaType.ELITE_INTERVIEWER,
            company="TechCorp",
            role="Engineer",
            stakes="Interview",
            user_goal="Get hired",
            difficulty=3
        )
        
        issues = self.architect.validate_scenario(scenario)
        self.assertEqual(len(issues), 0)
    
    def test_invalid_difficulty(self):
        """Test that invalid difficulty raises error."""
        with self.assertRaises(ValueError):
            self.architect.design_scenario(
                persona_type=PersonaType.ELITE_INTERVIEWER,
                company="TechCorp",
                role="Engineer",
                stakes="Interview",
                user_goal="Get hired",
                difficulty=6  # Invalid
            )
    
    def test_get_scenario_template(self):
        """Test getting scenario templates."""
        template = self.architect.get_scenario_template(PersonaType.ELITE_INTERVIEWER)
        
        self.assertIn("description", template)
        self.assertIn("key_behaviors", template)
        self.assertIn("success_criteria", template)


class TestResearcherAgent(unittest.TestCase):
    """Test suite for Researcher Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.researcher = ResearcherAgent()
    
    def test_research_company(self):
        """Test company research."""
        context = self.researcher.research_company("TechCorp")
        
        self.assertEqual(context.name, "TechCorp")
        self.assertIsNotNone(context.industry)
    
    def test_research_role(self):
        """Test role research."""
        context = self.researcher.research_role("Software Engineer")
        
        self.assertEqual(context.title, "Software Engineer")
        self.assertIsNotNone(context.key_skills)
        self.assertGreater(len(context.key_skills), 0)
    
    def test_generate_context_summary(self):
        """Test context summary generation."""
        company = self.researcher.research_company("TechCorp")
        role = self.researcher.research_role("Engineer")
        
        summary = self.researcher.generate_context_summary(company, role)
        
        self.assertIn("TechCorp", summary)
        self.assertIn("Engineer", summary)
    
    def test_research_caching(self):
        """Test that research results are cached."""
        context1 = self.researcher.research_company("TechCorp")
        context2 = self.researcher.research_company("TechCorp")
        
        # Should be the same object from cache
        self.assertIs(context1, context2)


class TestAdversaryAgent(unittest.TestCase):
    """Test suite for Adversary Agent."""
    
    def test_initialization_without_scenario(self):
        """Test adversary initialization without scenario."""
        from unittest.mock import patch
        
        with patch('difficult_ai.OpenAI'):
            adversary = AdversaryAgent(api_key="test")
            self.assertIsNone(adversary.scenario)
    
    def test_initialization_with_scenario(self):
        """Test adversary initialization with scenario."""
        from unittest.mock import patch
        
        scenario = {
            "persona_type": "ELITE_INTERVIEWER",
            "company": "TechCorp",
            "role": "Engineer",
            "difficulty": 3
        }
        
        with patch('difficult_ai.OpenAI'):
            adversary = AdversaryAgent(api_key="test", scenario=scenario)
            self.assertEqual(adversary.scenario, scenario)
            self.assertEqual(adversary.difficulty_level, 3)
    
    def test_set_scenario(self):
        """Test setting scenario after initialization."""
        from unittest.mock import patch
        
        scenario = {
            "persona_type": "ANGRY_CUSTOMER",
            "difficulty": 4
        }
        
        with patch('difficult_ai.OpenAI'):
            adversary = AdversaryAgent(api_key="test")
            adversary.set_scenario(scenario)
            
            self.assertEqual(adversary.scenario, scenario)
            self.assertEqual(adversary.difficulty_level, 4)
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        from unittest.mock import patch
        
        scenario = {"difficulty": 3}
        
        with patch('difficult_ai.OpenAI'):
            adversary = AdversaryAgent(api_key="test", scenario=scenario)
            adversary.vague_response_count = 2
            adversary.commitments_made = ["commitment 1"]
            
            metrics = adversary.get_performance_metrics()
            
            self.assertIn("scenario_difficulty", metrics)
            self.assertIn("conversation_quality_score", metrics)
            self.assertEqual(metrics["scenario_difficulty"], 3)


class TestEvaluatorAgent(unittest.TestCase):
    """Test suite for Evaluator Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = EvaluatorAgent()
    
    def test_evaluate_conversation(self):
        """Test conversation evaluation."""
        metrics = {
            "vague_response_count": 1,
            "deflection_count": 0,
            "commitments_made": 2,
            "total_exchanges": 5,
            "current_difficulty": 2,
            "scenario_difficulty": 2
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics)
        
        self.assertIn("scores", evaluation)
        self.assertIn("feedback", evaluation)
        self.assertIn("overall", evaluation["scores"])
    
    def test_score_calculations(self):
        """Test that scores are calculated correctly."""
        metrics = {
            "vague_response_count": 0,
            "deflection_count": 0,
            "commitments_made": 3,
            "total_exchanges": 5,
            "current_difficulty": 2,
            "scenario_difficulty": 2
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics)
        scores = evaluation["scores"]
        
        # High quality conversation should have high scores
        self.assertGreater(scores["clarity"], 80)
        self.assertGreater(scores["confidence"], 80)
        self.assertGreater(scores["overall"], 70)
    
    def test_get_summary_report(self):
        """Test summary report generation."""
        metrics = {
            "vague_response_count": 2,
            "deflection_count": 1,
            "commitments_made": 1,
            "total_exchanges": 5,
            "current_difficulty": 3,
            "scenario_difficulty": 2
        }
        
        evaluation = self.evaluator.evaluate_conversation(metrics)
        report = self.evaluator.get_summary_report(evaluation)
        
        self.assertIn("PERFORMANCE EVALUATION", report)
        self.assertIn("Overall Score", report)
        self.assertIn("STRENGTHS", report)
        self.assertIn("WEAKNESSES", report)


if __name__ == '__main__':
    unittest.main()

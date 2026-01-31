"""
Tests for the Difficult AI agent.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from difficult_ai import DifficultAI


class TestDifficultAI(unittest.TestCase):
    """Test suite for Difficult AI agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the OpenAI client to avoid API calls during testing
        self.mock_openai_patcher = patch('difficult_ai.OpenAI')
        self.mock_openai = self.mock_openai_patcher.start()
        self.agent = DifficultAI(api_key="test_key")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.mock_openai_patcher.stop()
    
    def test_initialization(self):
        """Test that the agent initializes correctly."""
        self.assertEqual(self.agent.difficulty_level, 1)
        self.assertEqual(self.agent.vague_response_count, 0)
        self.assertEqual(self.agent.deflection_count, 0)
        self.assertEqual(len(self.agent.commitments_made), 0)
        self.assertFalse(self.agent.interrupted)
    
    def test_analyze_vague_response(self):
        """Test detection of vague responses."""
        vague_message = "Maybe I'll do something about it"
        analysis = self.agent._analyze_response_quality(vague_message)
        self.assertTrue(analysis["is_vague"])
    
    def test_analyze_concrete_response(self):
        """Test detection of concrete responses."""
        concrete_message = "I will deliver 5 units by Monday at 3pm"
        analysis = self.agent._analyze_response_quality(concrete_message)
        self.assertTrue(analysis["is_concrete"])
    
    def test_analyze_deflection(self):
        """Test detection of deflecting responses."""
        deflecting_message = "Let's talk about something else first"
        analysis = self.agent._analyze_response_quality(deflecting_message)
        self.assertTrue(analysis["is_deflecting"])
    
    def test_difficulty_increases_with_vague_responses(self):
        """Test that difficulty increases when user gives vague responses."""
        initial_difficulty = self.agent.difficulty_level
        
        # Simulate vague responses
        self.agent._update_difficulty({"is_vague": True, "is_deflecting": False, "is_concrete": False})
        self.agent._update_difficulty({"is_vague": True, "is_deflecting": False, "is_concrete": False})
        
        self.assertGreater(self.agent.difficulty_level, initial_difficulty)
        self.assertEqual(self.agent.vague_response_count, 2)
    
    def test_difficulty_increases_with_deflections(self):
        """Test that difficulty increases when user deflects."""
        initial_difficulty = self.agent.difficulty_level
        
        # Simulate deflections
        self.agent._update_difficulty({"is_vague": False, "is_deflecting": True, "is_concrete": False})
        self.agent._update_difficulty({"is_vague": False, "is_deflecting": True, "is_concrete": False})
        
        self.assertGreater(self.agent.difficulty_level, initial_difficulty)
        self.assertEqual(self.agent.deflection_count, 2)
    
    def test_extract_commitments(self):
        """Test extraction of commitments from user messages."""
        message = "I will deliver the report by Friday"
        commitments = self.agent._extract_commitments(message)
        self.assertGreater(len(commitments), 0)
        self.assertTrue(any("will deliver" in c.lower() for c in commitments))
    
    def test_extract_multiple_commitments(self):
        """Test extraction of multiple commitments."""
        message = "I'll finish the project by Monday and I promise to send updates"
        commitments = self.agent._extract_commitments(message)
        self.assertGreater(len(commitments), 0)
    
    def test_stats_tracking(self):
        """Test that statistics are tracked correctly."""
        self.agent.vague_response_count = 3
        self.agent.deflection_count = 2
        self.agent.commitments_made = ["commitment 1", "commitment 2"]
        self.agent.difficulty_level = 3
        self.agent.conversation_history = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"}
        ]
        
        stats = self.agent.get_stats()
        
        self.assertEqual(stats["vague_response_count"], 3)
        self.assertEqual(stats["deflection_count"], 2)
        self.assertEqual(stats["commitments_made"], 2)
        self.assertEqual(stats["difficulty_level"], 3)
        self.assertEqual(stats["total_exchanges"], 1)
    
    def test_reset(self):
        """Test that reset clears all state."""
        # Set some state
        self.agent.vague_response_count = 5
        self.agent.deflection_count = 3
        self.agent.commitments_made = ["test"]
        self.agent.difficulty_level = 4
        self.agent.conversation_history = [{"role": "user", "content": "test"}]
        
        # Reset
        self.agent.reset()
        
        # Verify everything is reset
        self.assertEqual(self.agent.difficulty_level, 1)
        self.assertEqual(self.agent.vague_response_count, 0)
        self.assertEqual(self.agent.deflection_count, 0)
        self.assertEqual(len(self.agent.commitments_made), 0)
        self.assertEqual(len(self.agent.conversation_history), 0)
    
    def test_system_prompt_includes_difficulty_level(self):
        """Test that system prompt reflects current difficulty level."""
        self.agent.difficulty_level = 3
        prompt = self.agent._build_system_prompt()
        self.assertIn("DIFFICULTY LEVEL: 3/5", prompt)
    
    def test_system_prompt_includes_tracking_info(self):
        """Test that system prompt includes conversation tracking."""
        self.agent.vague_response_count = 2
        self.agent.deflection_count = 1
        prompt = self.agent._build_system_prompt()
        self.assertIn("Vague responses so far: 2", prompt)
        self.assertIn("Deflections so far: 1", prompt)
    
    def test_difficulty_max_is_5(self):
        """Test that difficulty doesn't exceed maximum of 5."""
        self.agent.difficulty_level = 5
        
        # Try to increase difficulty
        self.agent._update_difficulty({"is_vague": True, "is_deflecting": True, "is_concrete": False})
        
        # Should not exceed 5
        self.assertEqual(self.agent.difficulty_level, 5)
    
    def test_difficulty_min_is_1(self):
        """Test that difficulty doesn't go below minimum of 1."""
        self.agent.difficulty_level = 1
        self.agent.commitments_made = ["commitment 1", "commitment 2"]
        
        # Try to decrease difficulty
        self.agent._update_difficulty({"is_vague": False, "is_deflecting": False, "is_concrete": True})
        
        # Should not go below 1
        self.assertGreaterEqual(self.agent.difficulty_level, 1)


class TestResponseAnalysis(unittest.TestCase):
    """Test suite for response quality analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_openai_patcher = patch('difficult_ai.OpenAI')
        self.mock_openai = self.mock_openai_patcher.start()
        self.agent = DifficultAI(api_key="test_key")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.mock_openai_patcher.stop()
    
    def test_vague_indicators_detected(self):
        """Test that various vague indicators are detected."""
        vague_phrases = [
            "maybe I'll do it",
            "possibly next week",
            "probably going to happen",
            "I think so",
            "perhaps we could",
            "kind of ready",
            "sort of finished",
            "not sure about that",
            "we'll see what happens",
            "hopefully it works"
        ]
        
        for phrase in vague_phrases:
            with self.subTest(phrase=phrase):
                analysis = self.agent._analyze_response_quality(phrase)
                self.assertTrue(analysis["is_vague"], f"Failed to detect vagueness in: {phrase}")
    
    def test_deflection_indicators_detected(self):
        """Test that various deflection indicators are detected."""
        deflection_phrases = [
            "let's talk about something else",
            "what about this other issue",
            "but first we need to",
            "before we get to that",
            "can we discuss another topic"
        ]
        
        for phrase in deflection_phrases:
            with self.subTest(phrase=phrase):
                analysis = self.agent._analyze_response_quality(phrase)
                self.assertTrue(analysis["is_deflecting"], f"Failed to detect deflection in: {phrase}")
    
    def test_concrete_with_numbers(self):
        """Test that responses with numbers are considered concrete."""
        analysis = self.agent._analyze_response_quality("I will deliver 10 units")
        self.assertTrue(analysis["is_concrete"])
    
    def test_concrete_with_dates(self):
        """Test that responses with dates are considered concrete."""
        date_phrases = [
            "I'll finish by Monday",
            "We'll meet on Tuesday",
            "Delivery scheduled for Friday",
            "The deadline is March 15th"
        ]
        
        for phrase in date_phrases:
            with self.subTest(phrase=phrase):
                analysis = self.agent._analyze_response_quality(phrase)
                self.assertTrue(analysis["is_concrete"], f"Failed to detect concrete date in: {phrase}")
    
    def test_concrete_with_action_verbs(self):
        """Test that responses with action verbs are considered concrete."""
        action_phrases = [
            "I will complete the task",
            "I commit to finishing",
            "I promise to deliver",
            "I guarantee results"
        ]
        
        for phrase in action_phrases:
            with self.subTest(phrase=phrase):
                analysis = self.agent._analyze_response_quality(phrase)
                self.assertTrue(analysis["is_concrete"], f"Failed to detect concrete action in: {phrase}")


if __name__ == '__main__':
    unittest.main()

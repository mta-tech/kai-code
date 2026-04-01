"""Tests for cost tracking module."""

import unittest

from kai_code.cost_tracking import UsageSummary, CostTracker


class TestUsageSummary(unittest.TestCase):
    def test_empty_summary(self) -> None:
        """Test empty usage summary."""
        summary = UsageSummary()
        self.assertEqual(summary.input_tokens, 0)
        self.assertEqual(summary.output_tokens, 0)
        self.assertEqual(summary.turn_count, 0)
        self.assertEqual(summary.total_tokens(), 0)

    def test_add_turn_with_estimation(self) -> None:
        """Test adding turn with token estimation."""
        summary = UsageSummary()
        prompt = "Hello world this is a test"
        output = "This is the response"
        
        new_summary = summary.add_turn(prompt, output)
        
        # Estimation: split by spaces
        self.assertEqual(new_summary.input_tokens, 6)  # "Hello world this is a test"
        self.assertEqual(new_summary.output_tokens, 4)  # "This is the response"
        self.assertEqual(new_summary.turn_count, 1)
        self.assertEqual(new_summary.total_tokens(), 10)

    def test_add_turn_with_exact_counts(self) -> None:
        """Test adding turn with exact token counts."""
        summary = UsageSummary()
        prompt = "Hello world"
        output = "Hi there"
        
        new_summary = summary.add_turn(
            prompt, 
            output, 
            input_tokens=10, 
            output_tokens=5
        )
        
        self.assertEqual(new_summary.input_tokens, 10)
        self.assertEqual(new_summary.output_tokens, 5)
        self.assertEqual(new_summary.turn_count, 1)

    def test_multiple_turns(self) -> None:
        """Test accumulating multiple turns."""
        summary = UsageSummary()
        
        summary = summary.add_turn("test", "response", input_tokens=5, output_tokens=3)
        summary = summary.add_turn("another", "reply", input_tokens=4, output_tokens=2)
        summary = summary.add_turn("final", "answer", input_tokens=3, output_tokens=1)
        
        self.assertEqual(summary.input_tokens, 12)
        self.assertEqual(summary.output_tokens, 6)
        self.assertEqual(summary.turn_count, 3)
        self.assertEqual(summary.total_tokens(), 18)

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        summary = UsageSummary(input_tokens=100, output_tokens=50, turn_count=5)
        result = summary.to_dict()
        
        self.assertEqual(result["input_tokens"], 100)
        self.assertEqual(result["output_tokens"], 50)
        self.assertEqual(result["turn_count"], 5)
        self.assertEqual(result["total_tokens"], 150)

    def test_str_representation(self) -> None:
        """Test string representation."""
        summary = UsageSummary(input_tokens=1000, output_tokens=500, turn_count=10)
        s = str(summary)
        
        self.assertIn("turns=10", s)
        self.assertIn("input=1,000", s)
        self.assertIn("output=500", s)
        self.assertIn("total=1,500", s)


class TestCostTracker(unittest.TestCase):
    def test_empty_tracker(self) -> None:
        """Test empty cost tracker."""
        tracker = CostTracker()
        total = tracker.get_total()
        
        self.assertEqual(total.input_tokens, 0)
        self.assertEqual(total.output_tokens, 0)
        self.assertEqual(total.turn_count, 0)

    def test_add_session(self) -> None:
        """Test adding a session."""
        tracker = CostTracker()
        usage = UsageSummary(input_tokens=100, output_tokens=50, turn_count=3)
        
        tracker.add_session("session-1", usage)
        
        retrieved = tracker.get_session("session-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.input_tokens, 100)
        self.assertEqual(retrieved.output_tokens, 50)

    def test_merge_sessions(self) -> None:
        """Test merging sessions with same ID."""
        tracker = CostTracker()
        
        usage1 = UsageSummary(input_tokens=100, output_tokens=50, turn_count=3)
        usage2 = UsageSummary(input_tokens=50, output_tokens=25, turn_count=2)
        
        tracker.add_session("session-1", usage1)
        tracker.add_session("session-1", usage2)
        
        retrieved = tracker.get_session("session-1")
        self.assertEqual(retrieved.input_tokens, 150)
        self.assertEqual(retrieved.output_tokens, 75)
        self.assertEqual(retrieved.turn_count, 5)

    def test_get_total(self) -> None:
        """Test getting total across sessions."""
        tracker = CostTracker()
        
        usage1 = UsageSummary(input_tokens=100, output_tokens=50, turn_count=3)
        usage2 = UsageSummary(input_tokens=50, output_tokens=25, turn_count=2)
        
        tracker.add_session("session-1", usage1)
        tracker.add_session("session-2", usage2)
        
        total = tracker.get_total()
        self.assertEqual(total.input_tokens, 150)
        self.assertEqual(total.output_tokens, 75)
        self.assertEqual(total.turn_count, 5)

    def test_clear_session(self) -> None:
        """Test clearing a session."""
        tracker = CostTracker()
        usage = UsageSummary(input_tokens=100, output_tokens=50, turn_count=3)
        
        tracker.add_session("session-1", usage)
        tracker.clear_session("session-1")
        
        self.assertIsNone(tracker.get_session("session-1"))

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        tracker = CostTracker()
        usage = UsageSummary(input_tokens=100, output_tokens=50, turn_count=3)
        
        tracker.add_session("session-1", usage)
        result = tracker.to_dict()
        
        self.assertIn("sessions", result)
        self.assertIn("total", result)
        self.assertIn("session-1", result["sessions"])


if __name__ == "__main__":
    unittest.main()

"""
Tests for LoopDetectionMiddleware

Validates loop detection capabilities across 4 pattern types.
"""

import pytest
from datetime import datetime
from loop_detection import (
    LoopDetectionMiddleware,
    ToolCallRecord,
    LoopPattern
)


class TestLoopDetectionMiddleware:
    """Test suite for LoopDetectionMiddleware"""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        return LoopDetectionMiddleware(
            history_size=50,
            exact_match_threshold=3,
            semantic_similarity_threshold=0.85
        )
    
    # ========================================
    # Exact Repetition Tests
    # ========================================
    
    def test_exact_repetition_detection(self, middleware):
        """Test that exact repetition is detected"""
        tool_name = "read_file"
        arguments = {"path": "/test/file.py"}
        
        # First call should pass
        should_exec, reason = middleware.check_before_execution(tool_name, arguments)
        assert should_exec is True
        assert reason is None
        
        # Second call should pass
        should_exec, reason = middleware.check_before_execution(tool_name, arguments)
        assert should_exec is True
        
        # Third call should pass
        should_exec, reason = middleware.check_before_execution(tool_name, arguments)
        assert should_exec is True
        
        # Fourth call should be blocked (3 repetitions = loop)
        should_exec, reason = middleware.check_before_execution(tool_name, arguments)
        assert should_exec is False
        assert "Exact repetition detected" in reason
    
    def test_exact_repetition_different_tools(self, middleware):
        """Test that different tools don't trigger repetition"""
        tool1 = "read_file"
        tool2 = "write_file"
        args = {"path": "/test/file.py"}
        
        # Mix of different tools should not trigger
        for _ in range(5):
            middleware.check_before_execution(tool1, args)
            middleware.check_before_execution(tool2, args)
        
        # Both should still be allowed
        should_exec, _ = middleware.check_before_execution(tool1, args)
        assert should_exec is True
    
    def test_exact_repetition_different_args(self, middleware):
        """Test that different arguments don't trigger repetition"""
        tool_name = "read_file"
        
        # Different files should not trigger
        for i in range(10):
            should_exec, _ = middleware.check_before_execution(
                tool_name,
                {"path": f"/test/file_{i}.py"}
            )
            assert should_exec is True
    
    # ========================================
    # Semantic Similarity Tests
    # ========================================
    
    def test_semantic_similarity_detection(self, middleware):
        """Test that semantically similar calls are detected"""
        tool_name = "read_file"
        
        # Similar arguments (different path but same structure)
        similar_args = [
            {"path": "/test/file.py"},
            {"path": "/test/file_v2.py"},
            {"path": "/test/file_v3.py"},
        ]
        
        # First 3 should pass
        for args in similar_args:
            should_exec, _ = middleware.check_before_execution(tool_name, args)
            assert should_exec is True
        
        # Fourth similar call should be blocked
        should_exec, reason = middleware.check_before_execution(
            tool_name,
            {"path": "/test/file_v4.py"}
        )
        assert should_exec is False
        assert "Semantic similarity detected" in reason
    
    def test_semantic_similarity_different_structure(self, middleware):
        """Test that different argument structures don't trigger"""
        tool_name = "search"
        
        # Different argument structures
        different_args = [
            {"query": "test"},
            {"pattern": "test"},
            {"regex": "test"},
        ]
        
        for args in different_args:
            should_exec, _ = middleware.check_before_execution(tool_name, args)
            assert should_exec is True
    
    # ========================================
    # Cycle Detection Tests
    # ========================================
    
    def test_cycle_detection_simple(self, middleware):
        """Test simple A → B → A cycle detection"""
        tool_a = "read_file"
        tool_b = "write_file"
        args_a = {"path": "/test/a.py"}
        args_b = {"path": "/test/b.py"}
        
        # First cycle should pass
        middleware.check_before_execution(tool_a, args_a)
        middleware.check_before_execution(tool_b, args_b)
        
        # Second cycle should pass
        middleware.check_before_execution(tool_a, args_a)
        middleware.check_before_execution(tool_b, args_b)
        
        # Third cycle should be detected
        should_exec, reason = middleware.check_before_execution(tool_a, args_a)
        assert should_exec is False
        assert "Cycle detected" in reason
    
    def test_cycle_detection_complex(self, middleware):
        """Test complex A → B → C → A cycle detection"""
        cycle_tools = [
            ("read_config", {"file": "config.json"}),
            ("parse_config", {"format": "json"}),
            ("apply_config", {"config": "parsed"}),
        ]
        
        # First 2 cycles should pass
        for _ in range(2):
            for tool, args in cycle_tools:
                middleware.check_before_execution(tool, args)
        
        # Third cycle should be detected
        should_exec, reason = middleware.check_before_execution(
            cycle_tools[0][0],
            cycle_tools[0][1]
        )
        assert should_exec is False
        assert "Cycle detected" in reason
    
    # ========================================
    # State Mutation Tests
    # ========================================
    
    def test_state_mutation_detection(self, middleware):
        """Test state mutation loop detection"""
        tool_name = "execute_query"
        
        # Different queries but same result
        queries = [
            {"sql": "SELECT * FROM users WHERE id = 1"},
            {"sql": "SELECT * FROM users WHERE id = 2"},
            {"sql": "SELECT * FROM users WHERE id = 3"},
        ]
        
        # Execute with same result
        for args in queries:
            middleware.check_before_execution(tool_name, args)
            middleware.record_execution_result(
                tool_name,
                args,
                {"result": "empty"}  # Same result
            )
        
        # Fourth call should be blocked
        should_exec, reason = middleware.check_before_execution(
            tool_name,
            {"sql": "SELECT * FROM users WHERE id = 4"}
        )
        assert should_exec is False
        assert "State mutation loop" in reason
    
    def test_state_mutation_different_results(self, middleware):
        """Test that different results don't trigger state mutation"""
        tool_name = "execute_query"
        
        # Different queries with different results
        queries = [
            ({"sql": "SELECT 1"}, {"result": "1"}),
            ({"sql": "SELECT 2"}, {"result": "2"}),
            ({"sql": "SELECT 3"}, {"result": "3"}),
        ]
        
        for args, result in queries:
            middleware.check_before_execution(tool_name, args)
            middleware.record_execution_result(tool_name, args, result)
        
        # Should still be allowed
        should_exec, _ = middleware.check_before_execution(
            tool_name,
            {"sql": "SELECT 4"}
        )
        assert should_exec is True
    
    # ========================================
    # History Management Tests
    # ========================================
    
    def test_history_size_limit(self):
        """Test that history respects size limit"""
        middleware = LoopDetectionMiddleware(history_size=10)
        
        # Add more calls than limit
        for i in range(20):
            middleware.check_before_execution("tool", {"arg": i})
        
        # Should only keep last 10
        assert len(middleware.call_history) == 10
    
    def test_clear_history(self, middleware):
        """Test history clearing"""
        # Add some calls
        for i in range(10):
            middleware.check_before_execution("tool", {"arg": i})
        
        # Clear history
        middleware.clear_history()
        
        # Should be empty
        assert len(middleware.call_history) == 0
        assert len(middleware.detected_patterns) == 0
    
    def test_get_statistics(self, middleware):
        """Test statistics collection"""
        # Add various calls
        middleware.check_before_execution("tool_a", {"arg": 1})
        middleware.check_before_execution("tool_b", {"arg": 2})
        middleware.check_before_execution("tool_a", {"arg": 3})
        middleware.check_before_execution("tool_a", {"arg": 4})
        
        stats = middleware.get_statistics()
        
        assert stats["total_calls"] == 4
        assert stats["unique_tools"] == 2
        assert len(stats["most_repeated_tools"]) > 0
    
    # ========================================
    # Edge Cases
    # ========================================
    
    def test_empty_history(self, middleware):
        """Test behavior with empty history"""
        should_exec, reason = middleware.check_before_execution("tool", {"arg": 1})
        
        assert should_exec is True
        assert reason is None
    
    def test_single_tool_repeated(self, middleware):
        """Test single tool repeated many times"""
        tool_name = "check_status"
        args = {"target": "system"}
        
        # Should trigger after threshold
        for i in range(middleware.exact_match_threshold + 1):
            should_exec, reason = middleware.check_before_execution(tool_name, args)
            
            if i < middleware.exact_match_threshold:
                assert should_exec is True
            else:
                assert should_exec is False
    
    def test_concurrent_tools_no_loop(self, middleware):
        """Test that concurrent different tools don't create false positive"""
        tools = ["read", "process", "write", "verify"]
        
        for _ in range(10):
            for tool in tools:
                should_exec, _ = middleware.check_before_execution(
                    tool,
                    {"data": "test"}
                )
                assert should_exec is True
    
    def test_similar_arguments_calculation(self, middleware):
        """Test argument similarity calculation"""
        args1 = {"path": "/test/file.py", "mode": "read"}
        args2 = {"path": "/test/file_v2.py", "mode": "read"}
        args3 = {"path": "/completely/different.txt", "mode": "write"}
        
        # Similar args should have high similarity
        similarity_high = middleware._calculate_similarity(args1, args2)
        assert similarity_high > 0.7
        
        # Different args should have low similarity
        similarity_low = middleware._calculate_similarity(args1, args3)
        assert similarity_low < 0.5
    
    def test_nested_dict_similarity(self, middleware):
        """Test similarity with nested dictionaries"""
        args1 = {
            "config": {
                "input": "/data/input.csv",
                "output": "/data/output.csv"
            }
        }
        args2 = {
            "config": {
                "input": "/data/input_v2.csv",
                "output": "/data/output_v2.csv"
            }
        }
        
        similarity = middleware._calculate_similarity(args1, args2)
        assert similarity > 0.5
    
    # ========================================
    # Integration Tests
    # ========================================
    
    def test_full_workflow(self, middleware):
        """Test complete workflow with mixed patterns"""
        # Normal execution
        should_exec, _ = middleware.check_before_execution("init", {"config": "default"})
        assert should_exec is True
        
        # Different tools
        should_exec, _ = middleware.check_before_execution("load", {"file": "data.csv"})
        assert should_exec is True
        
        should_exec, _ = middleware.check_before_execution("process", {"operation": "clean"})
        assert should_exec is True
        
        # Repeat same tool (should eventually trigger)
        for i in range(middleware.exact_match_threshold + 1):
            should_exec, _ = middleware.check_before_execution("check", {"status": "ready"})
        
        # Should be blocked by now
        assert should_exec is False
    
    def test_result_recording(self, middleware):
        """Test that results are recorded correctly"""
        tool = "query"
        args = {"sql": "SELECT 1"}
        result = {"rows": 5}
        
        middleware.check_before_execution(tool, args)
        middleware.record_execution_result(tool, args, result)
        
        # Check result hash was recorded
        assert middleware.call_history[-1].result_hash is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

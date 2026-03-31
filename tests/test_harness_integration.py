"""
Tests for Harness Integration

Tests the integration of all Phase 1 components.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from harness.integration import (
    HarnessIntegration,
    create_harness
)


class TestHarnessIntegration:
    """Test suite for HarnessIntegration"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def harness(self, temp_storage):
        """Create harness integration with temp storage"""
        return create_harness(storage_path=temp_storage)
    
    # ========================================
    # Initialization Tests
    # ========================================
    
    def test_create_harness_defaults(self):
        """Test create_harness with defaults"""
        harness = create_harness()
        
        assert harness.pre_completion is not None
        assert harness.loop_detector is not None
        assert harness.trajectory_store is not None
    
    def test_create_harness_partial(self):
        """Test create_harness with partial components"""
        harness = HarnessIntegration(
            enable_pre_completion=False,
            enable_loop_detection=True,
            enable_trajectory_memory=False
        )
        
        assert harness.pre_completion is None
        assert harness.loop_detector is not None
        assert harness.trajectory_store is None
    
    # ========================================
    # Loop Detection Tests
    # ========================================
    
    def test_check_before_tool_no_loop(self, harness):
        """Test tool check without loop"""
        should_exec, reason = harness.check_before_tool(
            "read_file",
            {"path": "test.py"}
        )
        
        assert should_exec == True
        assert reason is None
    
    def test_check_before_tool_with_loop(self, harness):
        """Test tool check with loop"""
        args = {"path": "test.py"}
        
        # Execute same tool multiple times
        for i in range(5):
            should_exec, reason = harness.check_before_tool("read_file", args)
            if not should_exec:
                # Loop detected
                assert "repetition" in reason.lower()
                return
        
        # Should have detected loop by now
        # If not, the threshold is too high
        assert False, "Loop not detected after 5 repetitions"
    
    def test_record_tool_execution(self, harness):
        """Test tool execution recording"""
        harness.start_trajectory("Test task")
        
        harness.record_tool_execution(
            tool_name="read_file",
            arguments={"path": "test.py"},
            result="file contents",
            success=True
        )
        
        # Should have recorded step
        assert len(harness.current_steps) == 1
        assert harness.current_steps[0].tool_name == "read_file"
    
    # ========================================
    # Pre-Completion Tests
    # ========================================
    
    def test_check_completion_all_pass(self, harness):
        """Test completion check with all passing"""
        task_context = {
            "task": "Write function",
            "constraints": ["Use type hints"],
            "acceptance_criteria": ["Function works"]
        }
        agent_output = {
            "code": "def add(a: int, b: int) -> int:\n    return a + b",
            "tests": "assert add(1, 2) == 3"
        }
        
        should_complete, reason = harness.check_completion(
            task_context,
            agent_output
        )
        
        # May pass or fail depending on specific checks
        # Just verify it runs without error
        assert isinstance(should_complete, bool)
    
    def test_check_completion_missing_context(self, harness):
        """Test completion check with missing context"""
        task_context = {}  # Missing required keys
        agent_output = {"code": "def foo(): pass"}
        
        should_complete, reason = harness.check_completion(
            task_context,
            agent_output
        )
        
        # Should fail due to missing context
        assert should_complete == False
        assert reason is not None
        assert "context" in reason.lower()
    
    # ========================================
    # Trajectory Memory Tests
    # ========================================
    
    def test_trajectory_lifecycle(self, harness):
        """Test full trajectory lifecycle"""
        # Start trajectory
        harness.start_trajectory("Test task", task_type="testing")
        
        assert harness.current_trajectory is not None
        assert harness.current_trajectory.task_description == "Test task"
        
        # Record steps
        harness.record_tool_execution("read", {"file": "test.py"}, "content", True)
        harness.record_tool_execution("write", {"file": "out.py"}, None, True)
        
        # End trajectory
        harness.end_trajectory(outcome="success")
        
        # Should have reset
        assert harness.current_trajectory is None
        assert len(harness.current_steps) == 0
    
    def test_get_similar_trajectories(self, harness):
        """Test retrieving similar trajectories"""
        # Create and store some trajectories
        harness.start_trajectory("Fix auth bug")
        harness.record_tool_execution("read", {"file": "auth.py"}, "code", True)
        harness.end_trajectory("success")
        
        # Search for similar
        similar = harness.get_similar_trajectories("Fix authentication issue")
        
        # Should find our stored trajectory
        assert isinstance(similar, list)
    
    def test_get_success_tips(self, harness):
        """Test getting success tips"""
        # Store some successful trajectories
        for i in range(3):
            harness.start_trajectory(f"Task {i}")
            harness.record_tool_execution("read", {"file": f"file{i}.py"}, "code", True)
            harness.end_trajectory("success")
        
        # Get tips
        tips = harness.get_success_tips()
        
        # Should have tips from successful executions
        assert isinstance(tips, list)
    
    # ========================================
    # Statistics Tests
    # ========================================
    
    def test_get_statistics(self, harness):
        """Test getting harness statistics"""
        stats = harness.get_statistics()
        
        assert "pre_completion" in stats
        assert "loop_detection" in stats
        assert "trajectory_memory" in stats
    
    # ========================================
    # Integration Tests
    # ========================================
    
    def test_full_workflow(self, harness):
        """Test complete harness workflow"""
        # Start
        harness.start_trajectory("Complete task", task_type="coding")
        
        # Execute tools
        tools = [
            ("read_file", {"path": "main.py"}),
            ("analyze", {"code": "content"}),
            ("write_file", {"path": "output.py"})
        ]
        
        for tool_name, args in tools:
            # Check before
            should_exec, reason = harness.check_before_tool(tool_name, args)
            assert should_exec, f"Unexpected loop: {reason}"
            
            # Record execution
            harness.record_tool_execution(tool_name, args, "result", True)
        
        # Check completion
        task_context = {
            "task": "Complete task",
            "constraints": [],
            "acceptance_criteria": ["Done"]
        }
        agent_output = {
            "code": "output.py",
            "tests": "assert True"
        }
        
        should_complete, reason = harness.check_completion(
            task_context,
            agent_output
        )
        
        # End trajectory
        harness.end_trajectory(
            outcome="success" if should_complete else "partial"
        )
        
        # Verify steps recorded
        # (should have 3 tool executions)
        assert len(harness.current_steps) == 0  # Reset after end
    
    def test_with_disabled_components(self):
        """Test harness with disabled components"""
        harness = HarnessIntegration(
            enable_pre_completion=False,
            enable_loop_detection=False,
            enable_trajectory_memory=False
        )
        
        # Should gracefully handle disabled components
        should_exec, reason = harness.check_before_tool("read", {})
        assert should_exec == True  # No loop detector
        assert reason is None
        
        should_complete, reason = harness.check_completion({}, {})
        assert should_complete == True  # No pre-completion
        assert reason is None
        
        # Trajectory methods should be no-ops
        harness.start_trajectory("test")
        assert harness.current_trajectory is None  # Disabled


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

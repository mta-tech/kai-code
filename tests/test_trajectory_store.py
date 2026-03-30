"""
Tests for TrajectoryMemoryStore

Validates trajectory storage, retrieval, and pattern extraction.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from trajectory_store import (
    TrajectoryMemoryStore,
    Trajectory,
    ExecutionStep
)


class TestTrajectoryMemoryStore:
    """Test suite for TrajectoryMemoryStore"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def store(self, temp_storage):
        """Create store with temporary storage"""
        return TrajectoryMemoryStore(storage_path=temp_storage)
    
    @pytest.fixture
    def sample_trajectory(self):
        """Create sample trajectory for testing"""
        steps = [
            ExecutionStep(
                step_number=1,
                tool_name="read_file",
                arguments={"path": "/test/input.py"},
                result="content",
                success=True
            ),
            ExecutionStep(
                step_number=2,
                tool_name="analyze_code",
                arguments={"code": "content"},
                result={"issues": []},
                success=True
            ),
            ExecutionStep(
                step_number=3,
                tool_name="write_file",
                arguments={"path": "/test/output.py"},
                result=None,
                success=True
            )
        ]
        
        return Trajectory(
            trajectory_id="test-001",
            task_description="Fix authentication bug in login.py",
            task_type="debugging",
            steps=steps,
            final_outcome="success",
            total_duration_ms=1500.0,
            tags=["auth", "bug"],
            metadata={"priority": "high"}
        )
    
    # ========================================
    # Storage Tests
    # ========================================
    
    def test_store_trajectory(self, store, sample_trajectory):
        """Test storing a trajectory"""
        trajectory_id = store.store(sample_trajectory)
        
        assert trajectory_id == "test-001"
        assert "test-001" in store.trajectories
    
    def test_store_multiple_trajectories(self, store):
        """Test storing multiple trajectories"""
        for i in range(5):
            trajectory = Trajectory(
                trajectory_id=f"test-{i:03d}",
                task_description=f"Task {i}",
                task_type="coding",
                steps=[],
                final_outcome="success",
                total_duration_ms=1000.0
            )
            store.store(trajectory)
        
        assert len(store.trajectories) == 5
    
    def test_persist_to_disk(self, temp_storage):
        """Test that trajectories are persisted to disk"""
        store = TrajectoryMemoryStore(storage_path=temp_storage)
        
        trajectory = Trajectory(
            trajectory_id="persist-test",
            task_description="Test persistence",
            task_type="testing",
            steps=[],
            final_outcome="success",
            total_duration_ms=500.0
        )
        
        store.store(trajectory)
        
        # Check file exists
        file_path = Path(temp_storage) / "persist-test.json"
        assert file_path.exists()
    
    def test_load_from_disk(self, temp_storage, sample_trajectory):
        """Test loading trajectories from disk"""
        # Store trajectory
        store1 = TrajectoryMemoryStore(storage_path=temp_storage)
        store1.store(sample_trajectory)
        
        # Create new store (should load from disk)
        store2 = TrajectoryMemoryStore(storage_path=temp_storage)
        
        assert len(store2.trajectories) == 1
        assert "test-001" in store2.trajectories
    
    # ========================================
    # Retrieval Tests
    # ========================================
    
    def test_retrieve_similar_by_description(self, store, sample_trajectory):
        """Test retrieving similar trajectories by description"""
        store.store(sample_trajectory)
        
        # Add more trajectories
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=f"test-{i+2:03d}",
                task_description="Implement new feature",
                task_type="coding",
                steps=[],
                final_outcome="success",
                total_duration_ms=1000.0
            )
            store.store(trajectory)
        
        # Search for similar
        similar = store.retrieve_similar(
            task_description="Fix authentication issue",
            limit=3
        )
        
        assert len(similar) > 0
        # Most similar should be the auth bug one
        assert similar[0].trajectory_id == "test-001"
    
    def test_retrieve_similar_by_type(self, store, sample_trajectory):
        """Test retrieving trajectories filtered by type"""
        store.store(sample_trajectory)
        
        # Add different type
        other_trajectory = Trajectory(
            trajectory_id="test-002",
            task_description="Write unit tests",
            task_type="testing",
            steps=[],
            final_outcome="success",
            total_duration_ms=500.0
        )
        store.store(other_trajectory)
        
        # Filter by type
        debugging_only = store.retrieve_similar(
            task_description="Fix bug",
            task_type="debugging"
        )
        
        assert len(debugging_only) == 1
        assert debugging_only[0].task_type == "debugging"
    
    def test_retrieve_similar_by_outcome(self, store):
        """Test retrieving trajectories filtered by outcome"""
        # Store success and failure
        for i, outcome in enumerate(["success", "failure", "partial"]):
            trajectory = Trajectory(
                trajectory_id=f"test-{i:03d}",
                task_description=f"Task {i}",
                task_type="coding",
                steps=[],
                final_outcome=outcome,
                total_duration_ms=1000.0
            )
            store.store(trajectory)
        
        # Get only successes
        successes = store.retrieve_similar(
            task_description="Task",
            outcome="success"
        )
        
        assert len(successes) == 1
        assert successes[0].final_outcome == "success"
    
    def test_retrieve_limit(self, store):
        """Test that retrieval respects limit"""
        for i in range(10):
            trajectory = Trajectory(
                trajectory_id=f"test-{i:03d}",
                task_description="Similar task",
                task_type="coding",
                steps=[],
                final_outcome="success",
                total_duration_ms=1000.0
            )
            store.store(trajectory)
        
        similar = store.retrieve_similar(
            task_description="Similar task",
            limit=3
        )
        
        assert len(similar) == 3
    
    # ========================================
    # Success Tips Tests
    # ========================================
    
    def test_get_success_tips(self, store):
        """Test extracting success tips"""
        # Create successful trajectory with patterns
        steps = [
            ExecutionStep(
                step_number=1,
                tool_name="read_file",
                arguments={"path": "test.py"},
                success=True
            ),
            ExecutionStep(
                step_number=2,
                tool_name="analyze",
                arguments={"code": "content"},
                success=True
            )
        ]
        
        trajectory = Trajectory(
            trajectory_id="success-001",
            task_description="Successful task",
            task_type="coding",
            steps=steps,
            final_outcome="success",
            total_duration_ms=1000.0
        )
        
        store.store(trajectory)
        
        tips = store.get_success_tips()
        
        assert len(tips) > 0
        assert any(tip["tool"] == "read_file" for tip in tips)
    
    def test_get_success_tips_by_type(self, store):
        """Test extracting success tips filtered by task type"""
        # Add different types
        for task_type in ["coding", "debugging"]:
            trajectory = Trajectory(
                trajectory_id=f"tip-{task_type}",
                task_description=f"Task {task_type}",
                task_type=task_type,
                steps=[
                    ExecutionStep(
                        step_number=1,
                        tool_name=f"tool_{task_type}",
                        arguments={},
                        success=True
                    )
                ],
                final_outcome="success",
                total_duration_ms=1000.0
            )
            store.store(trajectory)
        
        coding_tips = store.get_success_tips(task_type="coding")
        
        assert len(coding_tips) > 0
        assert all(tip["task_type"] == "coding" for tip in coding_tips)
    
    def test_tip_frequency_aggregation(self, store):
        """Test that tips are aggregated by frequency"""
        # Store multiple trajectories with same tool
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=f"freq-{i:03d}",
                task_description="Task",
                task_type="coding",
                steps=[
                    ExecutionStep(
                        step_number=1,
                        tool_name="common_tool",
                        arguments={"arg": "value"},
                        success=True
                    )
                ],
                final_outcome="success",
                total_duration_ms=1000.0
            )
            store.store(trajectory)
        
        tips = store.get_success_tips()
        
        # Common tool should have frequency > 1
        common_tip = next(
            (tip for tip in tips if tip["tool"] == "common_tool"),
            None
        )
        
        assert common_tip is not None
        assert common_tip["frequency"] >= 3
    
    # ========================================
    # Failure Patterns Tests
    # ========================================
    
    def test_get_failure_patterns(self, store):
        """Test extracting failure patterns"""
        steps = [
            ExecutionStep(
                step_number=1,
                tool_name="read_file",
                arguments={"path": "test.py"},
                success=True
            ),
            ExecutionStep(
                step_number=2,
                tool_name="broken_tool",
                arguments={},
                success=False
            )
        ]
        
        trajectory = Trajectory(
            trajectory_id="fail-001",
            task_description="Failed task",
            task_type="debugging",
            steps=steps,
            final_outcome="failure",
            total_duration_ms=1000.0
        )
        
        store.store(trajectory)
        
        patterns = store.get_failure_patterns()
        
        assert len(patterns) > 0
        assert patterns[0]["final_outcome"] == "failure"
    
    def test_failure_pattern_includes_sequence(self, store):
        """Test that failure patterns include tool sequence"""
        steps = [
            ExecutionStep(step_number=1, tool_name="tool_a", arguments={}, success=True),
            ExecutionStep(step_number=2, tool_name="tool_b", arguments={}, success=True),
            ExecutionStep(step_number=3, tool_name="tool_c", arguments={}, success=False)
        ]
        
        trajectory = Trajectory(
            trajectory_id="fail-seq",
            task_description="Failed with sequence",
            task_type="coding",
            steps=steps,
            final_outcome="failure",
            total_duration_ms=1000.0
        )
        
        store.store(trajectory)
        
        patterns = store.get_failure_patterns()
        
        assert len(patterns[0]["tool_sequence"]) > 0
        assert patterns[0]["failure_step"] == "tool_c"
    
    # ========================================
    # Statistics Tests
    # ========================================
    
    def test_statistics_empty_store(self, store):
        """Test statistics with empty store"""
        stats = store.get_statistics()
        
        assert stats["total_trajectories"] == 0
        assert stats["by_type"] == {}
        assert stats["by_outcome"] == {}
    
    def test_statistics_with_data(self, store):
        """Test statistics with trajectories"""
        # Add trajectories with different types and outcomes
        for task_type in ["coding", "debugging", "coding"]:
            for outcome in ["success", "failure"]:
                trajectory = Trajectory(
                    trajectory_id=f"stat-{task_type}-{outcome}",
                    task_description="Task",
                    task_type=task_type,
                    steps=[],
                    final_outcome=outcome,
                    total_duration_ms=1000.0
                )
                store.store(trajectory)
        
        stats = store.get_statistics()
        
        assert stats["total_trajectories"] == 6
        assert stats["by_type"]["coding"] == 4
        assert stats["by_type"]["debugging"] == 2
        assert stats["success_rate"] > 0
    
    # ========================================
    # ExecutionStep Tests
    # ========================================
    
    def test_execution_step_serialization(self):
        """Test ExecutionStep serialization"""
        step = ExecutionStep(
            step_number=1,
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="output",
            success=True,
            duration_ms=100.0
        )
        
        data = step.to_dict()
        restored = ExecutionStep.from_dict(data)
        
        assert restored.step_number == step.step_number
        assert restored.tool_name == step.tool_name
        assert restored.arguments == step.arguments
        assert restored.success == step.success
    
    def test_trajectory_serialization(self, sample_trajectory):
        """Test Trajectory serialization"""
        data = sample_trajectory.to_dict()
        restored = Trajectory.from_dict(data)
        
        assert restored.trajectory_id == sample_trajectory.trajectory_id
        assert restored.task_description == sample_trajectory.task_description
        assert len(restored.steps) == len(sample_trajectory.steps)
    
    # ========================================
    # Utility Methods Tests
    # ========================================
    
    def test_get_tool_sequence(self, sample_trajectory):
        """Test getting tool sequence from trajectory"""
        sequence = sample_trajectory.get_tool_sequence()
        
        assert len(sequence) == 3
        assert sequence[0] == "read_file"
        assert sequence[1] == "analyze_code"
        assert sequence[2] == "write_file"
    
    def test_get_success_patterns(self, sample_trajectory):
        """Test getting success patterns from trajectory"""
        patterns = sample_trajectory.get_success_patterns()
        
        assert len(patterns) == 3
        assert all(isinstance(p, tuple) and len(p) == 2 for p in patterns)
    
    def test_similarity_calculation(self, store):
        """Test text similarity calculation"""
        text1 = "fix authentication bug in login"
        text2 = "fix authentication issue in login"
        text3 = "implement new feature for dashboard"
        
        # Similar texts should have high score
        score_high = store._calculate_similarity(text1, text2)
        assert score_high > 0.7
        
        # Different texts should have low score
        score_low = store._calculate_similarity(text1, text3)
        assert score_low < 0.5
    
    def test_clear_store(self, store, sample_trajectory):
        """Test clearing the store"""
        store.store(sample_trajectory)
        
        assert len(store.trajectories) > 0
        
        store.clear()
        
        assert len(store.trajectories) == 0
        assert len(store.index_by_task_type) == 0
        assert len(store.index_by_outcome) == 0
    
    # ========================================
    # Edge Cases
    # ========================================
    
    def test_empty_steps_trajectory(self, store):
        """Test handling trajectory with no steps"""
        trajectory = Trajectory(
            trajectory_id="empty",
            task_description="Empty trajectory",
            task_type="testing",
            steps=[],
            final_outcome="success",
            total_duration_ms=0.0
        )
        
        store.store(trajectory)
        
        assert "empty" in store.trajectories
    
    def test_retrieve_from_empty_store(self, store):
        """Test retrieving from empty store"""
        similar = store.retrieve_similar("any task")
        
        assert len(similar) == 0
    
    def test_get_tips_from_empty_store(self, store):
        """Test getting tips from empty store"""
        tips = store.get_success_tips()
        
        assert len(tips) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

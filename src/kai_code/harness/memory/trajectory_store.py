"""
TrajectoryMemoryStore

Stores execution trajectories and enables retrieval of similar past executions
to guide future behavior.

Research Source: arXiv:2603.10600 (Trajectory-Informed Memory Generation)
Impact: +14% accuracy improvement
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
from pathlib import Path
from collections import defaultdict


@dataclass
class ExecutionStep:
    """Single step in an execution trajectory"""
    step_number: int
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "step_number": self.step_number,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionStep':
        """Create from dictionary"""
        return cls(
            step_number=data["step_number"],
            tool_name=data["tool_name"],
            arguments=data["arguments"],
            result=data.get("result"),
            success=data.get("success", True),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_ms=data.get("duration_ms")
        )


@dataclass
class Trajectory:
    """Complete execution trajectory"""
    trajectory_id: str
    task_description: str
    task_type: str
    steps: List[ExecutionStep]
    final_outcome: str  # 'success', 'failure', 'partial'
    total_duration_ms: float
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "trajectory_id": self.trajectory_id,
            "task_description": self.task_description,
            "task_type": self.task_type,
            "steps": [step.to_dict() for step in self.steps],
            "final_outcome": self.final_outcome,
            "total_duration_ms": self.total_duration_ms,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trajectory':
        """Create from dictionary"""
        return cls(
            trajectory_id=data["trajectory_id"],
            task_description=data["task_description"],
            task_type=data["task_type"],
            steps=[ExecutionStep.from_dict(s) for s in data["steps"]],
            final_outcome=data["final_outcome"],
            total_duration_ms=data["total_duration_ms"],
            created_at=datetime.fromisoformat(data["created_at"]),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
    
    def get_tool_sequence(self) -> List[str]:
        """Get sequence of tool names"""
        return [step.tool_name for step in self.steps]
    
    def get_success_patterns(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get successful tool + argument patterns"""
        return [
            (step.tool_name, step.arguments)
            for step in self.steps
            if step.success
        ]


class TrajectoryMemoryStore:
    """
    Stores and retrieves execution trajectories to guide agent behavior.
    
    Research-Backed Patterns:
    - Store successful execution paths
    - Retrieve similar past executions
    - Extract tips and patterns from successes
    - Learn from failures (avoid repeated mistakes)
    
    Expected Impact:
    - +14% accuracy improvement
    - Faster convergence on correct solutions
    - Reduced trial-and-error
    
    Usage:
        store = TrajectoryMemoryStore()
        
        # Store a trajectory
        store.store(trajectory)
        
        # Retrieve similar past executions
        similar = store.retrieve_similar(
            task_description="Fix authentication bug",
            task_type="debugging",
            limit=5
        )
        
        # Get tips from successful executions
        tips = store.get_success_tips(task_type="coding")
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize trajectory memory store.
        
        Args:
            storage_path: Path to persist trajectories (optional)
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.trajectories: Dict[str, Trajectory] = {}
        self.index_by_task_type: Dict[str, List[str]] = defaultdict(list)
        self.index_by_outcome: Dict[str, List[str]] = defaultdict(list)
        
        # Load existing trajectories if storage path exists
        if self.storage_path and self.storage_path.exists():
            self._load_from_disk()
    
    def store(self, trajectory: Trajectory) -> str:
        """
        Store a trajectory.
        
        Args:
            trajectory: Trajectory to store
            
        Returns:
            Trajectory ID
        """
        # Store trajectory
        self.trajectories[trajectory.trajectory_id] = trajectory
        
        # Update indices
        self.index_by_task_type[trajectory.task_type].append(
            trajectory.trajectory_id
        )
        self.index_by_outcome[trajectory.final_outcome].append(
            trajectory.trajectory_id
        )
        
        # Persist to disk if enabled
        if self.storage_path:
            self._save_to_disk(trajectory)
        
        return trajectory.trajectory_id
    
    def retrieve_similar(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 5
    ) -> List[Trajectory]:
        """
        Retrieve similar trajectories based on task description.
        
        Args:
            task_description: Description of current task
            task_type: Optional filter by task type
            outcome: Optional filter by outcome ('success', 'failure', 'partial')
            limit: Maximum number of trajectories to return
            
        Returns:
            List of similar trajectories, sorted by similarity
        """
        candidates = []
        
        # Filter by task type
        if task_type:
            candidate_ids = self.index_by_task_type.get(task_type, [])
            candidates = [
                self.trajectories[tid]
                for tid in candidate_ids
                if tid in self.trajectories
            ]
        else:
            candidates = list(self.trajectories.values())
        
        # Filter by outcome
        if outcome:
            candidates = [
                t for t in candidates
                if t.final_outcome == outcome
            ]
        
        # Calculate similarity scores
        scored = [
            (t, self._calculate_similarity(task_description, t.task_description))
            for t in candidates
        ]
        
        # Sort by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        return [t for t, score in scored[:limit]]
    
    def get_success_tips(
        self,
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get tips extracted from successful executions.
        
        Args:
            task_type: Optional filter by task type
            limit: Maximum number of tips
            
        Returns:
            List of tips with metadata
        """
        # Get successful trajectories
        success_ids = self.index_by_outcome.get("success", [])
        
        trajectories = [
            self.trajectories[tid]
            for tid in success_ids
            if tid in self.trajectories
        ]
        
        # Filter by task type
        if task_type:
            trajectories = [
                t for t in trajectories
                if t.task_type == task_type
            ]
        
        # Extract patterns
        tips = []
        for trajectory in trajectories[:limit * 2]:  # Get more to filter
            patterns = trajectory.get_success_patterns()
            
            for tool_name, args in patterns:
                tip = {
                    "tool": tool_name,
                    "arguments": args,
                    "task_type": trajectory.task_type,
                    "trajectory_id": trajectory.trajectory_id,
                    "frequency": 1
                }
                tips.append(tip)
        
        # Aggregate similar tips
        aggregated = self._aggregate_tips(tips)
        
        # Sort by frequency and return top
        aggregated.sort(key=lambda x: x["frequency"], reverse=True)
        
        return aggregated[:limit]
    
    def get_failure_patterns(
        self,
        task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get patterns from failed executions (to avoid).
        
        Args:
            task_type: Optional filter by task type
            limit: Maximum number of patterns
            
        Returns:
            List of failure patterns
        """
        # Get failed trajectories
        failure_ids = self.index_by_outcome.get("failure", [])
        
        trajectories = [
            self.trajectories[tid]
            for tid in failure_ids
            if tid in self.trajectories
        ]
        
        # Filter by task type
        if task_type:
            trajectories = [
                t for t in trajectories
                if t.task_type == task_type
            ]
        
        # Extract failure patterns
        patterns = []
        for trajectory in trajectories[:limit]:
            # Get last few steps before failure
            last_steps = trajectory.steps[-3:] if len(trajectory.steps) >= 3 else trajectory.steps
            
            pattern = {
                "task_description": trajectory.task_description,
                "tool_sequence": [s.tool_name for s in last_steps],
                "failure_step": trajectory.steps[-1].tool_name if trajectory.steps else None,
                "trajectory_id": trajectory.trajectory_id
            }
            patterns.append(pattern)
        
        return patterns[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        total = len(self.trajectories)
        
        if total == 0:
            return {
                "total_trajectories": 0,
                "by_type": {},
                "by_outcome": {}
            }
        
        # Count by type
        by_type = {
            task_type: len(ids)
            for task_type, ids in self.index_by_task_type.items()
        }
        
        # Count by outcome
        by_outcome = {
            outcome: len(ids)
            for outcome, ids in self.index_by_outcome.items()
        }
        
        # Success rate
        success_count = len(self.index_by_outcome.get("success", []))
        success_rate = success_count / total if total > 0 else 0
        
        return {
            "total_trajectories": total,
            "by_type": by_type,
            "by_outcome": by_outcome,
            "success_rate": success_rate,
            "storage_path": str(self.storage_path) if self.storage_path else None
        }
    
    # Internal Methods
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Simple implementation using word overlap.
        Can be enhanced with embeddings.
        """
        # Tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _aggregate_tips(
        self,
        tips: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Aggregate similar tips and count frequencies"""
        aggregated = {}
        
        for tip in tips:
            # Create key from tool + argument structure
            key = self._create_tip_key(tip)
            
            if key in aggregated:
                aggregated[key]["frequency"] += 1
            else:
                aggregated[key] = tip.copy()
                aggregated[key]["frequency"] = 1
        
        return list(aggregated.values())
    
    def _create_tip_key(self, tip: Dict[str, Any]) -> str:
        """Create a key for tip aggregation"""
        tool = tip["tool"]
        args = tip["arguments"]
        
        # Create deterministic key
        arg_keys = sorted(args.keys())
        key_parts = [tool] + arg_keys
        
        return "|".join(key_parts)
    
    def _save_to_disk(self, trajectory: Trajectory):
        """Save trajectory to disk"""
        if not self.storage_path:
            return
        
        # Create directory if needed
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        file_path = self.storage_path / f"{trajectory.trajectory_id}.json"
        
        with open(file_path, 'w') as f:
            json.dump(trajectory.to_dict(), f, indent=2)
    
    def _load_from_disk(self):
        """Load trajectories from disk"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    trajectory = Trajectory.from_dict(data)
                    self.trajectories[trajectory.trajectory_id] = trajectory
                    
                    # Rebuild indices
                    self.index_by_task_type[trajectory.task_type].append(
                        trajectory.trajectory_id
                    )
                    self.index_by_outcome[trajectory.final_outcome].append(
                        trajectory.trajectory_id
                    )
            except Exception as e:
                # Skip corrupted files
                print(f"Warning: Could not load trajectory from {file_path}: {e}")
    
    def clear(self):
        """Clear all trajectories"""
        self.trajectories.clear()
        self.index_by_task_type.clear()
        self.index_by_outcome.clear()

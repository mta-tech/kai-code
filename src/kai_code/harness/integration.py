"""
KaiAgent Harness Integration

Wires Phase 1 harness components into KaiAgent.

Integration Points:
1. PreCompletionChecklistMiddleware - Before task completion
2. LoopDetectionMiddleware - Tool execution wrapper
3. TrajectoryMemoryStore - Run lifecycle tracking
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import time

from .middleware import (
    PreCompletionChecklistMiddleware,
    LoopDetectionMiddleware,
    CheckResult
)
from .memory import TrajectoryMemoryStore, Trajectory, ExecutionStep


class HarnessIntegration:
    """
    Integrates harness engineering middleware into KaiAgent.
    
    Usage:
        harness = HarnessIntegration()
        
        # In KaiAgent.__init__
        self.harness = harness
        
        # Before tool execution
        should_exec, reason = harness.check_before_tool(tool_name, args)
        
        # After tool execution
        harness.record_tool_execution(tool_name, args, result)
        
        # Before task completion
        passed = harness.check_completion(task_context, output)
        
        # At run start/end
        harness.start_trajectory(task)
        harness.end_trajectory(outcome)
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        enable_pre_completion: bool = True,
        enable_loop_detection: bool = True,
        enable_trajectory_memory: bool = True
    ):
        """
        Initialize harness integration.
        
        Args:
            storage_path: Path for trajectory storage (default: ~/.kai/trajectories)
            enable_pre_completion: Enable pre-completion checks
            enable_loop_detection: Enable loop detection
            enable_trajectory_memory: Enable trajectory memory
        """
        # Initialize components
        self.pre_completion = (
            PreCompletionChecklistMiddleware() 
            if enable_pre_completion else None
        )
        
        self.loop_detector = (
            LoopDetectionMiddleware() 
            if enable_loop_detection else None
        )
        
        self.trajectory_store = (
            TrajectoryMemoryStore(storage_path=storage_path or "~/.kai/trajectories")
            if enable_trajectory_memory else None
        )
        
        # Current trajectory state
        self.current_trajectory: Optional[Trajectory] = None
        self.current_steps: List[ExecutionStep] = []
        self.start_time: Optional[float] = None
        
    # ========================================
    # Loop Detection Integration
    # ========================================
    
    def check_before_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if tool should be executed (loop detection).
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            (should_execute, reason_if_blocked)
        """
        if not self.loop_detector:
            return True, None
        
        return self.loop_detector.check_before_execution(
            tool_name=tool_name,
            arguments=arguments
        )
    
    def record_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        success: bool = True
    ):
        """
        Record tool execution for loop detection and trajectory memory.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            result: Execution result
            success: Whether execution succeeded
        """
        # Record for loop detection
        if self.loop_detector:
            self.loop_detector.record_execution_result(
                tool_name=tool_name,
                arguments=arguments,
                result=result
            )
        
        # Record for trajectory memory
        if self.trajectory_store and self.current_trajectory:
            step = ExecutionStep(
                step_number=len(self.current_steps) + 1,
                tool_name=tool_name,
                arguments=arguments,
                result_summary=str(result)[:200],  # Truncate for storage
                success=success,
                duration_ms=None  # Could be calculated if we track times
            )
            self.current_steps.append(step)
    
    # ========================================
    # Pre-Completion Check Integration
    # ========================================
    
    def check_completion(
        self,
        task_context: Dict[str, Any],
        agent_output: Dict[str, Any],
        plan: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if task is truly complete (pre-completion checks).
        
        Args:
            task_context: Task context (task, constraints, acceptance_criteria)
            agent_output: Agent's output
            plan: Optional plan (if planning was done)
            
        Returns:
            (should_complete, reason_if_not)
        """
        if not self.pre_completion:
            return True, None
        
        result = self.pre_completion.check(
            task_context=task_context,
            agent_output=agent_output,
            plan=plan
        )
        
        if not result.all_passed:
            failures = "\n".join(
                f"  [{f.severity.upper()}] {f.check_name}: {f.message}"
                for f in result.failures
            )
            reason = f"Pre-completion checks failed:\n{failures}"
            return False, reason
        
        return True, None
    
    # ========================================
    # Trajectory Memory Integration
    # ========================================
    
    def start_trajectory(self, task: str, task_type: str = "general"):
        """
        Start tracking a new trajectory.
        
        Args:
            task: Task description
            task_type: Task type (coding, debugging, research, etc.)
        """
        if not self.trajectory_store:
            return
        
        self.current_steps = []
        self.start_time = time.time()
        self.current_trajectory = Trajectory(
            trajectory_id=f"traj-{int(time.time() * 1000)}",
            task_description=task,
            task_type=task_type,
            steps=[],
            final_outcome="running",
            total_duration_ms=0,
            tags=[task_type],
            metadata={}
        )
    
    def end_trajectory(self, outcome: str = "success"):
        """
        End trajectory tracking and store.
        
        Args:
            outcome: Final outcome (success, failure, partial)
        """
        if not self.trajectory_store or not self.current_trajectory:
            return
        
        # Calculate duration
        duration_ms = 0
        if self.start_time:
            duration_ms = int((time.time() - self.start_time) * 1000)
        
        # Update trajectory
        self.current_trajectory.steps = self.current_steps
        self.current_trajectory.final_outcome = outcome
        self.current_trajectory.total_duration_ms = duration_ms
        
        # Store trajectory
        self.trajectory_store.store(self.current_trajectory)
        
        # Reset state
        self.current_trajectory = None
        self.current_steps = []
        self.start_time = None
    
    def get_similar_trajectories(self, task: str, limit: int = 3) -> List[Trajectory]:
        """
        Get similar past trajectories for a task.
        
        Args:
            task: Task description
            limit: Maximum number of trajectories
            
        Returns:
            List of similar trajectories
        """
        if not self.trajectory_store:
            return []
        
        return self.trajectory_store.retrieve_similar(
            task_description=task,
            limit=limit
        )
    
    def get_success_tips(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get tips from successful past executions.
        
        Args:
            task_type: Optional filter by task type
            
        Returns:
            List of success tips
        """
        if not self.trajectory_store:
            return []
        
        return self.trajectory_store.get_success_tips(task_type=task_type)
    
    # ========================================
    # Statistics & Monitoring
    # ========================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get harness statistics.
        
        Returns:
            Dictionary of statistics from all components
        """
        stats = {
            "pre_completion": None,
            "loop_detection": None,
            "trajectory_memory": None
        }
        
        if self.loop_detector:
            stats["loop_detection"] = self.loop_detector.get_statistics()
        
        if self.trajectory_store:
            stats["trajectory_memory"] = self.trajectory_store.get_statistics()
        
        return stats


# Convenience function for quick integration
def create_harness(
    storage_path: Optional[str] = None,
    enable_all: bool = True
) -> HarnessIntegration:
    """
    Create a harness integration with sensible defaults.
    
    Args:
        storage_path: Optional custom storage path
        enable_all: Enable all components (default: True)
        
    Returns:
        Configured HarnessIntegration instance
    """
    return HarnessIntegration(
        storage_path=storage_path,
        enable_pre_completion=enable_all,
        enable_loop_detection=enable_all,
        enable_trajectory_memory=enable_all
    )

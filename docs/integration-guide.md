"""
KaiAgent Harness Integration Guide

This guide shows how to integrate Phase 1 harness components into KaiAgent.
"""

# ========================================
# OPTION 1: QUICK START (Recommended)
# ========================================

from kai_code.harness import create_harness

# Create harness with defaults
harness = create_harness()

# Use in your KaiAgent
harness.start_trajectory(task="Fix authentication bug")

# Before tool execution
should_exec, reason = harness.check_before_tool("read_file", {"path": "auth.py"})
if not should_exec:
    print(f"Loop detected: {reason}")
    # Handle loop

# After tool execution
harness.record_tool_execution("read_file", {"path": "auth.py"}, result, success=True)

# Before task completion
task_context = {
    "task": "Fix authentication bug",
    "constraints": ["Don't break existing tests"],
    "acceptance_criteria": ["Auth works", "Tests pass"]
}
should_complete, reason = harness.check_completion(task_context, agent_output)
if not should_complete:
    print(f"Not ready: {reason}")
    # Continue working

# End trajectory
harness.end_trajectory(outcome="success")


# ========================================
# OPTION 2: CUSTOM CONFIGURATION
# ========================================

from kai_code.harness import HarnessIntegration

harness = HarnessIntegration(
    storage_path="~/.kai/custom_trajectories",
    enable_pre_completion=True,
    enable_loop_detection=True,
    enable_trajectory_memory=True
)


# ========================================
# OPTION 3: PARTIAL INTEGRATION
# ========================================

# Only loop detection
harness = HarnessIntegration(
    enable_pre_completion=False,
    enable_loop_detection=True,
    enable_trajectory_memory=False
)


# ========================================
# INTEGRATION WITH KAIAGENT
# ========================================

class KaiAgent:
    """Example KaiAgent with harness integration"""
    
    def __init__(self):
        # Initialize harness
        self.harness = create_harness(
            storage_path="~/.kai/trajectories"
        )
    
    async def run(self, task: str):
        """Run agent with harness integration"""
        
        # Start trajectory tracking
        self.harness.start_trajectory(task)
        
        try:
            # Get similar past trajectories for context
            similar = self.harness.get_similar_trajectories(task)
            if similar:
                print(f"Found {len(similar)} similar past tasks")
                for traj in similar:
                    print(f"  - {traj.task_description}: {traj.final_outcome}")
            
            # Get success tips
            tips = self.harness.get_success_tips()
            if tips:
                print("Success tips:")
                for tip in tips[:3]:
                    print(f"  - {tip['tool']}: {tip.get('frequency', 0)} times")
            
            # Execute task (simplified)
            result = await self._execute_task(task)
            
            # Check completion
            task_context = {
                "task": task,
                "constraints": [],
                "acceptance_criteria": ["Task completed"]
            }
            should_complete, reason = self.harness.check_completion(
                task_context, 
                result
            )
            
            if should_complete:
                self.harness.end_trajectory(outcome="success")
                return result
            else:
                self.harness.end_trajectory(outcome="partial")
                # Continue working...
                return {"status": "needs_more_work", "reason": reason}
                
        except Exception as e:
            self.harness.end_trajectory(outcome="failure")
            raise
    
    async def _execute_tool(self, tool_name: str, args: dict):
        """Execute tool with loop detection"""
        
        # Check for loops
        should_exec, reason = self.harness.check_before_tool(tool_name, args)
        if not should_exec:
            return {"error": f"Loop detected: {reason}"}
        
        # Execute tool
        try:
            result = await self._call_tool(tool_name, args)
            success = True
        except Exception as e:
            result = str(e)
            success = False
        
        # Record execution
        self.harness.record_tool_execution(tool_name, args, result, success)
        
        return result
    
    async def _call_tool(self, tool_name: str, args: dict):
        """Actual tool implementation"""
        # Your tool implementation here
        pass
    
    async def _execute_task(self, task: str):
        """Task execution logic"""
        # Your task implementation here
        pass


# ========================================
# CLI INTEGRATION
# ========================================

# In cli.py, add these commands:

@app.command("checklist")
def checklist_command():
    """Show pre-completion checklist status"""
    harness = create_harness(enable_loop_detection=False, enable_trajectory_memory=False)
    
    # Example context
    task_context = {
        "task": "Fix auth bug",
        "constraints": ["Don't break tests"],
        "acceptance_criteria": ["Auth works"]
    }
    
    result = harness.pre_completion.check(task_context, {})
    print(result.summary())


@app.command("trajectories")
def trajectories_command(task: str, limit: int = 5):
    """Show similar past trajectories"""
    harness = create_harness(enable_pre_completion=False, enable_loop_detection=False)
    
    similar = harness.get_similar_trajectories(task, limit=limit)
    
    print(f"Found {len(similar)} similar trajectories:\n")
    for i, traj in enumerate(similar, 1):
        print(f"{i}. {traj.task_description}")
        print(f"   Outcome: {traj.final_outcome}")
        print(f"   Steps: {len(traj.steps)}")
        print(f"   Duration: {traj.total_duration_ms}ms")
        print()


@app.command("loops")
def loops_command():
    """Show loop detection statistics"""
    harness = create_harness(enable_pre_completion=False, enable_trajectory_memory=False)
    
    stats = harness.loop_detector.get_statistics()
    print("Loop Detection Statistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Unique tools: {stats['unique_tools']}")
    print(f"  Most repeated tools:")
    for tool, count in stats['most_repeated_tools']:
        print(f"    - {tool}: {count} times")


# ========================================
# MONITORING & DEBUGGING
# ========================================

# Get harness statistics
stats = harness.get_statistics()
print("Harness Statistics:")
for component, data in stats.items():
    if data:
        print(f"{component}: {data}")


# ========================================
# TESTING INTEGRATION
# ========================================

import pytest

def test_harness_integration():
    """Test harness integration"""
    harness = create_harness()
    
    # Test loop detection
    should_exec, _ = harness.check_before_tool("read", {"path": "test.py"})
    assert should_exec == True
    
    # Test trajectory tracking
    harness.start_trajectory("Test task")
    harness.record_tool_execution("read", {"path": "test.py"}, "content")
    harness.end_trajectory("success")
    
    # Test pre-completion
    task_context = {
        "task": "Test",
        "constraints": [],
        "acceptance_criteria": []
    }
    should_complete, _ = harness.check_completion(task_context, {})
    # May or may not pass depending on checks

if __name__ == "__main__":
    # Quick test
    harness = create_harness()
    print("✅ Harness integration ready")
    print(harness.get_statistics())

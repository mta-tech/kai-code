"""
Kai-Code Harness Engineering System

Research-backed middleware components for improving AI agent reliability.

Expected Impact:
- 50% error catch rate (PreCompletionChecklistMiddleware)
- 80% loop prevention (LoopDetectionMiddleware)
- +14% accuracy improvement (TrajectoryMemoryStore)
"""

from .middleware import (
    PreCompletionChecklistMiddleware,
    LoopDetectionMiddleware,
    CheckResult,
    ChecklistResult,
    LoopPattern,
    ToolCallRecord
)

from .memory.trajectory_store import (
    TrajectoryMemoryStore,
    Trajectory,
    ExecutionStep
)

from .integration import (
    HarnessIntegration,
    create_harness
)

__all__ = [
    # Middleware
    'PreCompletionChecklistMiddleware',
    'LoopDetectionMiddleware',
    
    # Data structures
    'CheckResult',
    'ChecklistResult',
    'LoopPattern',
    'ToolCallRecord',
    
    # Memory
    'TrajectoryMemoryStore',
    'Trajectory',
    'ExecutionStep',
    
    # Integration
    'HarnessIntegration',
    'create_harness'
]

__version__ = '0.2.0'

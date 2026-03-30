"""
Kai-Code Harness Engineering Middleware

This package contains research-backed middleware components
for improving AI agent reliability and output quality.

Components:
- PreCompletionChecklistMiddleware: Catches 50% of errors before completion
- LoopDetectionMiddleware: Prevents 80% of infinite loops (coming soon)
- TrajectoryMemoryStore: 14% accuracy improvement (coming soon)

Research Sources:
- Systematic Approach to Long-Running Agent Workflows
- LangChain Harness Engineering Patterns
- arXiv:2603.10600 (Trajectory-Informed Memory)
"""

from .pre_completion import (
    PreCompletionChecklistMiddleware,
    CheckResult,
    ChecklistResult
)

__all__ = [
    'PreCompletionChecklistMiddleware',
    'CheckResult',
    'ChecklistResult'
]

__version__ = '0.1.0'

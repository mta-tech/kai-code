"""
Cost Tracking Module for KaiAgent

Tracks token usage across agent turns for production monitoring.
Pattern adapted from claw-code UsageSummary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UsageSummary:
    """Token usage summary for a single turn or session.
    
    Attributes:
        input_tokens: Number of input tokens (approximate)
        output_tokens: Number of output tokens (approximate)
        turn_count: Number of turns tracked
    """
    input_tokens: int = 0
    output_tokens: int = 0
    turn_count: int = 0

    def add_turn(
        self, 
        prompt: str, 
        output: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None
    ) -> UsageSummary:
        """Add a turn to the usage summary.
        
        Args:
            prompt: User prompt text
            output: Agent output text
            input_tokens: Exact input token count (optional, will estimate if not provided)
            output_tokens: Exact output token count (optional, will estimate if not provided)
        
        Returns:
            New UsageSummary with updated counts
        """
        # Use exact counts if provided, otherwise estimate
        input_count = input_tokens if input_tokens is not None else len(prompt.split())
        output_count = output_tokens if output_tokens is not None else len(output.split())
        
        return UsageSummary(
            input_tokens=self.input_tokens + input_count,
            output_tokens=self.output_tokens + output_count,
            turn_count=self.turn_count + 1,
        )

    def total_tokens(self) -> int:
        """Get total tokens (input + output)."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens(),
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"UsageSummary(turns={self.turn_count}, "
            f"input={self.input_tokens:,}, "
            f"output={self.output_tokens:,}, "
            f"total={self.total_tokens():,})"
        )


@dataclass
class CostTracker:
    """Tracks usage across multiple sessions and agents.
    
    Provides aggregated cost tracking for production monitoring.
    """
    sessions: dict[str, UsageSummary] = field(default_factory=dict)
    
    def add_session(self, session_id: str, usage: UsageSummary) -> None:
        """Add or update a session's usage."""
        if session_id in self.sessions:
            # Merge with existing
            existing = self.sessions[session_id]
            self.sessions[session_id] = UsageSummary(
                input_tokens=existing.input_tokens + usage.input_tokens,
                output_tokens=existing.output_tokens + usage.output_tokens,
                turn_count=existing.turn_count + usage.turn_count,
            )
        else:
            self.sessions[session_id] = usage
    
    def get_session(self, session_id: str) -> UsageSummary | None:
        """Get usage for a specific session."""
        return self.sessions.get(session_id)
    
    def get_total(self) -> UsageSummary:
        """Get total usage across all sessions."""
        total_input = sum(s.input_tokens for s in self.sessions.values())
        total_output = sum(s.output_tokens for s in self.sessions.values())
        total_turns = sum(s.turn_count for s in self.sessions.values())
        
        return UsageSummary(
            input_tokens=total_input,
            output_tokens=total_output,
            turn_count=total_turns,
        )
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session's usage."""
        self.sessions.pop(session_id, None)
    
    def clear_all(self) -> None:
        """Clear all sessions."""
        self.sessions.clear()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sessions": {
                sid: usage.to_dict() 
                for sid, usage in self.sessions.items()
            },
            "total": self.get_total().to_dict(),
        }


__all__ = ["UsageSummary", "CostTracker"]

# Auto-Compact When Tokens Near Limit - Design Document

**Date:** 2025-01-19
**Status:** Design Approved
**Author:** AI Design Assistant (Brainstorming Session)

## Overview

This document describes the design for an **auto-compact feature** that automatically reduces conversation history when token usage approaches the model's context window limit. The feature uses intelligent content selection and AI-powered summarization to preserve critical context while freeing up tokens for continued conversation.

## Problem Statement

As conversations grow longer, token usage accumulates and eventually approaches the model's context window limit. kai-code currently displays color-coded warnings (yellow at 80%, red at 95%) but takes no automatic action. Users must manually `/clear` the conversation or hit context limits, causing:

1. **Lost context** - Valuable conversation history is discarded
2. **Interrupted flow** - Users must stop to manage context manually
3. **Reduced utility** - Large context windows are underutilized

## Requirements Summary

| Requirement | Choice | Rationale |
|-------------|--------|-----------|
| Trigger | Fixed 85% threshold | Predictable, avoids last-minute panic |
| Method | AI summarization | Preserves semantic meaning vs truncation |
| Selection | Smart algorithm | Balances automation with importance |
| User control | Fully automatic | Set-and-forget, reduces cognitive load |
| Persistence | Session-only | Simpler implementation, fresh starts |

## Architecture

### High-Level Flow

```
TokenTracker detects 85% usage
         ↓
CompactionManager.check_and_compact()
         ↓
┌─────────────────────────────────────┐
│ 1. Pause new message processing     │
│ 2. SmartContentSelector.classify()  │
│ 3. ContentSummarizer.summarize()    │
│ 4. ConversationManager.rebuild()    │
│ 5. Resume processing                │
└─────────────────────────────────────┘
         ↓
Updated conversation history with summaries
```

### Components

#### New Package Structure

```
src/kai_code/compaction/
├── __init__.py       # Package exports
├── manager.py        # CompactionManager - orchestrates the process
├── selector.py       # SmartContentSelector - classifies messages
├── summarizer.py     # ContentSummarizer - generates summaries
├── state.py          # CompactionState enum
└── prompts.py        # Summarization prompt templates
```

#### CompactionManager

```python
class CompactionManager:
    """Coordinates the auto-compaction process."""

    def __init__(
        self,
        threshold: float = 0.85,
        recent_window_turns: int = 10,
        min_time_between: int = 300,
    ):
        self.threshold = threshold
        self.recent_window_turns = recent_window_turns
        self.min_time_between = min_time_between
        self.state: CompactionState = CompactionState.IDLE
        self.last_compaction_time: float | None = None
        self.selector = SmartContentSelector()
        self.summarizer = ContentSummarizer()

    def check_and_compact(
        self,
        token_tracker: TokenTracker,
        conversation_manager: ConversationManager,
    ) -> bool:
        """Check threshold and trigger compaction if needed."""
        if not self._should_compact(token_tracker):
            return False

        self.state = CompactionState.COMPACTING
        try:
            # Get messages and classify
            messages = conversation_manager.get_messages_for_compaction()
            keep, summarize = self.selector.classify_messages(
                messages,
                self.recent_window_turns
            )

            # Summarize batches
            summaries = []
            for batch in batch_messages(summarize, batch_size=10):
                summary = await self.summarizer.summarize_batch(batch, llm)
                summaries.append(summary)

            # Rebuild history
            conversation_manager.rebuild_with_compacted_history(keep, summaries)

            # Update token tracker
            token_tracker.recalculate()

            self.state = CompactionState.COMPLETE
            self.last_compaction_time = time.time()
            return True

        except Exception as e:
            self.state = CompactionState.FAILED
            logger.error(f"Compaction failed: {e}")
            return False

    def is_running(self) -> bool:
        """Check if compaction is in progress."""
        return self.state in (
            CompactionState.TRIGGERED,
            CompactionState.COMPACTING,
            CompactionState.REBUILDING,
        )

    def _should_compact(self, token_tracker: TokenTracker) -> bool:
        """Check if compaction should trigger."""
        # Check threshold
        if token_tracker.get_usage_percentage() < self.threshold:
            return False

        # Check cooldown
        if self.last_compaction_time:
            elapsed = time.time() - self.last_compaction_time
            if elapsed < self.min_time_between:
                return False

        # Check already running
        if self.is_running():
            return False

        return True
```

#### SmartContentSelector

```python
class SmartContentSelector:
    """Selects which content to keep vs summarize."""

    def classify_messages(
        self,
        messages: list[Message],
        recent_turns: int,
    ) -> tuple[list[Message], list[Message]]:
        """
        Classify messages into keep and summarize piles.

        Returns:
            (keep_messages, summarize_messages)
        """
        keep = []
        summarize = []

        # Calculate recent window
        recent_start = max(0, len(messages) - recent_turns * 2)  # *2 for user+assistant

        for i, msg in enumerate(messages):
            if self._should_keep(msg, i, recent_start):
                keep.append(msg)
            else:
                summarize.append(msg)

        return keep, summarize

    def _should_keep(self, msg: Message, index: int, recent_start: int) -> bool:
        """Determine if a message should be kept verbatim."""
        # Always keep recent messages
        if index >= recent_start:
            return True

        # Always keep [keep] tagged messages
        if "[keep]" in msg.content.lower():
            return True

        # Always keep error messages
        if msg.role == "tool" and msg.was_error:
            return True

        # Summarize large tool outputs
        if msg.role == "tool" and msg.token_count > 1000:
            return False

        # Use importance score for rest
        return self._calculate_importance_score(msg) > 0.5

    def _calculate_importance_score(self, msg: Message) -> float:
        """Score message by retention importance (0.0 - 1.0)."""
        score = 0.5  # Base score

        # User questions are important
        if msg.role == "user" and "?" in msg.content:
            score += 0.2

        # Code blocks should be preserved
        if "```" in msg.content:
            score += 0.15

        # Tool calls with errors are critical
        if msg.role == "tool" and msg.was_error:
            score += 0.3

        # Large file reads can be summarized
        if msg.tool_name == "read_file" and msg.token_count > 500:
            score -= 0.2

        return min(max(score, 0.0), 1.0)
```

#### ContentSummarizer

```python
class ContentSummarizer:
    """Generates summaries of conversation content."""

    async def summarize_batch(
        self,
        messages: list[Message],
        llm: BaseLanguageModel,
    ) -> str:
        """Summarize a batch of messages."""
        prompt = self._build_summarization_prompt(messages)

        response = await llm.ainvoke(prompt)
        return response.content

    def _build_summarization_prompt(self, messages: list[Message]) -> str:
        """Build prompt for LLM summarization."""
        messages_text = self._format_messages(messages)

        return f"""You are compacting AI conversation history to save tokens while preserving critical information.

SUMMARIZE the following conversation messages into a concise representation that:
- Preserves all file paths, function names, variable names, error messages
- Captures the core intent and outcome of each exchange
- Removes redundant explanations and conversational filler
- Uses bullet points for structured information
- Keeps code snippets only if they show unique patterns or solutions

INPUT MESSAGES:
{messages_text}

OUTPUT FORMAT:
[COMPACTED] Summary of {len(messages)} message exchange
- Key points extracted
- Important technical details preserved
- File references: path1, path2, path3
- Next context: what should be remembered for continuation"""

    def _format_messages(self, messages: list[Message]) -> str:
        """Format messages for the prompt."""
        lines = []
        for msg in messages:
            role = msg.role.upper()
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            lines.append(f"{role}: {content}")
        return "\n\n".join(lines)
```

### Integration with Existing Code

#### TokenTracker Extension

```python
# src/kai_code/cli_ui.py

class TokenTracker:
    def __init__(self, ...):
        # ... existing code ...
        self.compaction_manager: CompactionManager | None = None

    def add_tokens(self, count: int, ...) -> None:
        """Add tokens and check for compaction threshold."""
        # ... existing token counting logic ...

        # Check compaction threshold
        if self.compaction_manager:
            self.compaction_manager.check_and_compact(self, conversation_manager)
```

#### ConversationManager Extension

```python
# src/kai_code/rich_ui/conversation_manager.py

class ConversationManager:
    def get_messages_for_compaction(self) -> list[Message]:
        """Return all messages eligible for compaction."""
        return self.messages.copy()

    def rebuild_with_compacted_history(
        self,
        kept_messages: list[Message],
        summaries: list[str],
    ) -> None:
        """Replace history with compacted version."""
        self.messages.clear()

        # Add kept messages
        self.messages.extend(kept_messages)

        # Add summary as a system message
        summary_msg = Message(
            role="system",
            content="\n\n".join(summaries),
            metadata={"compacted": True}
        )
        self.messages.insert(0, summary_msg)
```

## State Management

### Compaction States

```python
class CompactionState(Enum):
    """States in the compaction lifecycle."""
    IDLE = "idle"              # No compaction active
    TRIGGERED = "triggered"    # Threshold exceeded, preparing
    COMPACTING = "compacting"  # Actively summarizing
    REBUILDING = "rebuilding"  # Rebuilding conversation
    COMPLETE = "complete"      # Successfully finished
    FAILED = "failed"          # Error occurred
```

### State Transitions

```
IDLE → TRIGGERED (threshold reached)
TRIGGERED → COMPACTING (started processing)
COMPACTING → REBUILDING (summarization done)
REBUILDING → COMPLETE (history rebuilt)
COMPACTING → FAILED (error occurred)
FAILED → IDLE (ready to retry)
```

## Configuration

### Settings Schema

```json
{
  "compaction": {
    "enabled": true,
    "threshold": 0.85,
    "recent_window_turns": 10,
    "min_time_between": 300,
    "max_summary_tokens": 1000
  }
}
```

### Configuration Loading

Priority order (highest first):
1. CLI flags (`--no-compact`, `--compact-threshold`)
2. Project local settings (`.kai/settings.local.json`)
3. Project settings (`.kai/settings.json`)
4. Global settings (`~/.kai/settings.json`)
5. Default values

### CLI Flags

```bash
kai-code --no-compact              # Disable entirely
kai-code --compact-threshold 0.80  # Use 80% threshold
```

### Slash Commands

```
/compact status    # Show compaction state and last run
/compact now       # Manually trigger compaction
/compact disable   # Disable for session
/compact enable    # Re-enable
```

## Error Handling

### Failure Scenarios

| Scenario | Handling |
|----------|----------|
| LLM summarization fails | Fall back to simple truncation (drop oldest) |
| User interrupts (Ctrl+C) | Cancel gracefully, keep original history |
| Instant jump from 84% → 100% | Abort compaction, let LLM fail naturally |
| Empty history | Skip compaction, return to IDLE |
| Summary too large | Add `[COMPACTED]` tag, exclude from future |

### User Feedback

```python
# During compaction
status_bar.update("Compacting context...")

# Success
console.print("[green]✓[/green] Context compacted: 50K → 15K tokens")

# Failure
console.print("[yellow]⚠[/yellow] Compaction failed: {error}")

# Near-limit warning
console.print("[red]⚠[/red] Context at 98%. Use /clear to reset.")
```

## Implementation Phases

### Phase 1: Foundation
- Create `CompactionManager` skeleton
- Implement `SmartContentSelector`
- Add threshold check in `TokenTracker`
- Add basic configuration loading

### Phase 2: Summarization
- Implement `ContentSummarizer`
- Add async LLM calls
- Implement history rebuild

### Phase 3: Refinement
- Add fallback truncation
- Implement cooldown timer
- Handle concurrent messages
- Error recovery

### Phase 4: User Controls
- Add slash commands
- Implement CLI flags
- Project settings override

### Phase 5: Testing & Docs
- Unit tests
- Integration tests
- Documentation

**Estimated Timeline:** ~9 days

## Testing Strategy

### Unit Tests
- `test_selector_classifies_keep_messages()` - Recent window preserved
- `test_selector_respects_keep_tag()` - `[keep]` messages retained
- `test_selector_handles_large_tool_outputs()` - Large outputs marked for summary
- `test_summarizer_produces_compact_output()` - Summary < original
- `test_manager_triggers_at_threshold()` - 85% triggers compaction
- `test_manager_respects_cooldown()` - Won't run twice in 5 min

### Integration Tests
- `test_full_compaction_flow()` - End-to-end compaction
- `test_compaction_preserves_recent_context()` - Recent messages unchanged

## Future Enhancements (Out of Scope)

- Persistent summaries across sessions
- User-defined compaction strategies
- Hook system for custom actions
- ML-based importance ranking

## References

- Claude Code auto-compact: Triggers at ~75% (25% remaining)
- LangChain ConversationSummaryBufferMemory: Token-length based pruning
- Cursor hooks: `beforeCompaction` observational hook

## Appendix: Research Findings

### Claude Code Approach
- Auto-compacts at ~25% remaining context (75% usage)
- Reserves ~20% for compaction process
- User complaints: interrupts near-complete work
- No user control over what gets compacted

### LangChain Approach
- `ConversationSummaryBufferMemory`
- Keeps recent + summary of older
- Uses token length (not turn count)
- Flushes old to summary when approaching limit

### Cursor Approach
- `beforeCompaction` hook (observational)
- Automatically condenses files to fit context

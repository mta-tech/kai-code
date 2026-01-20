# Auto-Compact Guide

## Overview

The auto-compact feature automatically compresses long conversations when they approach the model's context window limit, preserving critical information while freeing up tokens for continued work.

## How It Works

1. **Monitoring**: TokenTracker monitors context usage in real-time
2. **Trigger**: At 85% usage (configurable), compaction begins
3. **Selection**: Smart algorithm classifies messages:
   - Recent messages (last 10 turns) - always kept
   - `[keep]` tagged messages - always kept
   - Error messages - always kept
   - Large tool outputs - summarized
4. **Summarization**: LLM condenses older messages into compact summaries
5. **Rebuild**: Conversation history is rebuilt with summaries + recent messages

## Configuration

### Settings File

Add to `~/.kai/settings.json` or `/.kai/settings.json`:

```json
{
  "compaction": {
    "enabled": true,
    "threshold": 0.85,
    "recent_window_turns": 10
  }
}
```

### CLI Flags

```bash
# Disable compaction
kai-code --no-compact

# Custom threshold (90%)
kai-code --compact-threshold 0.90
```

## Slash Commands

Interactive session commands:

```
/compact status    # Show current state
/compact now       # Trigger manually
/compact enable    # Enable for session
/compact disable   # Disable for session
```

## Best Practices

1. **Use `[keep]` tags**: Mark important context to preserve
   ```
   User: [keep] Remember we're using the v2 API
   ```

2. **Check before big tasks**: Use `/compact status` to see current state

3. **Manual compaction**: Trigger with `/compact now` before context-heavy work

4. **Adjust threshold**: Lower threshold (0.80) for aggressive compaction, higher (0.90) for more context

## Troubleshooting

### Compaction not triggering

- Check if enabled: `/compact status`
- Verify threshold: Default is 85%, ensure you're above it
- Check cooldown: Minimum 5 minutes between compactions

### Too much context lost

- Increase `recent_window_turns` in settings
- Use `[keep]` tags for important context
- Increase `threshold` to compact later

### Summaries losing important info

- Tag critical messages with `[keep]`
- The LLM is instructed to preserve errors, file paths, and code patterns

## Technical Details

See design document: `docs/plans/2025-01-19-auto-compact-design.md`

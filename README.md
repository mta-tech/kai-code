# Stream JSON Schema

This document defines the stable JSONL schema for streaming events from the agent.

## Event Types

All events are JSON objects separated by newlines. Each event has a `type` field.

### 1. `init`
Emitted at the start of a stream.
```json
{
  "type": "init",
  "id": "run_id_...",
  "timestamp": "2023-10-27T10:00:00Z"
}
```

### 2. `message`
Emitted for text deltas or complete messages.
```json
{
  "type": "message",
  "content": "Hello",
  "delta": true, 
  "index": 0
}
```

### 3. `tool_call`
Emitted when a tool is called.
```json
{
  "type": "tool_call",
  "id": "call_id_...",
  "name": "calculator",
  "arguments": "{\"a\": 1, \"b\": 2}"
}
```

### 4. `tool_result`
Emitted when a tool returns a result.
```json
{
  "type": "tool_result",
  "id": "call_id_...",
  "result": "3"
}
```

### 5. `error`
Emitted when an exception occurs.
```json
{
  "type": "error",
  "message": "Something went wrong",
  "code": 500
}
```

### 6. `result`
Emitted at the end of the stream with the final aggregate result.
```json
{
  "type": "result",
  "output": "...",
  "stats": {
    "token_usage": 150,
    "latency_ms": 500
  }
}
```

## Usage

Use the `StreamProcessor` class to wrap existing chunks.

## Verification

To verify the schema implementation without an LLM:

```bash
python3 verify_schema.py
```

This script runs a dry-run simulation of various chunk types (messages, tool calls, results) and validates the output against the defined schema.

```
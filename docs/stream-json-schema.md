# `--output-format stream-json` schema

Kai emits JSONL (one JSON object per line).

This schema is intentionally **stable** and **best-effort**: when a chunk cannot be
cleanly mapped, Kai includes the original `raw` chunk so clients can still recover
information.

For non-stream `--output-format json`, errors are emitted as a single JSON object with
`type: "error"` (see README).

## Common fields

- `type`: event type (see below)
- `schema_version`: currently `1`
- `run_id`: unique id per CLI invocation
- `event_id`: monotonically increasing integer per *emitted* event (unique per run)
- `ts_ms`: event timestamp in ms

Kai also emits common metadata fields (best-effort) on all events:
- `thread_id`, `state_path`
- `model`, `provider`, `permission_mode`
- `tools`: enabled-tools filter for the run/session (or `null`)

### Event filtering

Use `--stream-event-types` to emit only a subset of event types (comma-separated).
`init` and `result` are always emitted.

## Event types

### `init`

Emitted once at the start.

Fields:
- `thread_id`, `state_path`
- `model`, `provider`, `permission_mode`

### `message`

Best-effort assistant streaming text.

Fields:
- `role`: currently `assistant`
- `delta`: newly observed suffix
- `content`: full current content

Grouping fields (best-effort):
- `turn_id`: 0-based index of the latest user message
- `step_id`: 0-based index of the latest assistant message

May include:
- `raw`: underlying chunk when it doesn't map cleanly

### `tool_call`

Emitted when Kai detects a tool call from streamed message snapshots, or when the
agent interrupts for HITL approvals.

Fields (best-effort):
- `turn_id`, `step_id`
- `tool_index`: 0-based index of tool events within the current snapshot
- `msg_index`: message index within the snapshot `messages` list (when available)
- `part_index`: index within a message content block list (when available)
- `tool_call_id`
- `tool_name`
- `args`
- `interrupt`: present when the event came from HITL interrupt
- `resume_hint`: present when interrupting and CLI can suggest next step
- `raw`: always included for tool events

### `tool_result`

Emitted when Kai detects a tool output/result from streamed message snapshots.

Fields (best-effort):
- `turn_id`, `step_id`
- `tool_index`, `msg_index`, `part_index`
- `tool_call_id`
- `tool_name`
- `content`

Additional timing field:
- `tool_latency_ms`: when a matching `tool_call` was seen earlier in the run (best-effort)

Additional extracted fields (when available):
- `stdout`, `stderr`
- `exit_code`
- `status`
- `command`

If the underlying provider omits tool call ids, Kai correlates a `tool_result` to the
most recent unmatched `tool_call` within the same snapshot order and assigns that
`tool_call_id`.
- `raw`

### `turn_start` / `turn_end`

Deterministic lifecycle events derived from changes in streamed `messages` snapshots.

- `turn_start`: emitted when a new `turn_id` is first observed
- `turn_end`: emitted when the run ends or the turn advances

Fields:
- `turn_id`
- `stop_reason` on `turn_end` (e.g. `end_turn`, `interrupt`, `error`, `turn_advanced`)

### `step_start` / `step_end`

Optional deterministic lifecycle events derived from changes in assistant message count.

Fields:
- `turn_id`, `step_id`
- `stop_reason` on `step_end` (e.g. `end_turn`, `interrupt`, `error`, `step_advanced`)

### `error`

Unexpected exception.

Fields:
- `message`
- `error_type`
- `traceback` (only when enabled via `--stream-include-traceback`, `--include-traceback`, or env)

Also included for schema consistency:
- `run_id`, `thread_id`, `state_path`
- `model`, `provider`, `permission_mode`
- `stop_reason: "error"`
- `stats`: same structure as in `result` event (best-effort, may have partial data)

## Compatibility / guarantees

- New fields may be added over time; consumers should ignore unknown fields.
- `schema_version` is stable within major releases; breaking changes require a new version.
- If `--stream-event-types` is used, `init` and `result` are always emitted.

Grouping fields (best-effort):
- `turn_id`, `step_id`

### `result`

Emitted once at the end.

Fields:
- `persisted`: whether a session state file exists
- `interrupted`: whether the run ended in HITL interrupt
- `stop_reason`: best-effort reason (`end_turn`, `interrupt`, `error`, `dry_run`, ...)
- `output`: final best-effort output string
- `stats`: object containing run metrics (see below)

Grouping fields (best-effort):
- `turn_id`, `step_id` (the last observed ids for the run)

#### `stats` object

The `stats` object contains comprehensive metrics about the run:

**Timing metrics:**
- `duration_ms`: total run duration in milliseconds
- `started_ms`: run start timestamp (epoch ms)
- `ended_ms`: run end timestamp (epoch ms)
- `ttft_ms`: time to first token in milliseconds (best-effort, may be `null`)

**Interaction metrics:**
- `chunk_count`: number of streaming chunks received
- `interrupted`: whether the run was interrupted
- `message_count`: total number of messages in conversation
- `turn_count`: number of user messages (best-effort)
- `step_count`: number of assistant messages (best-effort)

**Tool usage metrics:**
- `tool_call_count`: number of unique tool calls observed
- `tool_result_count`: number of unique tool results observed
- `tool_error_count`: number of tool results that were errors (non-zero exit code or error status)
- `tool_count`: number of distinct tools used (unique tool names)
- `tool_names`: object mapping tool names to call counts (e.g., `{"Bash": 3, "Read": 2}`)

**Tool timing stats:**
- `tool_latency_ms_total`: sum of all tool latencies in milliseconds
- `tool_latency_ms_avg`: average tool latency (float, or `null` if no data)
- `tool_latency_ms_max`: maximum tool latency (or `null` if no data)

**Token usage:**
- `token_usage`: object with token counts (best-effort, values may be `null`):
  - `prompt_tokens`: input tokens sent to the model
  - `completion_tokens`: output tokens generated by the model
  - `total_tokens`: total tokens (prompt + completion)
  - `cached_input_tokens`: tokens served from cache (if provider supports)
  - `reasoning_tokens`: tokens used for reasoning (if provider supports)

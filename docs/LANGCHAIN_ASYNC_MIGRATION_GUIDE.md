# LangChain Async Migration Guide for KaiAgent

## Executive Summary

This guide provides comprehensive documentation on converting the KaiAgent system (which extends `deepagents`) from synchronous to asynchronous execution using LangChain's async APIs.

**Key Finding**: LangChain has full async support via "a" prefixed methods (`ainvoke`, `astream`, `astream_events`). The migration is straightforward but requires attention to callback propagation and Python version compatibility.

---

## 1. Version Information

### Project Dependencies
```
langchain-core: 1.2.3
langchain: 1.1.2
deepagents: >=0.2.8
langgraph: (bundled with deepagents)
Python: >=3.11 (recommended for async)
```

### Key Dependencies
- **deepagents** (>=0.2.8): Package providing `create_deep_agent()` that KaiAgent extends
- **langgraph**: Low-level orchestration framework for stateful agents (used by deepagents)
- **langchain-core**: Core `Runnable` interface with async support
- **Python 3.11+**: Recommended for proper context propagation in async contexts

---

## 2. Key Concepts

### 2.1 LangChain Async Architecture

LangChain uses an "a" prefix convention for async methods:

| Sync Method | Async Method | Description |
|-------------|--------------|-------------|
| `invoke()` | `ainvoke()` | Execute runnable and return final output |
| `stream()` | `astream()` | Stream output chunks as they're produced |
| `batch()` | `abatch()` | Execute multiple inputs in parallel |
| `stream_events()` | `astream_events()` | Stream intermediate events (tokens, tool calls, etc.) |

### 2.2 Runnable Interface

All LangChain components implement the `Runnable` interface, which provides:
- Synchronous execution methods
- Asynchronous execution methods (with "a" prefix)
- Configuration propagation via `RunnableConfig`
- Streaming capabilities

### 2.3 RunnableConfig

Configuration object that propagates settings through call chains:
- **callbacks**: For streaming and observability
- **tags**: For filtering and tracing
- **metadata**: For additional context
- **run_name**: For identifying specific runs

**Critical**: In async contexts, especially Python < 3.11, you must explicitly pass `RunnableConfig` to ensure callbacks propagate.

### 2.4 LangGraph Async Support

LangGraph (the underlying framework for `deepagents`) has comprehensive async support:
- `Pregel` graphs (returned by `create_deep_agent()`) support `ainvoke()`, `astream()`, `astream_events()`
- Checkpointing works with async execution
- State management is thread-safe
- Human-in-the-loop interrupts work with async

---

## 3. Current Implementation Analysis

### 3.1 Current Synchronous Implementation

**File**: `/Users/fitrakacamarga/project/self/bmad-new/kai-code-1/src/kai_code/agent.py`

#### Current `run()` Method (Lines 648-687)
```python
def run(self, prompt: str) -> KaiResult:
    """Run the agent with the given prompt."""
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]

    # SYNCHRONOUS CALL
    state = graph.invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)

    # Extract output from last message
    output = ""
    if self._messages:
        last = self._messages[-1]
        if last.get("role") in ("assistant", "ai"):
            output = last.get("content") or ""

    result = KaiResult(output=output, messages=list(self._messages), raw=state)

    # Ralph loop handling
    should_continue, next_prompt = self._ralph_hook.on_agent_complete(self, result)
    if should_continue and next_prompt:
        return self.run(next_prompt)  # Recursive call

    return result
```

#### Current `stream()` Method (Lines 711-731)
```python
def stream(self, prompt: str) -> Iterator[Any]:
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]
    last_snapshot: dict[str, Any] | None = None

    try:
        # SYNCHRONOUS STREAMING
        for chunk in graph.stream(
            {"messages": messages},
            config={"configurable": {"thread_id": self._thread_id}},
            stream_mode="values",
        ):
            if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                last_snapshot = chunk
            yield chunk
    finally:
        if last_snapshot is not None:
            try:
                self._update_from_state(last_snapshot)
            except Exception:
                pass
```

#### Current `resume()` Method (Lines 689-709)
```python
def resume(self, decisions: list[dict[str, Any]]) -> KaiResult:
    """Resume a human-in-the-loop interrupted run."""
    graph = self._build_graph()

    # SYNCHRONOUS CALL
    state = graph.invoke(
        Command(resume={"decisions": decisions}),
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)

    output = ""
    if self._messages:
        output = (self._messages[-1].get("content") or "")

    return KaiResult(output=output, messages=list(self._messages), raw=state)
```

### 3.2 Synchronous Tool Example

**Lines 543-608**: `execute_async_tool` (ironically named, but sync implementation)
```python
@tool("execute_async")
def execute_async_tool(command: str, timeout: int) -> str:
    """Execute shell command with auto-background on timeout."""
    import subprocess as sp

    try:
        # SYNCHRONOUS subprocess call
        result = sp.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,  # Synchronous timeout
            cwd=str(root_dir),
            env={**os.environ},
        )
        return json.dumps({"exit_code": result.returncode, "output": output})
    except sp.TimeoutExpired as e:
        # Promote to background task
        task_id = task_manager.run_shell(command, working_dir=root_dir)
        return json.dumps({
            "moved_to_background": True,
            "task_id": task_id,
            "message": f"Command exceeded {timeout}s timeout, moved to background."
        })
```

---

## 4. Async Migration Guide

### 4.1 API Reference

#### 4.1.1 `ainvoke()` - Async Execution

**Signature**:
```python
async def ainvoke(
    self,
    input: Input,
    config: RunnableConfig | None = None,
    **kwargs: Any
) -> Output
```

**Parameters**:
- `input`: The input to the runnable (usually a dict with "messages" key)
- `config`: RunnableConfig for callbacks, metadata, tags
- `**kwargs`: Additional parameters (e.g., `stream_mode`, `interrupt_before`)

**Returns**:
- Final output (usually a dict with "messages" key)

**LangGraph Pregel `ainvoke()` signature** (from actual code):
```python
async def ainvoke(
    self,
    input: InputT | Command | None,
    config: RunnableConfig | None = None,
    *,
    context: ContextT | None = None,
    stream_mode: StreamMode = 'values',
    print_mode: StreamMode | Sequence[StreamMode] = (),
    output_keys: str | Sequence[str] | None = None,
    interrupt_before: All | Sequence[str] | None = None,
    interrupt_after: All | Sequence[str] | None = None,
    durability: Durability | None = None,
    **kwargs: Any
) -> dict[str, Any] | Any
```

#### 4.1.2 `astream()` - Async Streaming

**Signature**:
```python
async def astream(
    self,
    input: Input,
    config: RunnableConfig | None = None,
    **kwargs: Any | None
) -> AsyncIterator[Output]
```

**Returns**:
- Async iterator yielding output chunks

**Usage**:
```python
async for chunk in graph.astream(...):
    # Process chunk
```

#### 4.1.3 `astream_events()` - Async Event Streaming

**Signature**:
```python
async def astream_events(
    self,
    input: Any,
    config: RunnableConfig | None = None,
    *,
    version: Literal['v1', 'v2'] = 'v2',
    include_names: Sequence[str] | None = None,
    include_types: Sequence[str] | None = None,
    include_tags: Sequence[str] | None = None,
    exclude_names: Sequence[str] | None = None,
    exclude_types: Sequence[str] | None = None,
    exclude_tags: Sequence[str] | None = None,
    **kwargs: Any
) -> AsyncIterator[StreamEvent]
```

**Event Types**:
- `on_chat_model_start`: Before LLM call
- `on_chat_model_stream`: Token streaming
- `on_chat_model_end`: After LLM completion
- `on_tool_start`: Before tool execution
- `on_tool_end`: After tool execution
- `on_chain_start/end`: Chain boundaries

**Event Structure**:
```python
{
    "event": "on_chat_model_stream",
    "name": "ChatOpenAI",
    "run_id": "...",
    "tags": [...],
    "metadata": {...},
    "data": {"chunk": MessageChunk(content="Hello")}
}
```

### 4.2 Migration Pattern 1: Convert `run()` to Async

**Before**:
```python
def run(self, prompt: str) -> KaiResult:
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]

    state = graph.invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)
    # ... rest of method
```

**After**:
```python
async def run(self, prompt: str) -> KaiResult:
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]

    # ASYNCHRONOUS CALL
    state = await graph.ainvoke(
        {"messages": messages},
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)
    # ... rest of method

    # For Ralph loop recursion, use await
    should_continue, next_prompt = self._ralph_hook.on_agent_complete(self, result)
    if should_continue and next_prompt:
        return await self.run(next_prompt)  # Add await

    return result
```

### 4.3 Migration Pattern 2: Convert `stream()` to Async

**Before**:
```python
def stream(self, prompt: str) -> Iterator[Any]:
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]
    last_snapshot = None

    try:
        for chunk in graph.stream(
            {"messages": messages},
            config={"configurable": {"thread_id": self._thread_id}},
            stream_mode="values",
        ):
            if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                last_snapshot = chunk
            yield chunk
    finally:
        if last_snapshot:
            self._update_from_state(last_snapshot)
```

**After**:
```python
from typing import AsyncIterator

async def stream(self, prompt: str) -> AsyncIterator[Any]:
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]
    last_snapshot = None

    try:
        # ASYNCHRONOUS STREAMING
        async for chunk in graph.astream(
            {"messages": messages},
            config={"configurable": {"thread_id": self._thread_id}},
            stream_mode="values",
        ):
            if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                last_snapshot = chunk
            yield chunk
    finally:
        if last_snapshot:
            self._update_from_state(last_snapshot)
```

### 4.4 Migration Pattern 3: Convert `resume()` to Async

**Before**:
```python
def resume(self, decisions: list[dict[str, Any]]) -> KaiResult:
    graph = self._build_graph()

    state = graph.invoke(
        Command(resume={"decisions": decisions}),
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)
    # ... rest of method
```

**After**:
```python
async def resume(self, decisions: list[dict[str, Any]]) -> KaiResult:
    graph = self._build_graph()

    # ASYNCHRONOUS CALL
    state = await graph.ainvoke(
        Command(resume={"decisions": decisions}),
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)
    # ... rest of method
```

### 4.5 Migration Pattern 4: Async Tool with Progress Streaming

**Before** (sync tool):
```python
@tool("process_data")
def process_data(data: str) -> str:
    """Process data without progress updates."""
    # Long-running operation
    result = do_something(data)
    return result
```

**After** (async tool with progress):
```python
from langchain.types import ToolRuntime
import asyncio

@tool
async def process_data(data: str, *, config: ToolRuntime) -> str:
    """Process data with progress updates."""
    steps = ["Loading...", "Processing...", "Saving..."]

    for i, step in enumerate(steps):
        # Emit progress events
        if config.writer:
            config.writer({
                "type": "progress",
                "id": f"step-{i}",
                "message": step,
                "progress": ((i + 1) / len(steps)) * 100,
            })

        # Simulate async work
        await asyncio.sleep(1)

    return '{"result": "Processing complete"}'
```

### 4.6 Migration Pattern 5: Async Tool with Callback Propagation

**For Python < 3.11** (explicit config passing required):

```python
from langchain_core.runnables import RunnableConfig

@tool
async def my_tool(input: str, *, config: RunnableConfig) -> str:
    """Async tool with proper callback propagation."""

    # Explicitly pass config to any async LangChain calls
    result = await some_model.ainvoke(
        [{"role": "user", "content": input}],
        config,  # CRITICAL: Pass config for callback propagation
    )

    return result.content
```

**For Python 3.11+** (automatic propagation):
```python
@tool
async def my_tool(input: str) -> str:
    """Async tool in Python 3.11+ with auto propagation."""

    # Config automatically propagated in 3.11+
    result = await some_model.ainvoke([{"role": "user", "content": input}])

    return result.content
```

---

## 5. Streaming Patterns

### 5.1 Stream Final Output (astream)

```python
async for chunk in graph.astream(
    {"messages": [{"role": "user", "content": prompt}]},
    config={"configurable": {"thread_id": thread_id}},
    stream_mode="values",  # Full state after each node
):
    # chunk contains the full state with messages
    messages = chunk.get("messages", [])
    if messages:
        last_message = messages[-1]
        print(f"Content: {last_message.content}")
```

**Stream Modes**:
- `"values"`: Full state after each step (default)
- `"updates"`: Only the node outputs (deltas)
- `"messages"`: Stream message tokens (for LLM responses)
- `"custom"`: Custom data from `StreamWriter`

### 5.2 Stream Intermediate Events (astream_events)

```python
async for event in graph.astream_events(
    {"messages": [{"role": "user", "content": prompt}]},
    config={"configurable": {"thread_id": thread_id}},
    version="v2",
):
    event_type = event["event"]

    if event_type == "on_chat_model_stream":
        # Token streaming from LLM
        chunk = event["data"]["chunk"]
        print(chunk.content, end="", flush=True)

    elif event_type == "on_tool_start":
        # Tool execution started
        print(f"Running tool: {event['name']}")

    elif event_type == "on_tool_end":
        # Tool execution finished
        print(f"Tool output: {event['data'].get('output')}")
```

### 5.3 Stream Message Tokens Only

```python
# Stream LLM tokens in real-time
async for message, metadata in graph.astream(
    {"messages": [{"role": "user", "content": prompt}]},
    config={"configurable": {"thread_id": thread_id}},
    stream_mode="messages",
):
    if message.content:
        print(message.content, end="|", flush=True)
```

---

## 6. Timeout Handling

### 6.1 Known Issues

**Current State (2025)**: LangChain has known issues with timeout handling in async contexts:
- GitHub Issue #32853: Async timeout support
- GitHub Issue #8279: Timeout propagation issues

### 6.2 Workaround: Async Timeout Wrapper

```python
import asyncio

async def run_with_timeout(graph, input_data, config, timeout_seconds=30):
    """Run agent with timeout using asyncio."""

    try:
        # Use asyncio.wait_for for timeout
        result = await asyncio.wait_for(
            graph.ainvoke(input_data, config),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        # Handle timeout
        return {"error": "Execution timed out"}
```

### 6.3 LangGraph Timeout Parameter (LangGraph 0.6+)

```python
# If using LangGraph 0.6+, you can pass timeout in config
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(
    configurable={"thread_id": thread_id},
    timeout=30.0  # seconds
)

result = await graph.ainvoke(input_data, config)
```

---

## 7. Compatibility Notes and Limitations

### 7.1 Python Version Requirements

| Python Version | Async Support | Notes |
|----------------|---------------|-------|
| **3.11+** (Recommended) | Full support | Automatic `RunnableConfig` propagation in async tasks |
| 3.10 | Partial support | Must explicitly pass `RunnableConfig` to async calls |
| 3.9 | Limited support | Context propagation limitations, may encounter issues |
| < 3.9 | Not recommended | Significant async compatibility issues |

### 7.2 RunnableConfig Propagation

**Python 3.11+**:
```python
@tool
async def my_tool(input: str) -> str:
    # Config auto-propagated
    return await model.ainvoke([{"role": "user", "content": input}])
```

**Python 3.10 and below**:
```python
@tool
async def my_tool(input: str, *, config: RunnableConfig) -> str:
    # Must explicitly pass config
    return await model.ainvoke(
        [{"role": "user", "content": input}],
        config  # CRITICAL
    )
```

### 7.3 Known Limitations

1. **Timeout Handling**: Native timeout support is incomplete; use `asyncio.wait_for()` as workaround
2. **Cancellation**: LangChain async operations may not handle cancellation gracefully
3. **Thread Safety**: Mixing sync and async code can cause thread safety issues
4. **Callback Propagation**: In Python < 3.11, callbacks don't automatically propagate in async tasks
5. **Memory Usage**: Async operations may use more memory due to pending coroutines

### 7.4 deepagents Compatibility

**Verified**: `deepagents` >=0.2.8 uses LangGraph under the hood, which supports async execution.

The `create_deep_agent()` function returns a `Pregel` graph that implements:
- `ainvoke()`
- `astream()`
- `astream_events()`

---

## 8. Performance Considerations

### 8.1 Async Overhead

**Measurement** (from LangChain docs):
- Tens of microseconds to few milliseconds overhead when delegating to sync methods
- Negligible for most I/O-bound operations
- Significant for CPU-bound operations (use `asyncio.to_thread()`)

### 8.2 Concurrency Benefits

Async enables:
- **Concurrent tool execution**: Multiple tools can run simultaneously
- **Streaming**: Real-time token delivery improves UX
- **Non-blocking**: Agent doesn't block during long-running operations

### 8.3 Best Practices

1. **Use async for I/O-bound operations**: File reads, network requests, subprocess calls
2. **Avoid async for CPU-bound work**: Use `asyncio.to_thread()` or process pool
3. **Stream when possible**: Improves perceived performance
4. **Limit concurrency**: Use `asyncio.Semaphore` to prevent resource exhaustion

---

## 9. Migration Checklist

### Phase 1: Preparation
- [ ] Verify Python version is 3.11+ (recommended)
- [ ] Update dependencies: `pip install -U langchain-core langchain langgraph`
- [ ] Run existing tests to establish baseline
- [ ] Create feature branch for async migration

### Phase 2: Core Methods
- [ ] Convert `run()` to `async def run()`
  - [ ] Replace `graph.invoke()` with `await graph.ainvoke()`
  - [ ] Add `await` to Ralph loop recursive call
- [ ] Convert `stream()` to `async def stream()`
  - [ ] Replace `for chunk in graph.stream()` with `async for chunk in graph.astream()`
  - [ ] Change return type to `AsyncIterator[Any]`
- [ ] Convert `resume()` to `async def resume()`
  - [ ] Replace `graph.invoke()` with `await graph.ainvoke()`

### Phase 3: Tool Migration
- [ ] Identify tools that can benefit from async
- [ ] Convert I/O-bound tools to async
  - [ ] File operations: use `aiofiles`
  - [ ] HTTP requests: use `httpx.AsyncClient`
  - [ ] Subprocess: use `asyncio.create_subprocess_exec`
- [ ] Add progress streaming to long-running tools
- [ ] Ensure proper callback propagation (especially Python < 3.11)

### Phase 4: CLI Integration
- [ ] Update CLI entry points to use `asyncio.run()`
- [ ] Update Rich UI to handle async streams
- [ ] Test interactive mode with async execution

### Phase 5: Testing
- [ ] Add `pytest-asyncio` to dev dependencies
- [ ] Write async tests for converted methods
- [ ] Test with real LLM providers
- [ ] Performance benchmark: sync vs async
- [ ] Load test with concurrent agents

### Phase 6: Documentation
- [ ] Update docstrings for async methods
- [ ] Add async examples to README
- [ ] Document breaking changes
- [ ] Update migration guide

---

## 10. Code Examples

### 10.1 Complete Async KaiAgent.run()

```python
async def run(self, prompt: str) -> KaiResult:
    """Run the agent with the given prompt (async version).

    If a Ralph loop is active, this method will re-feed the prompt
    recursively until the loop completes or safety limits are reached.

    Args:
        prompt: User prompt to execute.

    Returns:
        KaiResult with output, messages, and raw state.
    """
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]

    # ASYNCHRONOUS EXECUTION
    state = await graph.ainvoke(
        {"messages": messages},
        config={"configurable": {"thread_id": self._thread_id}},
    )

    self._update_from_state(state)

    # Extract output from last message
    output = ""
    if self._messages:
        last = self._messages[-1]
        if last.get("role") in ("assistant", "ai"):
            output = last.get("content") or ""
        else:
            output = last.get("content") or ""

    result = KaiResult(output=output, messages=list(self._messages), raw=state)

    # Ralph loop handling (async recursion)
    should_continue, next_prompt = self._ralph_hook.on_agent_complete(self, result)

    if should_continue and next_prompt:
        return await self.run(next_prompt)  # Add await for async recursion

    return result
```

### 10.2 Complete Async KaiAgent.stream()

```python
from typing import AsyncIterator

async def stream(self, prompt: str) -> AsyncIterator[Any]:
    """Stream agent execution (async version).

    Yields full state snapshots after each node execution.

    Args:
        prompt: User prompt to execute.

    Yields:
        State snapshots (dict with "messages" key).
    """
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]
    last_snapshot: dict[str, Any] | None = None

    try:
        # ASYNCHRONOUS STREAMING
        async for chunk in graph.astream(
            {"messages": messages},
            config={"configurable": {"thread_id": self._thread_id}},
            stream_mode="values",
        ):
            if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                last_snapshot = chunk
            yield chunk
    finally:
        # Persist final state
        if last_snapshot is not None:
            try:
                self._update_from_state(last_snapshot)
            except Exception:
                pass
```

### 10.3 Async Tool with Subprocess

```python
import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
async def execute_async(command: str, timeout: int = 30, *, config: RunnableConfig = None) -> str:
    """Execute shell command asynchronously with timeout.

    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds
        config: RunnableConfig for callback propagation

    Returns:
        JSON string with exit code and output, or timeout error
    """
    import json

    try:
        # Async subprocess execution
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(root_dir),
        )

        # Wait with timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )

        output = stdout.decode() + stderr.decode()
        return json.dumps({
            "exit_code": process.returncode,
            "output": output
        })

    except asyncio.TimeoutError:
        # Kill process on timeout
        try:
            process.kill()
            await process.wait()
        except:
            pass

        return json.dumps({
            "error": f"Command timed out after {timeout} seconds"
        })
```

### 10.4 Streaming with Events

```python
async def stream_with_events(self, prompt: str):
    """Stream agent execution with detailed events."""
    graph = self._build_graph()
    messages = list(self._messages) + [{"role": "user", "content": prompt}]

    # Stream all events
    async for event in graph.astream_events(
        {"messages": messages},
        config={"configurable": {"thread_id": self._thread_id}},
        version="v2",
    ):
        event_type = event["event"]
        event_name = event.get("name", "unknown")

        # Handle different event types
        if event_type == "on_chat_model_start":
            print(f"🤖 LLM starting: {event_name}")

        elif event_type == "on_chat_model_stream":
            # Token streaming
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content"):
                print(chunk.content, end="", flush=True)

        elif event_type == "on_chat_model_end":
            print()  # New line after streaming

        elif event_type == "on_tool_start":
            print(f"🔧 Tool starting: {event_name}")
            print(f"   Input: {event['data'].get('input')}")

        elif event_type == "on_tool_end":
            print(f"✅ Tool complete: {event_name}")
            print(f"   Output: {event['data'].get('output')[:100]}...")
```

---

## 11. Testing Strategy

### 11.1 Async Test Setup

**Install pytest-asyncio**:
```bash
pip install pytest-asyncio
```

**Configure pytest.ini**:
```ini
[pytest]
asyncio_mode = auto
```

### 11.2 Example Async Tests

```python
import pytest
from kai_code import KaiAgent

@pytest.mark.asyncio
async def test_agent_run_async(tmp_path):
    """Test async agent run."""
    agent = KaiAgent(
        root_dir=tmp_path,
        model="gpt-4o-mini",
        yolo=True,
    )

    result = await agent.run("Say 'Hello, async world!'")

    assert "Hello" in result.output.lower()
    assert len(result.messages) > 0

@pytest.mark.asyncio
async def test_agent_stream_async(tmp_path):
    """Test async agent streaming."""
    agent = KaiAgent(
        root_dir=tmp_path,
        model="gpt-4o-mini",
        yolo=True,
    )

    chunks = []
    async for chunk in agent.stream("Count to 5"):
        chunks.append(chunk)

    assert len(chunks) > 0

@pytest.mark.asyncio
async def test_concurrent_agents(tmp_path):
    """Test multiple agents running concurrently."""
    import asyncio

    async def run_agent(prompt):
        agent = KaiAgent(
            root_dir=tmp_path,
            model="gpt-4o-mini",
            yolo=True,
        )
        return await agent.run(prompt)

    # Run 3 agents concurrently
    results = await asyncio.gather(
        run_agent("Say 'A'"),
        run_agent("Say 'B'"),
        run_agent("Say 'C'"),
    )

    assert len(results) == 3
    for result in results:
        assert result.output
```

---

## 12. References

### 12.1 Official Documentation

1. **LangChain Async Programming**
   - URL: https://python.langchain.com/docs/concepts/async/
   - Topics: Async principles, callback propagation, Python version compatibility

2. **LangChain Streaming**
   - URL: https://python.langchain.com/docs/how_to/streaming/
   - Topics: `astream()`, `astream_events()`, stream modes

3. **LangGraph Streaming**
   - URL: https://langchain-ai.github.io/langgraph/how-tos/streaming/
   - Topics: Async streaming, token streaming, custom events

4. **LangGraph Async Execution**
   - URL: https://langchain-ai.github.io/langgraph/how-tos/async/
   - Topics: `ainvoke()`, `astream()`, state management

### 12.2 GitHub Repositories

1. **langchain-ai/langchain**
   - URL: https://github.com/langchain-ai/langchain
   - Relevant: Core async implementations, Runnable interface

2. **langchain-ai/langgraph**
   - URL: https://github.com/langchain-ai/langgraph
   - Relevant: Pregel async methods, checkpointing

3. **Context7 Code Examples**
   - Library ID: `/websites/langchain_oss_python` (13,592 code snippets)
   - Library ID: `/langchain-ai/langgraph` (254 code snippets)

### 12.3 Key Issues and Discussions

1. **GitHub Issue #32853**: Async timeout support
2. **GitHub Issue #8279**: Timeout propagation in async contexts
3. **LangChain v0.3 Release Notes**: Async improvements and breaking changes

---

## 13. Summary

### Key Takeaways

1. **LangChain has comprehensive async support**: All core methods have async equivalents with "a" prefix
2. **Migration is straightforward**: Replace `invoke()` with `await ainvoke()`, `stream()` with `async for/astream()`
3. **Python 3.11+ recommended**: Automatic callback propagation, fewer compatibility issues
4. **deepagents is compatible**: The `create_deep_agent()` function returns async-capable LangGraph graphs
5. **Timeout handling requires workarounds**: Use `asyncio.wait_for()` or LangGraph 0.6+ timeout parameter
6. **Streaming improves UX**: Use `astream_events()` for detailed progress, `astream()` for state updates

### Migration Path

1. **Start small**: Convert `run()` method first, test thoroughly
2. **Add streaming**: Convert `stream()` method, integrate with Rich UI
3. **Migrate tools**: Convert I/O-bound tools to async for better performance
4. **Update CLI**: Modify entry points to use `asyncio.run()`
5. **Test thoroughly**: Use `pytest-asyncio`, run integration tests
6. **Document changes**: Update README, add migration notes

### Expected Benefits

- **Improved concurrency**: Multiple agents can run simultaneously
- **Better UX**: Real-time streaming responses
- **Resource efficiency**: Non-blocking I/O operations
- **Future-proof**: Aligns with LangChain's async-first direction

---

**Document Version**: 1.0
**Last Updated**: 2025-01-23
**LangChain Version**: 1.1.2
**Python Version**: 3.11+

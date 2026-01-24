# LangChain Async Quick Reference

## Sync vs Async Method Mapping

| Sync Method | Async Method | Usage Example |
|-------------|--------------|---------------|
| `invoke(input, config)` | `ainvoke(input, config)` | `result = await graph.ainvoke(...)` |
| `stream(input, config)` | `astream(input, config)` | `async for chunk in graph.astream(...)` |
| `batch(inputs, config)` | `abatch(inputs, config)` | `results = await graph.abatch(...)` |
| `stream_events(...)` | `astream_events(...)` | `async for event in graph.astream_events(...)` |

## Common Patterns

### 1. Basic Async Execution

```python
# Before (sync)
def run(self, prompt: str) -> KaiResult:
    state = graph.invoke({"messages": messages}, config=config)
    return KaiResult(...)

# After (async)
async def run(self, prompt: str) -> KaiResult:
    state = await graph.ainvoke({"messages": messages}, config=config)
    return KaiResult(...)
```

### 2. Async Streaming

```python
# Before (sync)
def stream(self, prompt: str) -> Iterator[Any]:
    for chunk in graph.stream(input, config=config):
        yield chunk

# After (async)
async def stream(self, prompt: str) -> AsyncIterator[Any]:
    async for chunk in graph.astream(input, config=config):
        yield chunk
```

### 3. Async Tool

```python
from langchain_core.tools import tool

@tool
async def my_async_tool(input: str) -> str:
    """Tool description."""
    # Async I/O operation
    result = await some_async_operation(input)
    return result
```

### 4. RunnableConfig Propagation

```python
# Python 3.11+ (automatic)
@tool
async def tool_auto(input: str) -> str:
    return await model.ainvoke([{"role": "user", "content": input}])

# Python < 3.11 (explicit)
from langchain_core.runnables import RunnableConfig

@tool
async def tool_explicit(input: str, *, config: RunnableConfig) -> str:
    return await model.ainvoke(
        [{"role": "user", "content": input}],
        config  # Must pass explicitly
    )
```

### 5. Timeout Handling

```python
import asyncio

# Using asyncio.wait_for
try:
    result = await asyncio.wait_for(
        graph.ainvoke(input, config),
        timeout=30.0
    )
except asyncio.TimeoutError:
    # Handle timeout
    pass

# Using LangGraph 0.6+ timeout parameter
config = RunnableConfig(
    configurable={"thread_id": thread_id},
    timeout=30.0
)
result = await graph.ainvoke(input, config)
```

## Stream Modes

```python
# Stream full state
async for state in graph.astream(input, stream_mode="values"):
    print(state["messages"])

# Stream node outputs only
async for update in graph.astream(input, stream_mode="updates"):
    print(update)

# Stream message tokens
async for token, metadata in graph.astream(input, stream_mode="messages"):
    print(token.content, end="")

# Stream custom data
async for custom in graph.astream(input, stream_mode="custom"):
    print(custom)
```

## Event Streaming

```python
async for event in graph.astream_events(input, version="v2"):
    event_type = event["event"]

    if event_type == "on_chat_model_stream":
        # LLM token
        chunk = event["data"]["chunk"]
        print(chunk.content, end="")

    elif event_type == "on_tool_start":
        # Tool started
        print(f"Running: {event['name']}")

    elif event_type == "on_tool_end":
        # Tool finished
        print(f"Output: {event['data']['output']}")
```

## CLI Integration

```python
import asyncio

def cli_main():
    """CLI entry point with async support."""
    agent = KaiAgent(root_dir=".")

    # Run async code
    result = asyncio.run(agent.run("Hello"))

    # Or for streaming
    async def stream_and_print():
        async for chunk in agent.stream("Hello"):
            print(chunk)

    asyncio.run(stream_and_print())
```

## Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_agent():
    agent = KaiAgent(root_dir=tmp_path)
    result = await agent.run("Test")
    assert result.output
```

## Common Mistakes

❌ **Don't**: Forget `await` with async methods
```python
result = graph.ainvoke(input)  # Returns coroutine!
```

✅ **Do**: Use `await` to get the result
```python
result = await graph.ainvoke(input)  # Returns actual result
```

❌ **Don't**: Mix sync and async calls
```python
async def bad():
    result = graph.invoke(input)  # Blocks event loop!
```

✅ **Do**: Use async consistently
```python
async def good():
    result = await graph.ainvoke(input)  # Non-blocking
```

❌ **Don't**: Forget async iteration syntax
```python
for chunk in graph.astream(input):  # TypeError!
```

✅ **Do**: Use `async for`
```python
async for chunk in graph.astream(input):  # Correct
```

## Python Version Compatibility

| Feature | 3.11+ | 3.10 | 3.9 |
|---------|-------|------|-----|
| Basic async | ✅ | ✅ | ⚠️ |
| Config propagation | ✅ Auto | ⚠️ Manual | ⚠️ Manual |
| Context vars | ✅ | ⚠️ Limited | ❌ |
| Recommended | ✅ Yes | ⚠️ Works | ❌ No |

## Key Imports

```python
# Core async support
from langchain_core.runnables import Runnable, RunnableConfig

# Async tools
from langchain_core.tools import tool
from langchain.types import ToolRuntime

# Async iteration
from typing import AsyncIterator, AsyncGenerator

# Async utilities
import asyncio
```

## Performance Tips

1. **Use async for I/O**: Network, file, subprocess operations
2. **Stream when possible**: Improves perceived performance
3. **Limit concurrency**: Use `asyncio.Semaphore` for rate limiting
4. **Avoid CPU-bound in async**: Use `asyncio.to_thread()` instead
5. **Profile before optimizing**: Measure actual bottlenecks

## Debugging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use async debugger
import pdb; pdb.set_async()  # Python 3.12+

# Or use breakpoint()
async def debug_me():
    breakpoint()  # Works in async code
    result = await graph.ainvoke(input)
```

---

**For detailed information**, see: `docs/LANGCHAIN_ASYNC_MIGRATION_GUIDE.md`

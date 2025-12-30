import json
import time
import uuid
from typing import Any, Dict, Generator, List, Optional, Union

class StreamEvent:
    """Base class for stream events."""
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

class InitEvent(StreamEvent):
    def __init__(self, run_id: Optional[str] = None):
        self.type = "init"
        self.id = run_id or str(uuid.uuid4())
        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

class MessageEvent(StreamEvent):
    def __init__(self, content: str, delta: bool = True, index: int = 0):
        self.type = "message"
        self.content = content
        self.delta = delta
        self.index = index

class ToolCallEvent(StreamEvent):
    def __init__(self, name: str, arguments: str, call_id: Optional[str] = None):
        self.type = "tool_call"
        self.name = name
        self.arguments = arguments
        self.id = call_id or str(uuid.uuid4())

class ToolResultEvent(StreamEvent):
    def __init__(self, result: str, call_id: str):
        self.type = "tool_result"
        self.result = result
        self.id = call_id

class ErrorEvent(StreamEvent):
    def __init__(self, message: str, code: int = 500):
        self.type = "error"
        self.message = message
        self.code = code

class ResultEvent(StreamEvent):
    def __init__(self, output: Any, stats: Optional[Dict[str, Any]] = None):
        self.type = "result"
        self.output = output
        self.stats = stats or {}

class StreamProcessor:
    """
    Processes raw chunks from deepagents/langgraph and converts them 
    into a stable JSONL schema.
    """
    def __init__(self):
        self.start_time = time.time()
        self.chunk_count = 0
        self._emitted_init = False

    def process(self, chunk: Any) -> Generator[str, None, None]:
        """
        Takes a raw chunk and yields JSONL formatted strings.
        """
        if not self._emitted_init:
            yield InitEvent().to_json()
            self._emitted_init = True

        self.chunk_count += 1
        
        # Best-effort mapping logic
        try:
            for event in self._map_chunk_to_events(chunk):
                yield event.to_json()
        except Exception as e:
            yield ErrorEvent(f"Failed to process chunk: {str(e)}").to_json()

    def finalize(self, final_output: Any) -> str:
        """
        Emits the final result event with stats.
        """
        stats = {
            "chunk_count": self.chunk_count,
            "latency_ms": int((time.time() - self.start_time) * 1000)
        }
        return ResultEvent(final_output, stats).to_json()

    def _map_chunk_to_events(self, chunk: Any) -> Generator[StreamEvent, None, None]:
        """
        Maps a raw chunk (dict or object) to StreamEvents.
        """
        # Scenario 1: LangGraph-like dict with 'messages'
        if isinstance(chunk, dict) and "messages" in chunk:
            messages = chunk["messages"]
            if isinstance(messages, list):
                for msg in messages:
                    # Check for content (delta or full)
                    content = getattr(msg, "content", None) or chunk.get("content")
                    if content:
                         yield MessageEvent(content=content)
                    
                    # Check for tool calls
                    tool_calls = getattr(msg, "tool_calls", None) or chunk.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            # Handle LangChain/LangGraph ToolCall object or dict
                            if isinstance(tc, dict):
                                yield ToolCallEvent(
                                    name=tc.get("name", "unknown"),
                                    arguments=json.dumps(tc.get("args", {})) if isinstance(tc.get("args"), dict) else str(tc.get("args", "")),
                                    call_id=tc.get("id")
                                )
                            else:
                                # Assume object attributes
                                yield ToolCallEvent(
                                    name=getattr(tc, "name", "unknown"),
                                    arguments=str(getattr(tc, "args", "")),
                                    call_id=getattr(tc, "id", None)
                                )

        # Scenario 2: Simple text delta (string)
        elif isinstance(chunk, str):
            yield MessageEvent(content=chunk)

        # Scenario 3: Dict with 'chunk' key (common in some streams)
        elif isinstance(chunk, dict) and "chunk" in chunk:
             yield MessageEvent(content=str(chunk["chunk"]))
             
        # Scenario 4: Tool output/result
        elif isinstance(chunk, dict) and "tool_output" in chunk:
             yield ToolResultEvent(result=str(chunk["tool_output"]), call_id=chunk.get("id", "unknown"))

        # Fallback: Wrap raw chunk in a generic message or debug event if needed
        # For now, we'll try to extract 'content' if it exists in a generic dict
        elif isinstance(chunk, dict):
            if "content" in chunk:
                yield MessageEvent(content=str(chunk["content"]))
            else:
                 # If we can't identify it, maybe ignore or log? 
                 # The prompt says: "wrap raw chunk under event fields while keeping schema stable"
                 # Let's verify if we should wrap unknown stuff.
                 # "otherwise wrap raw chunk under event fields"
                 # We'll use a message event with non-delta or a specific type?
                 # Let's stick to MessageEvent but maybe stringify the whole dict?
                 # Or better, just ignore if it doesn't fit specific categories to avoid noise, 
                 # BUT the instruction says "wrap raw chunk".
                 # Let's wrap it in a 'raw' field of a message or custom type?
                 # Re-reading: "wrap raw chunk under event fields while keeping schema stable"
                 # I will assume this means putting it in a generic event or extending the schema slightly?
                 # I'll put it in 'data' of a generic message for now, or just json dump it as content.
                 yield MessageEvent(content=json.dumps(chunk), delta=False)
        else:
             yield MessageEvent(content=str(chunk), delta=False)

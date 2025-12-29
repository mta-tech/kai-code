"""Streaming conversation manager for multi-turn conversations.

Based on letta-code's approach with enhancements for kai-code.
"""

from __future__ import annotations

import logging
import asyncio
import uuid
from typing import AsyncIterator, Dict, List, Any, Optional, Tuple, Callable
from enum import Enum
from datetime import datetime

from ..agent import KaiAgent
from ..permissions import PermissionConfig

logger = logging.getLogger("kai_code.rich_ui")


class StreamEvent:
    """Single streaming event from agent."""
    
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now()
        self.id = str(uuid.uuid4())


class ConversationPhase(Enum):
    """Phases of conversation turn processing."""
    STARTING = "starting"
    STREAMING = "streaming"
    TOOL_EXECUTION = "tool_execution"
    APPROVAL_REQUIRED = "approval_required"
    COMPLETED = "completed"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class ConversationState:
    """State tracking for conversation."""
    
    def __init__(self):
        self.current_turn: int = 0
        self.messages: List[Dict[str, Any]] = []
        self.tool_results: List[Dict[str, Any]] = []
        self.approvals_pending: List[Dict[str, Any]] = []
        self.current_phase: ConversationPhase = ConversationPhase.STARTING
        self.context: Dict[str, Any] = {}
        self.interrupted: bool = False


class StreamingConversationManager:
    """Manages streaming multi-turn conversations.
    
    Based on letta-code's processConversation function with enhancements.
    """
    
    def __init__(self, agent: KaiAgent, permissions: Optional[PermissionConfig] = None):
        self.agent = agent
        self.permissions = permissions
        self.state = ConversationState()
        self.event_handlers: List[Callable[[StreamEvent], None]] = []
        
        # Streaming control
        self.abort_controller = Optional[None]
        self.current_stream = None
        
    def add_event_handler(self, handler: Callable[[StreamEvent], None]) -> None:
        """Add event handler for streaming updates."""
        self.event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable[[StreamEvent], None]) -> None:
        """Remove event handler."""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event to all handlers."""
        event = StreamEvent(event_type, data)
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def process_turn(self, user_message: str) -> AsyncIterator[StreamEvent]:
        """Process a single conversation turn with streaming updates."""
        
        # Reset turn state
        self.state.current_turn += 1
        self.state.current_phase = ConversationPhase.STARTING
        self.state.interrupted = False
        self.abort_controller = asyncio.CancelEvent()
        
        try:
            # Emit user message event
            self._emit_event("user_message", {
                "message": user_message,
                "turn": self.state.current_turn
            })
            
            # Add user message to conversation history
            self.state.messages.append({
                "type": "user",
                "text": user_message,
                "turn": self.state.current_turn,
                "timestamp": datetime.now().isoformat()
            })
            
            # Start processing turn
            self.state.current_phase = ConversationPhase.STREAMING
            
            # Process message through agent
            async for event in self._stream_agent_response(user_message):
                yield event
                
        except asyncio.CancelledError:
            # Handle interruption
            self.state.current_phase = ConversationPhase.INTERRUPTED
            self.state.interrupted = True
            self._emit_event("conversation_interrupted", {
                "turn": self.state.current_turn,
                "reason": "User cancelled"
            })
            
        except Exception as e:
            # Handle errors
            self.state.current_phase = ConversationPhase.ERROR
            logger.error(f"Error in conversation turn {self.state.current_turn}: {e}")
            
            self._emit_event("conversation_error", {
                "turn": self.state.current_turn,
                "error": str(e),
                "traceback": str(e.__traceback__)
            })
        
        finally:
            # Clean up
            self.abort_controller = None
            self.current_stream = None
    
    async def _stream_agent_response(self, user_message: str) -> AsyncIterator[StreamEvent]:
        """Stream agent response with turn processing.
        
        Based on letta-code's iterative conversation loop.
        """
        current_input = [{"type": "message", "content": user_message}]
        
        while True:
            try:
                # Stream one turn from agent
                async for chunk in self._stream_agent_chunk(current_input):
                    self._emit_event("agent_chunk", {
                        "chunk": chunk,
                        "turn": self.state.current_turn
                    })
                    
                    # Process the chunk
                    stop_reason = await self._process_agent_chunk(chunk)
                    
                    if stop_reason:
                        # Handle different stop reasons
                        if stop_reason == "end_turn":
                            self.state.current_phase = ConversationPhase.COMPLETED
                            self._emit_event("turn_completed", {
                                "turn": self.state.current_turn
                            })
                            return
                            
                        elif stop_reason == "cancelled":
                            self.state.current_phase = ConversationPhase.INTERRUPTED
                            self._emit_event("turn_cancelled", {
                                "turn": self.state.current_turn
                            })
                            return
                            
                        elif stop_reason == "requires_approval":
                            self.state.current_phase = ConversationPhase.APPROVAL_REQUIRED
                            await self._handle_approvals()
                            # Continue with approved results
                            current_input = self._build_approval_input()
                            break
                            
                        else:
                            # Unknown stop reason, end turn
                            self.state.current_phase = ConversationPhase.COMPLETED
                            self._emit_event("turn_completed", {
                                "turn": self.state.current_turn,
                                "stop_reason": stop_reason
                            })
                            return
                
            except Exception as e:
                logger.error(f"Error in agent streaming: {e}")
                self._emit_event("stream_error", {
                    "error": str(e),
                    "turn": self.state.current_turn
                })
                break
    
    async def _stream_agent_chunk(self, input_data: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        """Stream agent response chunks."""
        
        # This would integrate with agent's streaming capability
        # For now, simulate streaming response
        
        message_content = ""
        
        try:
            # Call agent to get response
            response = await self._get_agent_response(input_data)
            
            # Simulate streaming by yielding chunks
            if isinstance(response, str):
                # Simple text response - simulate character streaming
                words = response.split()
                current_text = ""
                
                for i, word in enumerate(words):
                    current_text += word
                    if i < len(words) - 1:
                        current_text += " "
                    
                    yield {
                        "type": "assistant_chunk",
                        "content": current_text,
                        "phase": "streaming"
                    }
                    
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.01)
            else:
                # Tool call or structured response
                yield response
                
        except Exception as e:
            logger.error(f"Error in agent chunk streaming: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "phase": "error"
            }
    
    async def _get_agent_response(self, input_data: List[Dict[str, Any]]) -> Any:
        """Get response from agent."""
        
        # Extract message content
        messages = [msg.get("content", "") for msg in input_data if msg.get("type") == "message"]
        user_message = messages[0] if messages else ""
        
        # Get agent response
        # This would integrate with KaiAgent's invoke method
        # For now, return a simulated response
        
        if user_message.lower().startswith("test"):
            return "This is a test response from the agent."
        elif "help" in user_message.lower():
            return "I can help you with various tasks. What would you like to do?"
        elif "error" in user_message.lower():
            raise Exception("Simulated error for testing")
        else:
            return f"I received your message: '{user_message}'. How can I assist you further?"
    
    async def _process_agent_chunk(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Process agent chunk and determine stop reason."""
        
        chunk_type = chunk.get("type", "unknown")
        phase = chunk.get("phase", "unknown")
        
        # Emit chunk event
        self._emit_event("chunk_processed", {
            "chunk": chunk,
            "turn": self.state.current_turn
        })
        
        # Determine if we should stop streaming
        if phase == "error":
            return "error"
        elif chunk_type == "assistant_chunk" and phase != "streaming":
            return "end_turn"
        elif chunk_type == "tool_call":
            # Tool calls require approval based on permissions
            tool_name = chunk.get("tool_name", "")
            if self._requires_approval(tool_name):
                return "requires_approval"
            else:
                # Auto-execute tool
                return None  # Continue streaming
        elif chunk_type == "tool_result":
            # Tool completed, continue
            return None
        
        # Default - continue streaming
        return None
    
    def _requires_approval(self, tool_name: str) -> bool:
        """Check if tool requires approval."""
        if not self.permissions:
            return True  # Default to requiring approval
        
        # Check permission configuration
        return self.permissions.tool_required(tool_name)
    
    async def _handle_approvals(self) -> None:
        """Handle pending tool approvals."""
        
        self._emit_event("approvals_pending", {
            "tools": self.state.approvals_pending,
            "turn": self.state.current_turn
        })
        
        # Wait for approval results
        # This would integrate with Rich UI approval dialog
        # For now, auto-approve for testing
        approval_results = []
        for tool_call in self.state.approvals_pending:
            approval_results.append({
                "tool_name": tool_call.get("tool_name"),
                "approved": True,
                "reason": "Auto-approved for testing"
            })
        
        self.state.approvals_pending = []
        
        self._emit_event("approvals_completed", {
            "results": approval_results,
            "turn": self.state.current_turn
        })
    
    def _build_approval_input(self) -> List[Dict[str, Any]]:
        """Build input for next turn after approvals."""
        
        # Include approval results as tool returns
        approval_inputs = []
        for result in self.state.tool_results:
            if result.get("from_approval"):
                approval_inputs.append({
                    "type": "tool_return",
                    "tool_call_id": result.get("tool_call_id"),
                    "tool_return": result.get("tool_return")
                })
        
        return approval_inputs
    
    def interrupt(self) -> None:
        """Interrupt current conversation turn."""
        if self.abort_controller:
            self.abort_controller.set()
            self.state.interrupted = True
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get complete conversation history."""
        return self.state.messages.copy()
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return {
            "turn": self.state.current_turn,
            "phase": self.state.current_phase.value,
            "message_count": len(self.state.messages),
            "tool_results_count": len(self.state.tool_results),
            "interrupted": self.state.interrupted,
            "context": self.state.context.copy()
        }
    
    def reset_conversation(self) -> None:
        """Reset conversation state."""
        self.state = ConversationState()
        self._emit_event("conversation_reset", {})

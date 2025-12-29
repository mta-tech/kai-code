"""Main Rich UI application.

Enhanced with streaming conversation management from letta-code.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..agent import KaiAgent
from .console import RichConsoleManager
from .input_handler import RichInputHandler
from .message_formatter import MessageFormatter
from .components import RichStatusBar, MessageDisplay, ToolDisplay, ApprovalDialog
from .conversation_manager import StreamingConversationManager, StreamEvent

logger = logging.getLogger("kai_code.rich_ui")


class KaiRichApp:
    """Rich-based interactive UI application."""
    
    def __init__(
        self,
        root_dir: str | Path = ".",
        model: str = "default",
        session: str = "default",
        yolo: bool = True,
    ):
        self.root_dir = Path(root_dir).resolve()
        self.model = model
        self.session = session
        self.yolo = yolo
        self.running = True
        
        # Initialize components
        self.console_manager = RichConsoleManager()
        self.input_handler = RichInputHandler()
        self.message_formatter = MessageFormatter(self.console_manager.console)
        
        # UI components
        self.status_bar = RichStatusBar(model, session, yolo)
        self.message_display = MessageDisplay(self.console_manager.console)
        self.tool_display = ToolDisplay()
        self.approval_dialog = ApprovalDialog(self.console_manager.console)
        
        # Agent and conversation manager
        self.agent: Optional[KaiAgent] = None
        self.conversation_manager: Optional[StreamingConversationManager] = None
        
        # Conversation state
        self.current_messages: List[Dict[str, Any]] = []
        self.streaming: bool = False
        self.interrupt_requested: bool = False
        
        # Context for command handling
        self.command_context = {
            "print_error": self.console_manager.print_error,
            "print_info": self.console_manager.print_info,
            "print_success": self.console_manager.print_success,
            "clear_messages": self.message_display.clear_messages,
            "agent": None,  # Will be set when agent is created
            "app": self,
        }
    
    def initialize_agent(self) -> bool:
        """Initialize the AI agent."""
        try:
            # Resolve model name
            model = self.model
            if model == "default":
                from ..model import get_default_model
                model = get_default_model()
            
            logger.debug(f"Creating agent with model={model}, yolo={self.yolo}")
            
            self.agent = KaiAgent(
                root_dir=self.root_dir,
                model=model,
                yolo=self.yolo,
            )
            
            # Update command context with agent
            self.command_context["agent"] = self.agent
            
            # Initialize conversation manager
            self.conversation_manager = StreamingConversationManager(
                agent=self.agent,
                permissions=getattr(self.agent, '_permissions', None)
            )
            
            # Set up event handlers for streaming
            self.conversation_manager.add_event_handler(self._handle_stream_event)
            
            # Update status bar with resolved model
            self.status_bar.update_model(model)
            
            logger.info("Agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            self.console_manager.print_error(f"Failed to initialize agent: {e}")
            return False
    
    def run(self):
        """Run the interactive Rich UI."""
        logger.info("Starting Kai Rich UI")
        
        # Initialize agent
        if not self.initialize_agent():
            return
        
        # Display welcome message
        self.console_manager.print_info(
            f"Welcome to Kai Code! (Model: {self.status_bar.model}, Session: {self.session})"
        )
        self.console_manager.print_info("Type /help for commands or just start chatting.")
        
        # Initial render
        self.update_display()
        
        # Main interaction loop
        try:
            while self.running:
                try:
                    # Get user input
                    user_input = self.input_handler.get_input("kai> ")
                    
                    # Check for slash commands
                    if self.input_handler.is_slash_command(user_input):
                        command, args = self.input_handler.parse_command(user_input)
                        should_exit = self.input_handler.execute_command(
                            command, args, self.command_context
                        )
                        if should_exit:
                            self.running = False
                        continue
                    
                    # Send message to agent
                    if user_input.strip():
                        self._handle_user_message(user_input)
                        
                except KeyboardInterrupt:
                    self.console_manager.print_info("\nUse /quit to exit or /help for commands.")
                except EOFError:
                    self.console_manager.print_info("\nGoodbye!")
                    break
                    
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.console_manager.print_error(f"Unexpected error: {e}")
        
        finally:
            # Clean up
            if hasattr(self.console_manager, 'live') and self.console_manager.live:
                self.console_manager.stop_live_display()
    
    def update_display(self):
        """Update the entire display."""
        # Update layout panels
        self.console_manager.update_header(self.status_bar.render())
        self.console_manager.update_messages(self.message_display.render())
        self.console_manager.update_tools(self.tool_display.render())
        
        # Update footer with hints
        footer_content = "[dim]Type /help for commands • Ctrl+C to interrupt[/dim]"
        self.console_manager.update_footer(footer_content)
    
    def _handle_user_message(self, message: str):
        """Handle a message from the user."""
        if not self.agent:
            self.console_manager.print_error("No agent available")
            return

        # Print user message echo
        self.console_manager.console.print(f"[dim]You:[/dim] {message}")

        try:
            # Stream response from agent - print directly to console
            self.console_manager.console.print("[cyan]Assistant:[/cyan] ", end="")

            assistant_message = ""
            has_response = False

            for chunk in self._stream_agent_response(message):
                has_response = True
                assistant_message += chunk
                # Print chunk directly (streaming effect)
                self.console_manager.console.print(chunk, end="")

            # End the assistant message line
            self.console_manager.console.print()

            # If no response was received, show a message
            if not has_response:
                self.console_manager.console.print("[yellow](No response from agent)[/yellow]")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    async def _handle_conversation_turn(self, user_input: str) -> None:
        """Handle conversation turn with streaming support."""
        
        # Add user message to display
        user_panel = self.message_display.render_user_message(user_input)
        self.current_messages.append({
            "type": "user",
            "text": user_input,
            "panel": user_panel
        })
        
        # Update display
        self.update_display()
        
        # Start streaming
        self.streaming = True
        self.interrupt_requested = False
        
        try:
            # Process turn through conversation manager
            if self.conversation_manager:
                async for event in self.conversation_manager.process_turn(user_input):
                    await self._handle_stream_event(event)
            else:
                # Fallback to non-streaming handler
                self._handle_user_message(user_input)
                
        except Exception as e:
            logger.error(f"Error in conversation turn: {e}")
            error_panel = self.message_display.render_error(str(e))
            self.current_messages.append({
                "type": "error",
                "text": str(e),
                "panel": error_panel
            })
        
        finally:
            # End streaming
            self.streaming = False
            self.update_display()
    
    async def _handle_stream_event(self, event) -> None:
        """Handle streaming event from conversation manager."""
        
        event_type = event.event_type
        data = event.data
        
        if event_type == "user_message":
            # User message already handled
            pass
            
        elif event_type == "agent_chunk":
            # Agent streaming chunk
            chunk = data.get("chunk", {})
            chunk_type = chunk.get("type", "unknown")
            
            if chunk_type == "assistant_chunk":
                content = chunk.get("content", "")
                panel = self.message_display.render_assistant_message(
                    content, 
                    streaming=True
                )
                
                # Update or add message
                self._update_assistant_message(panel)
                
            elif chunk_type == "tool_call":
                tool_name = chunk.get("tool_name", "")
                args = chunk.get("args", {})
                phase = chunk.get("phase", "ready")
                
                panel = self.message_display.render_tool_call(
                    tool_name, args, phase
                )
                
                self.current_messages.append({
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "args": args,
                    "phase": phase,
                    "panel": panel
                })
                
            elif chunk_type == "tool_result":
                tool_name = chunk.get("tool_name", "")
                result = chunk.get("result", "")
                success = chunk.get("success", True)
                
                panel = self.message_display.render_tool_result(
                    tool_name, result, success
                )
                
                self.current_messages.append({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": result,
                    "success": success,
                    "panel": panel
                })
                
        elif event_type == "turn_completed":
            # Turn completed
            self._finalize_assistant_message()
            
        elif event_type == "approvals_pending":
            # Handle tool approvals
            tools = data.get("tools", [])
            if tools:
                self._handle_approvals(tools)
            
        elif event_type == "conversation_error":
            error_msg = data.get("error", "Unknown error")
            error_panel = self.message_display.render_error(error_msg)
            self.current_messages.append({
                "type": "error",
                "text": error_msg,
                "panel": error_panel
            })
        
        # Update display for real-time updates
        if self.streaming:
            self.update_display()
    
    def _update_assistant_message(self, new_panel) -> None:
        """Update or add assistant message panel."""
        
        # Find existing assistant message
        for i, msg in enumerate(self.current_messages):
            if msg.get("type") == "assistant" and msg.get("streaming"):
                self.current_messages[i] = {
                    "type": "assistant",
                    "text": new_panel.title,
                    "panel": new_panel,
                    "streaming": True
                }
                return
        
        # Add new assistant message
        self.current_messages.append({
            "type": "assistant",
            "text": new_panel.title,
            "panel": new_panel,
            "streaming": True
        })
    
    def _finalize_assistant_message(self) -> None:
        """Finalize streaming assistant message."""
        
        for i, msg in enumerate(self.current_messages):
            if msg.get("type") == "assistant" and msg.get("streaming"):
                # Update to non-streaming
                self.current_messages[i] = {
                    **msg,
                    "streaming": False
                }
                return
    
    def _handle_approvals(self, tools) -> None:
        """Handle tool approvals."""
        
        if not tools:
            return
        
        # Show approval dialog
        try:
            approvals, reasons = self.approval_dialog.show_batch_approval_dialog(tools)
            
            # Submit approval results back to conversation manager
            # This would integrate with conversation manager
            logger.debug(f"Approval results: {approvals}")
            
        except Exception as e:
            logger.error(f"Error in approval handling: {e}")
            error_panel = self.message_display.render_error(f"Approval error: {e}")
            self.current_messages.append({
                "type": "error",
                "text": f"Approval error: {e}",
                "panel": error_panel
            })
    
    def _interrupt_conversation(self) -> None:
        """Interrupt current conversation."""
        if self.conversation_manager:
            self.conversation_manager.interrupt()
        self.interrupt_requested = True
        self.streaming = False
    
    def _stream_agent_response(self, prompt: str):
        """Stream response from agent.

        Yields delta content (new text since last yield) from the agent's streaming response.
        Only yields AI/assistant messages, not user messages or tool results.
        """
        def _is_ai_message(msg: object) -> bool:
            if isinstance(msg, dict):
                return msg.get("role") in ("assistant", "ai")

            name = type(msg).__name__
            # LangChain message objects (AIMessage / AIMessageChunk)
            return name.startswith("AIMessage") or "AIMessage" in name

        def _get_content(msg: object) -> str:
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = getattr(msg, "content", "")

            # Some message implementations can store structured content.
            if content is None:
                return ""
            if isinstance(content, str):
                return content
            # LangChain can represent content as a list of parts, e.g.
            # [{"type": "text", "text": "..."}, ...]
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        text = part.get("text")
                        if isinstance(text, str):
                            parts.append(text)
                return "".join(parts)
            try:
                return str(content)
            except Exception:
                return ""

        last_ai_content = ""
        chunk_count = 0
        last_snapshot: dict | None = None

        try:
            logger.debug(f"Starting agent.stream() with prompt: {prompt[:50]}...")
            for chunk in self.agent.stream(prompt):
                chunk_count += 1
                chunk_keys = chunk.keys() if isinstance(chunk, dict) else "N/A"
                logger.debug(f"Chunk #{chunk_count}: type={type(chunk)}, keys={chunk_keys}")

                # Track snapshot with messages for final extraction
                if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                    last_snapshot = chunk
                    messages = chunk.get("messages", [])

                    # Find the most recent AI message in the snapshot (the last message
                    # is often a tool/human message during execution).
                    ai_msg = next((m for m in reversed(messages) if _is_ai_message(m)), None)
                    if ai_msg is None:
                        continue

                    content = _get_content(ai_msg)
                    if content:
                        logger.debug(f"AI content: {repr(content[:100])}")

                    # Yield only the delta (new content)
                    if content and content != last_ai_content:
                        if content.startswith(last_ai_content):
                            delta = content[len(last_ai_content):]
                            if delta:
                                logger.debug(f"Yielding delta: {repr(delta[:50])}")
                                yield delta
                        else:
                            logger.debug(f"Yielding full content: {repr(content[:50])}")
                            # If the model restarts the assistant message (new message vs append),
                            # keep output readable.
                            yield ("\n" + content) if last_ai_content else content
                        last_ai_content = content

            logger.debug(f"Stream ended. Total chunks: {chunk_count}")

            # If no AI content was yielded during streaming, try final snapshot
            if not last_ai_content and last_snapshot:
                logger.debug("No AI content yielded during stream, extracting from final snapshot")
                msgs = last_snapshot.get("messages", [])
                ai_msg = next((m for m in reversed(msgs) if _is_ai_message(m)), None)
                if ai_msg is not None:
                    content = _get_content(ai_msg)
                    if content:
                        logger.debug(f"Final AI content: {repr(content[:100])}")
                        yield content

        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    async def _handle_conversation_turn(self, user_input: str) -> None:
        """Handle conversation turn with streaming support."""
        
        # Add user message to display
        user_panel = self.message_display.render_user_message(user_input)
        self.current_messages.append({
            "type": "user",
            "text": user_input,
            "panel": user_panel
        })
        
        # Update display
        self.update_display()
        
        # Start streaming
        self.streaming = True
        self.interrupt_requested = False
        
        try:
            # Process turn through conversation manager
            if self.conversation_manager:
                async for event in self.conversation_manager.process_turn(user_input):
                    await self._handle_stream_event(event)
            else:
                # Fallback to non-streaming handler
                self._handle_user_message(user_input)
                
        except Exception as e:
            logger.error(f"Error in conversation turn: {e}")
            error_panel = self.message_display.render_error(str(e))
            self.current_messages.append({
                "type": "error",
                "text": str(e),
                "panel": error_panel
            })
        
        finally:
            # End streaming
            self.streaming = False
            self.update_display()
    
    async def _handle_stream_event(self, event) -> None:
        """Handle streaming event from conversation manager."""
        
        event_type = event.event_type
        data = event.data
        
        if event_type == "user_message":
            # User message already handled
            pass
            
        elif event_type == "agent_chunk":
            # Agent streaming chunk
            chunk = data.get("chunk", {})
            chunk_type = chunk.get("type", "unknown")
            
            if chunk_type == "assistant_chunk":
                content = chunk.get("content", "")
                panel = self.message_display.render_assistant_message(
                    content, 
                    streaming=True
                )
                
                # Update or add message
                self._update_assistant_message(panel)
                
            elif chunk_type == "tool_call":
                tool_name = chunk.get("tool_name", "")
                args = chunk.get("args", {})
                phase = chunk.get("phase", "ready")
                
                panel = self.message_display.render_tool_call(
                    tool_name, args, phase
                )
                
                self.current_messages.append({
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "args": args,
                    "phase": phase,
                    "panel": panel
                })
                
            elif chunk_type == "tool_result":
                tool_name = chunk.get("tool_name", "")
                result = chunk.get("result", "")
                success = chunk.get("success", True)
                
                panel = self.message_display.render_tool_result(
                    tool_name, result, success
                )
                
                self.current_messages.append({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": result,
                    "success": success,
                    "panel": panel
                })
                
        elif event_type == "turn_completed":
            # Turn completed
            self._finalize_assistant_message()
            
        elif event_type == "approvals_pending":
            # Handle tool approvals
            tools = data.get("tools", [])
            if tools:
                self._handle_approvals(tools)
            
        elif event_type == "conversation_error":
            error_msg = data.get("error", "Unknown error")
            error_panel = self.message_display.render_error(error_msg)
            self.current_messages.append({
                "type": "error",
                "text": error_msg,
                "panel": error_panel
            })
        
        # Update display for real-time updates
        if self.streaming:
            self.update_display()
    
    def _update_assistant_message(self, new_panel) -> None:
        """Update or add assistant message panel."""
        
        # Find existing assistant message
        for i, msg in enumerate(self.current_messages):
            if msg.get("type") == "assistant" and msg.get("streaming"):
                self.current_messages[i] = {
                    "type": "assistant",
                    "text": new_panel.title,
                    "panel": new_panel,
                    "streaming": True
                }
                return
        
        # Add new assistant message
        self.current_messages.append({
            "type": "assistant",
            "text": new_panel.title,
            "panel": new_panel,
            "streaming": True
        })
    
    def _finalize_assistant_message(self) -> None:
        """Finalize streaming assistant message."""
        
        for i, msg in enumerate(self.current_messages):
            if msg.get("type") == "assistant" and msg.get("streaming"):
                # Update to non-streaming
                self.current_messages[i] = {
                    **msg,
                    "streaming": False
                }
                return
    
    def _handle_approvals(self, tools) -> None:
        """Handle tool approvals."""
        
        if not tools:
            return
        
        # Show approval dialog
        try:
            approvals, reasons = self.approval_dialog.show_batch_approval_dialog(tools)
            
            # Submit approval results back to conversation manager
            # This would integrate with conversation manager
            logger.debug(f"Approval results: {approvals}")
            
        except Exception as e:
            logger.error(f"Error in approval handling: {e}")
            error_panel = self.message_display.render_error(f"Approval error: {e}")
            self.current_messages.append({
                "type": "error",
                "text": f"Approval error: {e}",
                "panel": error_panel
            })
    
    def _interrupt_conversation(self) -> None:
        """Interrupt current conversation."""
        if self.conversation_manager:
            self.conversation_manager.interrupt()
        self.interrupt_requested = True
        self.streaming = False

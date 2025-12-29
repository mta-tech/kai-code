"""Main TUI application."""

import logging
from pathlib import Path

from textual.app import App
from textual.binding import Binding
from langgraph.types import Interrupt

from ..agent import KaiAgent
from .screens.main import MainScreen
from .widgets import (
    StatusBar,
    MessageList,
    ToolPanel,
    InputArea,
    InputSubmitted,
    ApprovalModal,
    ApprovalDecision,
    ApprovalResult,
)
from .components.message import MessageRole
from .commands import CommandRegistry

# Setup logger for TUI app
logger = logging.getLogger("kai_code.tui")


# Tools that require approval when not in YOLO mode
SENSITIVE_TOOLS = {"execute", "write_file", "edit_file", "apply_patch"}


class KaiCodeApp(App):
    """kai-code interactive TUI application."""

    TITLE = "kai-code"

    CSS = """
    Screen {
        background: $background;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "interrupt", "Interrupt"),
        Binding("escape", "escape", "Cancel"),
    ]

    def __init__(
        self,
        root_dir: str | Path = ".",
        model: str = "default",
        session: str = "default",
        yolo: bool = True,
        **kwargs,
    ) -> None:
        logger.debug(
            f"Initializing KaiCodeApp with root_dir={root_dir}, model={model}, session={session}, yolo={yolo}"
        )
        super().__init__(**kwargs)
        self.root_dir = Path(root_dir).resolve()
        self._model = model
        self._session = session
        self._yolo = yolo
        self._commands = CommandRegistry()
        self._agent = None  # Will hold KaiAgent instance
        self._streaming = False
        logger.debug("KaiCodeApp initialized, calling _init_agent")
        self._init_agent()

    def _init_agent(self) -> None:
        """Initialize the agent."""
        logger.debug("Initializing agent...")
        try:
            # Treat "default" as "use our configured default model", not "let dependencies pick".
            model = self._model
            if model == "default":
                from ..model import get_default_model

                model = get_default_model()
                logger.debug(f"Resolved default model to: {model}")

            logger.debug(f"Creating KaiAgent with model={model}, yolo={self._yolo}")
            self._agent = KaiAgent(
                root_dir=self.root_dir,
                model=model,
                yolo=self._yolo,
            )
            logger.debug("Agent created successfully")
        except Exception as e:
            # Agent initialization can fail if no API key is set
            logger.error(f"Failed to initialize agent: {e}")
            self._agent = None

    def on_mount(self) -> None:
        """Set up the app on mount."""
        self.push_screen(
            MainScreen(
                model=self._model,
                session=self._session,
                yolo=self._yolo,
            )
        )

    def on_input_submitted(self, event: InputSubmitted) -> None:
        """Handle input from user."""
        logger.debug(
            f"Input submitted: value={event.value}, is_command={event.is_command}"
        )

        if event.is_command:
            logger.debug(f"Handling command: {event.value}")
            self._handle_command(event.value)
        else:
            logger.debug(f"Handling message: {event.value}")
            self._handle_message(event.value)

    def _handle_command(self, text: str) -> None:
        """Handle a slash command."""
        # Parse command
        text = text.strip()
        if not text.startswith("/"):
            return

        parts = text[1:].split(None, 1)
        cmd_name = parts[0] if parts else ""
        cmd_args = parts[1] if len(parts) > 1 else ""

        if not self._commands.is_valid(cmd_name):
            self._show_error(f"Unknown command: /{cmd_name}")
            return

        # Execute command
        if cmd_name in ("exit", "quit", "q"):
            self.exit()
        elif cmd_name == "help":
            self._show_help()
        elif cmd_name == "clear":
            self._clear_messages()
        elif cmd_name == "yolo":
            self._toggle_yolo()
        elif cmd_name == "model":
            self._switch_model(cmd_args)
        elif cmd_name == "session":
            self._show_session_info()
        elif cmd_name == "ralph-loop":
            self._start_ralph_loop(cmd_args)
        elif cmd_name in ("cancel-ralph", "ralph-cancel", "stop-ralph"):
            self._cancel_ralph()
        elif cmd_name in ("ralph-status", "ralph"):
            self._show_ralph_status()
        else:
            self._show_error(f"Command not yet implemented: /{cmd_name}")

    def _needs_approval(self, tool_name: str) -> bool:
        """Check if a tool needs user approval."""
        if self._yolo:
            return False  # YOLO mode bypasses approval
        return tool_name in SENSITIVE_TOOLS

    def _handle_message(self, text: str) -> None:
        """Handle a user message."""
        logger.debug(f"Handling user message: {text}")
        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(MessageRole.USER, text)

        # NOTE: KaiAgent.stream() is a synchronous iterator and may block on network I/O.
        # We use an async worker that runs the sync iterator in a thread for both modes.
        logger.debug(
            f"Starting {'YOLO' if self._yolo else 'non-YOLO'} mode streaming (async)"
        )
        self.run_worker(self._run_agent_stream_async(text), name="agent_stream")

    async def _run_agent_stream_async(self, prompt: str) -> None:
        """Run agent and stream response using asyncio.to_thread for sync iterator.

        This is the primary streaming method that works with Textual's async event loop.
        """
        import asyncio

        logger.debug(f"Starting async agent stream with prompt: {prompt[:50]}...")

        if not self._agent:
            logger.error("Agent not available")
            message_list = self.query_one("#message-list", MessageList)
            message_list.add_message(
                MessageRole.ERROR,
                "No agent available. Check API key configuration.",
            )
            return

        message_list = self.query_one("#message-list", MessageList)
        tool_panel = self.query_one("#tool-panel", ToolPanel)
        logger.debug("Got widgets for streaming")

        self._streaming = True
        streaming_msg = message_list.add_streaming_message(MessageRole.ASSISTANT)
        streaming_msg.append_content("Processing...")
        logger.debug("Created streaming message with Processing... indicator")

        # Collect all chunks in a thread, then process them
        def collect_chunks():
            """Run synchronous stream in thread and collect chunks."""
            chunks = []
            try:
                for chunk in self._agent.stream(prompt):
                    chunks.append(chunk)
            except Exception as e:
                chunks.append({"__error__": str(e)})
            return chunks

        try:
            logger.debug("Running agent.stream() in thread...")
            chunks = await asyncio.to_thread(collect_chunks)
            logger.debug(f"Got {len(chunks)} chunks from stream")

            # Process all chunks on the main thread
            for i, chunk in enumerate(chunks):
                logger.debug(f"Processing chunk {i + 1}/{len(chunks)}")

                # Check for error
                if isinstance(chunk, dict) and chunk.get("__error__"):
                    error_msg = chunk["__error__"]
                    logger.error(f"Stream error: {error_msg}")
                    message_list.add_message(
                        MessageRole.ERROR, f"Stream error: {error_msg}"
                    )
                    continue

                # Process the chunk
                self._process_chunk(chunk, streaming_msg)

            # Check if we received any AI content
            final_content = getattr(streaming_msg, "_content", "")
            logger.debug(
                f"Final content: {final_content[:100] if final_content else 'empty'}..."
            )

            if not final_content or final_content in (
                "Processing...",
                "Processing... ",
                "",
            ):
                logger.warning("No AI content received")
                streaming_msg._content = "(No response from AI)"
                streaming_msg._refresh_display()

        except Exception as e:
            logger.error(f"Error in async stream: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            message_list.add_message(
                MessageRole.ERROR,
                f"Stream error: {e}\nThis might be due to network issues or API problems.",
            )
        finally:
            logger.debug("Finishing streaming")
            self._streaming = False
            message_list.finish_streaming()
            tool_panel.reset()

    def _run_agent_stream_threaded(self, prompt: str):
        """Run the agent stream in a background thread (YOLO mode only).

        Textual UI updates must happen on the main thread, so we use call_from_thread.
        NOTE: This method is deprecated in favor of _run_agent_stream_async.
        """

        def _runner() -> None:
            logger.debug("Threaded runner started")
            if not self._agent:
                self.call_from_thread(
                    lambda: self.query_one("#message-list", MessageList).add_message(
                        MessageRole.ERROR,
                        "No agent available. Check API key configuration.",
                    )
                )
                return

            # Get widgets once to avoid repeated queries
            def get_widgets():
                message_list = self.query_one("#message-list", MessageList)
                tool_panel = self.query_one("#tool-panel", ToolPanel)
                return message_list, tool_panel

            try:
                message_list, tool_panel = self.call_from_thread(get_widgets)
                logger.debug(
                    f"Got widgets: message_list={message_list}, tool_panel={tool_panel}"
                )
            except Exception as widget_error:
                logger.error(f"Failed to get widgets: {widget_error}")
                return

            self.call_from_thread(lambda: setattr(self, "_streaming", True))

            try:
                streaming_msg = self.call_from_thread(
                    lambda: message_list.add_streaming_message(MessageRole.ASSISTANT)
                )
                logger.debug(f"Created streaming message: {streaming_msg}")

                if streaming_msg is None:
                    logger.error("streaming_msg is None - call_from_thread failed")
                    self.call_from_thread(
                        lambda: message_list.add_message(
                            MessageRole.ERROR, "Failed to create streaming message"
                        )
                    )
                    return

                # Show processing indicator
                self.call_from_thread(
                    lambda msg=streaming_msg: msg.append_content("Processing...")
                )
                logger.debug("Added Processing... indicator to streaming message")
            except Exception as msg_error:
                logger.error(f"Failed to create streaming message: {msg_error}")
                return

            chunk_count = 0
            try:
                logger.debug(f"Starting agent.stream() with prompt: {prompt[:50]}...")
                for chunk in self._agent.stream(prompt):
                    chunk_count += 1
                    chunk_keys = chunk.keys() if isinstance(chunk, dict) else "N/A"
                    logger.debug(f"Chunk #{chunk_count}: keys={chunk_keys}")

                    # In YOLO mode we don't expect HITL approval interrupts.
                    # Use call_from_thread for all UI updates
                    # Capture both chunk and streaming_msg explicitly to avoid closure issues
                    try:
                        self.call_from_thread(
                            lambda c=chunk, msg=streaming_msg: self._process_chunk(
                                c, msg
                            )
                        )
                    except Exception as chunk_error:
                        # Error processing individual chunk, but continue streaming
                        logger.error(f"Error processing chunk: {chunk_error}")
                        self.call_from_thread(
                            lambda e=str(chunk_error), ml=message_list: ml.add_message(
                                MessageRole.ERROR,
                                f"Error processing response chunk: {e}",
                            )
                        )
                logger.debug(f"Stream completed. Total chunks: {chunk_count}")

                # Check if we received any AI content
                final_content = self.call_from_thread(
                    lambda msg=streaming_msg: getattr(msg, "_content", "")
                )
                logger.debug(
                    f"Final streaming content: {final_content[:100] if final_content else 'empty'}..."
                )

                # If still showing "Processing..." or empty, no AI content was received
                if not final_content or final_content in (
                    "Processing...",
                    "Processing... ",
                    "",
                ):
                    logger.warning("No AI content received in stream")
                    self.call_from_thread(
                        lambda msg=streaming_msg: setattr(
                            msg, "_content", "(No response from AI)"
                        )
                    )
                    self.call_from_thread(
                        lambda msg=streaming_msg: msg._refresh_display()
                    )

            except Exception as e:
                logger.error(f"Stream error: {e}")
                import traceback

                logger.debug(traceback.format_exc())
                self.call_from_thread(
                    lambda err=e: message_list.add_message(
                        MessageRole.ERROR,
                        f"Stream error: {err}\nThis might be due to network issues or API problems.",
                    )
                )
            finally:
                logger.debug("Cleaning up streaming state")
                self.call_from_thread(lambda: setattr(self, "_streaming", False))
                self.call_from_thread(message_list.finish_streaming)
                self.call_from_thread(tool_panel.reset)
                logger.debug("Threaded runner finished")

        return _runner

    async def _run_agent_stream(self, prompt: str) -> None:
        """Run agent and stream response to UI (non-YOLO mode with HITL support).

        Uses a background thread for the synchronous iterator to avoid blocking
        the event loop, while still supporting async HITL modal dialogs.
        """
        import asyncio
        import threading

        logger.debug(f"Starting async agent stream with prompt: {prompt}")

        if not self._agent:
            logger.error("Agent not available in async stream")
            message_list = self.query_one("#message-list", MessageList)
            message_list.add_message(
                MessageRole.ERROR,
                "No agent available. Check API key configuration.",
            )
            return

        message_list = self.query_one("#message-list", MessageList)
        tool_panel = self.query_one("#tool-panel", ToolPanel)
        logger.debug("Got widgets for async stream")

        self._streaming = True
        streaming_msg = message_list.add_streaming_message(MessageRole.ASSISTANT)
        streaming_msg.append_content("Processing...")
        logger.debug("Created streaming message with Processing... indicator")

        # Queue-based approach: run sync iterator in thread, consume async
        chunk_queue: asyncio.Queue = asyncio.Queue()
        done_event = asyncio.Event()
        error_holder: list = [None]

        def producer():
            """Run synchronous stream in background thread."""
            try:
                for chunk in self._agent.stream(prompt):
                    # Use call_from_thread to safely put chunk in async queue
                    self.call_from_thread(lambda c=chunk: chunk_queue.put_nowait(c))
            except Exception as e:
                error_holder[0] = e
            finally:
                self.call_from_thread(done_event.set)

        # Start producer in background thread
        thread = threading.Thread(target=producer, daemon=True)
        thread.start()

        try:
            logger.debug("Starting async chunk consumer loop")
            chunk_count = 0

            # Consume chunks from queue asynchronously
            while not done_event.is_set() or not chunk_queue.empty():
                try:
                    chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                chunk_count += 1
                logger.debug(f"Processing async chunk #{chunk_count}: {type(chunk)}")
                # Check if this chunk is an interrupt (HITL approval required)
                has_interrupt = False

                try:
                    if isinstance(chunk, tuple) and len(chunk) == 2:
                        # LangGraph streams tuples of (node_name, state)
                        node_name, state = chunk

                        # Check if there's an interrupt in the state
                        if isinstance(state, dict):
                            interrupts = state.get("__interrupts__", [])
                            if interrupts and not self._yolo:
                                has_interrupt = True
                                # Handle the interrupt - show approval modal
                                for interrupt in interrupts:
                                    if isinstance(interrupt, Interrupt):
                                        # Extract tool information from interrupt value
                                        tool_info = interrupt.value
                                        if isinstance(tool_info, dict):
                                            tool_name = tool_info.get("name", "unknown")
                                            tool_args = tool_info.get("args", {})

                                            if self._needs_approval(tool_name):
                                                # Show the tool in the tool panel
                                                tool_panel.show_tool_running(
                                                    tool_name, tool_args
                                                )

                                                # Show approval modal and wait for decision
                                                result = await self.push_screen_wait(
                                                    ApprovalModal(
                                                        tool_name=tool_name,
                                                        tool_args=tool_args,
                                                    )
                                                )

                                                if (
                                                    result.decision
                                                    == ApprovalDecision.REJECT
                                                ):
                                                    # User rejected the tool call
                                                    streaming_msg.append_content(
                                                        f"\n\n[Tool '{tool_name}' was rejected by user]"
                                                    )
                                                    tool_panel.reset()
                                                    return
                                                elif (
                                                    result.decision
                                                    == ApprovalDecision.APPROVE
                                                ):
                                                    # User approved - resume the agent
                                                    try:
                                                        # Resume with approval decision
                                                        for (
                                                            resume_chunk
                                                        ) in self._agent._graph.stream(
                                                            None,
                                                            config={
                                                                "configurable": {
                                                                    "thread_id": self._agent.thread_id
                                                                },
                                                            },
                                                        ):
                                                            # Continue processing resumed chunks
                                                            self._process_chunk(
                                                                resume_chunk,
                                                                streaming_msg,
                                                            )
                                                    except Exception as e:
                                                        message_list.add_message(
                                                            MessageRole.ERROR,
                                                            f"Error resuming: {e}",
                                                        )
                                                # TODO: Handle EDIT decision
                    elif isinstance(chunk, dict) and chunk.get("__interrupt__"):
                        has_interrupt = True
                        if not self._yolo:
                            # Handle direct interrupt format
                            interrupt_data = chunk.get("__interrupt__")
                            if isinstance(interrupt_data, dict):
                                tool_name = interrupt_data.get("name", "unknown")
                                tool_args = interrupt_data.get("args", {})

                                if self._needs_approval(tool_name):
                                    tool_panel.show_tool_running(tool_name, tool_args)
                                    result = await self.push_screen_wait(
                                        ApprovalModal(
                                            tool_name=tool_name,
                                            tool_args=tool_args,
                                        )
                                    )

                                    if result.decision == ApprovalDecision.REJECT:
                                        streaming_msg.append_content(
                                            f"\n\n[Tool '{tool_name}' was rejected by user]"
                                        )
                                        tool_panel.reset()
                                        return
                                    # TODO: Handle other decisions
                except Exception as interrupt_error:
                    # Error during interrupt processing
                    message_list.add_message(
                        MessageRole.ERROR,
                        f"Error processing interrupt: {interrupt_error}",
                    )
                    continue

                # Process normal chunks (content updates) if not an interrupt
                if not has_interrupt:
                    try:
                        self._process_chunk(chunk, streaming_msg)
                    except Exception as process_error:
                        # Error processing chunk, but continue with next chunk
                        message_list.add_message(
                            MessageRole.ERROR,
                            f"Error processing response chunk: {process_error}",
                        )

            # Check for producer thread error
            if error_holder[0]:
                raise error_holder[0]

            # Check if we received any AI content
            final_content = getattr(streaming_msg, "_content", "")
            logger.debug(
                f"Final async streaming content: {final_content[:100] if final_content else 'empty'}..."
            )

            # If still showing "Processing..." or empty, no AI content was received
            if not final_content or final_content in (
                "Processing...",
                "Processing... ",
                "",
            ):
                logger.warning("No AI content received in async stream")
                streaming_msg._content = "(No response from AI)"
                streaming_msg._refresh_display()

        except Exception as e:
            logger.error(f"Error in async stream: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            message_list.add_message(
                MessageRole.ERROR,
                f"Stream error: {e}\nThis might be due to network issues or API problems.",
            )
        finally:
            logger.debug("Async stream finishing up")
            self._streaming = False
            message_list.finish_streaming()
            tool_panel.reset()

    def _process_chunk(self, chunk: any, streaming_msg: any) -> None:
        """Process a stream chunk and update the streaming message.

        Only processes AI messages, skipping user messages and tool results.
        """
        messages = None

        # Extract messages from chunk
        if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
            messages = chunk.get("messages", [])
        elif isinstance(chunk, tuple) and len(chunk) == 2:
            # Handle tuple chunks (node_name, state)
            _, state = chunk
            if isinstance(state, dict) and isinstance(state.get("messages"), list):
                messages = state.get("messages", [])

        if not messages:
            return

        # Get the last message
        last_msg = messages[-1]
        msg_type = type(last_msg).__name__

        # Only process AI messages, skip user/human and tool messages
        is_ai_message = False
        if isinstance(last_msg, dict):
            role = last_msg.get("role", "")
            is_ai_message = role in ("assistant", "ai")
        else:
            # LangChain message objects
            is_ai_message = "AIMessage" in msg_type

        if not is_ai_message:
            logger.debug(f"Skipping non-AI message: {msg_type}")
            return

        # Get content from AI message
        if isinstance(last_msg, dict):
            content = last_msg.get("content", "")
        else:
            content = getattr(last_msg, "content", "")

        # Update streaming message with new content
        if content and isinstance(content, str):
            # Get current content to calculate delta
            current_content = getattr(streaming_msg, "_content", "")

            # Check if we need to clear the "Processing..." indicator
            if (
                current_content == "Processing..."
                or current_content == "Processing... "
            ):
                # First real AI content - replace the indicator entirely
                logger.debug(f"Replacing Processing indicator with: {content[:50]}...")
                streaming_msg._content = content
                streaming_msg._refresh_display()
            elif content.startswith(current_content):
                # Append only the new part (normal streaming delta)
                delta = content[len(current_content) :]
                if delta:
                    logger.debug(f"Appending delta: {delta[:50]}...")
                    streaming_msg.append_content(delta)
            elif current_content.startswith(content):
                # Content is subset of current - ignore (stale chunk)
                logger.debug(f"Ignoring stale chunk: {content[:30]}...")
            else:
                # Completely different content - replace entirely
                logger.debug(f"Replacing content: {content[:50]}...")
                streaming_msg._content = content
                streaming_msg._refresh_display()

    def _show_help(self) -> None:
        """Show help text."""
        message_list = self.query_one("#message-list", MessageList)
        help_text = self._commands.get_help_text()
        message_list.add_message(MessageRole.ASSISTANT, help_text)

    def _show_error(self, error: str) -> None:
        """Show error message."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(MessageRole.ERROR, error)

    def _clear_messages(self) -> None:
        """Clear all messages."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.clear_messages()

    def _toggle_yolo(self) -> None:
        """Toggle YOLO mode."""
        self._yolo = not self._yolo
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_yolo(self._yolo)

        message_list = self.query_one("#message-list", MessageList)
        mode = "enabled" if self._yolo else "disabled"

        # Note: The agent was initialized with the original yolo setting.
        # Toggling YOLO mode here affects only the TUI behavior (whether to show approval modals).
        # The agent's internal yolo setting and interrupt configuration remain unchanged.
        # To fully apply the new yolo mode to the agent, we would need to reinitialize it.

        message_list.add_message(
            MessageRole.ASSISTANT,
            f"YOLO mode {mode}. Note: Agent interrupt behavior set at startup.",
        )

    def _switch_model(self, model: str) -> None:
        """Switch to a different model."""
        if not model:
            self._show_error("Usage: /model <model-name>")
            return

        self._model = model
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_model(model)

        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"Switched to model: {model}",
        )

    def _show_session_info(self) -> None:
        """Show current session info."""
        message_list = self.query_one("#message-list", MessageList)
        info = f"""Session Info:
- Root: {self.root_dir}
- Model: {self._model}
- Session: {self._session}
- YOLO: {self._yolo}"""
        message_list.add_message(MessageRole.ASSISTANT, info)

    def _start_ralph_loop(self, args: str) -> None:
        """Start Ralph autonomous loop."""
        from ..ralph_commands import ralph_loop_command
        import shlex

        message_list = self.query_one("#message-list", MessageList)

        if not args.strip():
            message_list.add_message(
                MessageRole.ERROR,
                "Usage: /ralph-loop <prompt> [--promise <text>] [--max-iterations <n>]"
            )
            return

        # Parse arguments
        try:
            parts = shlex.split(args)
        except ValueError as e:
            message_list.add_message(MessageRole.ERROR, f"Error parsing arguments: {e}")
            return

        if not parts:
            message_list.add_message(
                MessageRole.ERROR,
                "Usage: /ralph-loop <prompt> [--promise <text>] [--max-iterations <n>]"
            )
            return

        # Extract prompt (first non-flag argument)
        prompt = parts[0]
        completion_promise = None
        max_iterations = None
        timeout_seconds = None
        token_limit = 500_000

        # Parse flags
        i = 1
        while i < len(parts):
            if parts[i] in ("--promise", "--completion-promise") and i + 1 < len(parts):
                completion_promise = parts[i + 1]
                i += 2
            elif parts[i] in ("--max-iterations", "--max-iter") and i + 1 < len(parts):
                try:
                    max_iterations = int(parts[i + 1])
                except ValueError:
                    message_list.add_message(MessageRole.ERROR, f"Invalid max-iterations: {parts[i + 1]}")
                    return
                i += 2
            elif parts[i] == "--timeout" and i + 1 < len(parts):
                try:
                    timeout_seconds = int(parts[i + 1])
                except ValueError:
                    message_list.add_message(MessageRole.ERROR, f"Invalid timeout: {parts[i + 1]}")
                    return
                i += 2
            elif parts[i] == "--token-limit" and i + 1 < len(parts):
                try:
                    token_limit = int(parts[i + 1])
                except ValueError:
                    message_list.add_message(MessageRole.ERROR, f"Invalid token-limit: {parts[i + 1]}")
                    return
                i += 2
            else:
                i += 1

        # Start the loop
        try:
            result = ralph_loop_command(
                self._agent,
                prompt=prompt,
                completion_promise=completion_promise,
                max_iterations=max_iterations,
                timeout_seconds=timeout_seconds,
                token_limit=token_limit,
            )
            message_list.add_message(MessageRole.ASSISTANT, result)
        except Exception as e:
            message_list.add_message(MessageRole.ERROR, f"Error starting Ralph loop: {e}")

    def _cancel_ralph(self) -> None:
        """Cancel active Ralph loop."""
        from ..ralph_commands import cancel_ralph_command

        message_list = self.query_one("#message-list", MessageList)
        try:
            result = cancel_ralph_command(self._agent)
            message_list.add_message(MessageRole.ASSISTANT, result)
        except Exception as e:
            message_list.add_message(MessageRole.ERROR, f"Error canceling Ralph loop: {e}")

    def _show_ralph_status(self) -> None:
        """Show Ralph loop status."""
        from ..ralph_commands import ralph_status_command

        message_list = self.query_one("#message-list", MessageList)
        try:
            result = ralph_status_command(self._agent)
            message_list.add_message(MessageRole.ASSISTANT, result)
        except Exception as e:
            message_list.add_message(MessageRole.ERROR, f"Error getting Ralph status: {e}")

    def action_interrupt(self) -> None:
        logger.debug(f"Interrupt requested. Streaming: {self._streaming}")
        if self._streaming:
            for worker in self.workers:
                if worker.name == "agent_stream":
                    logger.debug("Cancelling agent_stream worker")
                    worker.cancel()

            self._streaming = False
            message_list = self.query_one("#message-list", MessageList)
            message_list.add_message(MessageRole.ERROR, "Operation cancelled by user.")
            message_list.finish_streaming()

            tool_panel = self.query_one("#tool-panel", ToolPanel)
            tool_panel.reset()
        else:
            logger.debug("Not streaming, exiting app")
            self.exit()

    def action_escape(self) -> None:
        import time

        now = time.time()
        if hasattr(self, "_last_escape_time") and now - self._last_escape_time < 0.5:
            self.action_interrupt()
            self._last_escape_time = 0
        else:
            self._last_escape_time = now
            if self._streaming:
                self.notify("Press ESC again to cancel", timeout=1)


def main() -> None:
    """Run the TUI application."""
    app = KaiCodeApp()
    app.run()


if __name__ == "__main__":
    main()

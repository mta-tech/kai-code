"""DbtAgent - specialized agent for dbt data engineering."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kai_code.agent import KaiAgent
from kai_code.agents.dbt.adapters import DatabaseAdapter, get_adapter
from kai_code.agents.dbt.tools.dbt_cli_tools import create_dbt_cli_tools
from kai_code.agents.dbt.tools.schema_tools import create_schema_tools
from kai_code.prompts import load_prompt


class DbtAgent(KaiAgent):
    """Specialized agent for dbt data engineering.

    Inherits ALL KaiAgent capabilities:
    - File operations (read, write, edit, glob, grep)
    - Shell execution (execute)
    - Patch application (apply_patch)
    - Skills system (.skills/)
    - YOLO/approval modes
    - Session persistence

    Adds dbt-specific capabilities:
    - Schema introspection tools
    - dbt CLI wrapper tools
    - Database adapter connection
    - dbt skill auto-loading
    """

    def __init__(
        self,
        root_dir: str | Path,
        *,
        model: str | None = None,
        db_connection: str | None = None,
        dbt_project_dir: str | Path | None = None,
        dbt_profiles_dir: str | Path | None = None,
        yolo: bool = True,
        system_prompt: str | None = None,
        skills_dir: str = ".skills",
        state_path: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize DbtAgent.

        Args:
            root_dir: Project root directory.
            model: LLM model handle.
            db_connection: Database connection string for introspection.
            dbt_project_dir: dbt project directory (defaults to root_dir).
            dbt_profiles_dir: profiles.yml location (defaults to ~/.dbt).
            yolo: If False, require approval for dbt commands.
            system_prompt: Additional system prompt.
            skills_dir: Skills directory.
            state_path: Session state file path.
            **kwargs: Additional KaiAgent arguments.
        """
        # Load kai-dbt prompt (inherits from kai-code automatically)
        # Note: KaiAgent's _build_graph will use this instead of kai-code
        # The user's additional system_prompt is appended if provided
        combined_prompt = system_prompt  # Just pass through; dbt prompt loaded below

        # Initialize parent KaiAgent
        super().__init__(
            root_dir=root_dir,
            model=model,
            yolo=yolo,
            system_prompt=combined_prompt,
            skills_dir=skills_dir,
            state_path=state_path,
            **kwargs,
        )

        # dbt-specific configuration
        self._db_connection = db_connection
        self._dbt_project_dir = (
            Path(dbt_project_dir) if dbt_project_dir else Path(root_dir)
        )
        self._dbt_profiles_dir = Path(dbt_profiles_dir) if dbt_profiles_dir else None
        self._adapter: DatabaseAdapter | None = None

        # Initialize database adapter if connection provided
        if db_connection:
            self._adapter = get_adapter(db_connection)

    @property
    def adapter(self) -> DatabaseAdapter | None:
        """Database adapter for introspection."""
        return self._adapter

    @property
    def db_connection(self) -> str | None:
        """Database connection string."""
        return self._db_connection

    @property
    def dbt_project_dir(self) -> Path:
        """dbt project directory."""
        return self._dbt_project_dir

    @property
    def dbt_profiles_dir(self) -> Path | None:
        """dbt profiles directory."""
        return self._dbt_profiles_dir

    def _get_base_prompt_name(self) -> str:
        """Use kai-dbt prompt (inherits from kai-code)."""
        return "kai-dbt"

    def _build_graph(self):
        """Build the agent graph with dbt-specific tools included."""
        from langchain_core.tools import tool
        from kai_code.patching import apply_patch as _apply_patch
        from kai_code.permissions import permission_denied_message
        from kai_code.tasks import BACKGROUND_TASK_TOOLS
        from kai_code.tools import load_skill, unload_skill, list_skills, reload_skills
        from kai_code.tools.web import http_request as _http_request, web_search as _web_search, fetch_url as _fetch_url
        from deepagents import create_deep_agent
        from langchain.chat_models import init_chat_model
        import json
        import os
        import subprocess
        from pathlib import Path

        if self._graph is not None:
            return self._graph

        model = self._config.model
        if isinstance(model, str):
            # Handle OpenRouter models with custom base_url
            if model.startswith("openrouter:"):
                from langchain_openai import ChatOpenAI
                openrouter_model_id = model[len("openrouter:"):]
                chat_model = ChatOpenAI(
                    model=openrouter_model_id,
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ.get("OPENROUTER_API_KEY"),
                )
            else:
                chat_model = init_chat_model(model)
        else:
            chat_model = model

        # Get memory blocks for prompt assembly
        memory_manager = getattr(self._config, 'memory_manager', None)

        # Discover and format skills if memory manager available
        skills_prompt = None
        if memory_manager:
            from kai_code.skills_parser import discover_skills, format_skills_for_prompt
            skills_result = discover_skills(self._config.root_dir, self._config.skills_dir)
            memory_manager.update_skills_discovery(skills_result.skills, self._config.skills_dir)

            # Format skills for prompt
            skills_prompt = format_skills_for_prompt(skills_result.skills, skills_directory=self._config.skills_dir)
        else:
            # Fallback to old method
            from kai_code.skills import discover_skills_legacy, format_skills_for_prompt_legacy
            skills = discover_skills_legacy(self._config.root_dir, self._config.skills_dir)
            skills_prompt = format_skills_for_prompt_legacy(skills, skills_dir=self._config.skills_dir)

        # Build prompt parts: base prompt + project context + user custom + skills + memory
        base_prompt = load_prompt(self._get_base_prompt_name())
        prompt_parts = [base_prompt]

        # Load project context from CLAUDE.md or AGENTS.md if present
        project_context = self._load_project_context()
        if project_context:
            prompt_parts.append(project_context)

        # Add user's custom system_prompt if provided
        if self._config.system_prompt:
            prompt_parts.append(self._config.system_prompt)

        # Add skills prompt
        if skills_prompt:
            prompt_parts.append(skills_prompt)

        # Add memory blocks to prompt if available
        if memory_manager:
            memory_content = memory_manager.format_for_prompt()
            if memory_content.strip():
                prompt_parts.append(memory_content)

        full_system_prompt = "\n\n".join(prompt_parts)

        # YOLO mode means no HITL interrupts.
        interrupt_on = None
        checkpointer = None
        if not self._config.yolo:
            interrupt_on = self._config.interrupt_on or {
                "execute": True,
                "write_file": True,
                "edit_file": True,
                "apply_patch": True,
            }
            # Required for HITL interrupts to work.
            # Use a disk-backed saver so resume survives process restarts.
            if self._config.state_path is not None:
                from kai_code.checkpointer import KaiFileCheckpointer
                cp_path = (self._config.state_path.parent / "checkpoints.pkl").resolve()
                checkpointer = KaiFileCheckpointer(cp_path)
            else:
                from langgraph.checkpoint.memory import MemorySaver
                checkpointer = MemorySaver()

        @tool("apply_patch")
        def apply_patch_tool(patch: str) -> str:
            """Apply a unified diff patch under the project root."""
            enabled = self._config.enabled_tools
            if enabled is not None and not any(fnmatch("apply_patch", p) for p in enabled):
                return permission_denied_message("apply_patch")
            if self._config.permissions is not None and not self._config.permissions.tool_allowed("apply_patch"):
                return permission_denied_message("apply_patch")
            res = _apply_patch(self._config.root_dir, patch)
            if res.ok:
                return res.output or "OK"
            return f"Error applying patch:\n{res.output}".strip()

        @tool("web_search")
        def web_search_tool(
            query: str,
            max_results: int = 5,
            topic: str = "general",
            include_raw_content: bool = False,
        ) -> str:
            """Search the web using Tavily for current information and documentation.

            Args:
                query: The search query (be specific and detailed)
                max_results: Number of results to return (default: 5)
                topic: Search topic type - "general" for most queries, "news" for current events
                include_raw_content: Include full page content (warning: uses more tokens)

            Returns:
                JSON string with search results
            """
            result = _web_search(query, max_results=max_results, topic=topic, include_raw_content=include_raw_content)
            return json.dumps(result, indent=2)

        @tool("fetch_url")
        def fetch_url_tool(url: str, timeout: int = 30) -> str:
            """Fetch content from a URL and convert HTML to markdown format.

            Args:
                url: The URL to fetch (must be a valid HTTP/HTTPS URL)
                timeout: Request timeout in seconds (default: 30)

            Returns:
                JSON string with markdown content and metadata
            """
            result = _fetch_url(url, timeout=timeout)
            return json.dumps(result, indent=2)

        @tool("http_request")
        def http_request_tool(
            url: str,
            method: str = "GET",
            headers: str | None = None,
            data: str | None = None,
            params: str | None = None,
            timeout: int = 30,
        ) -> str:
            """Make HTTP requests to APIs and web services.

            Args:
                url: Target URL
                method: HTTP method (GET, POST, PUT, DELETE, etc.)
                headers: JSON string of HTTP headers to include
                data: Request body data (JSON string)
                params: JSON string of URL query parameters
                timeout: Request timeout in seconds

            Returns:
                JSON string with response data including status, headers, and content
            """
            # Parse JSON strings to dicts if provided
            headers_dict = json.loads(headers) if headers else None
            data_dict = json.loads(data) if data else None
            params_dict = json.loads(params) if params else None
            result = _http_request(url, method=method, headers=headers_dict, data=data_dict, params=params_dict, timeout=timeout)
            return json.dumps(result, indent=2)

        @tool("execute_async")
        def execute_async_tool(command: str, timeout: int) -> str:
            """Execute shell command with auto-background on timeout.

            Use this for commands that may take a while. If the command exceeds
            the specified timeout, it automatically moves to a background task
            so you can continue working.

            Args:
                command: Shell command to execute
                timeout: Seconds to wait before moving to background (required)

            Returns:
                JSON with either:
                - {exit_code, output} if completed within timeout
                - {moved_to_background, task_id, message} if promoted to background

            After promotion, use get_task_output(task_id) to check results.
            """
            import subprocess as sp
            from kai_code.tasks import get_task_manager

            root_dir = self._config.root_dir

            try:
                result = sp.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(root_dir),
                    env={**os.environ},
                )
                output = (result.stdout or "") + (result.stderr or "")
                # Truncate if too long
                if len(output) > 80000:
                    output = output[:80000] + "\n... (truncated)"
                return json.dumps({
                    "exit_code": result.returncode,
                    "output": output,
                })
            except sp.TimeoutExpired as e:
                # Capture any partial output before promoting to background
                partial_stdout = e.stdout or ""
                partial_stderr = e.stderr or ""
                if isinstance(partial_stdout, bytes):
                    partial_stdout = partial_stdout.decode("utf-8", errors="replace")
                if isinstance(partial_stderr, bytes):
                    partial_stderr = partial_stderr.decode("utf-8", errors="replace")
                partial_output = partial_stdout + partial_stderr

                # Auto-promote to background
                task_manager = get_task_manager()
                task_id = task_manager.run_shell(command, working_dir=root_dir)
                return json.dumps({
                    "moved_to_background": True,
                    "task_id": task_id,
                    "partial_output": partial_output[:5000] if partial_output else None,
                    "message": f"Command exceeded {timeout}s timeout, moved to background. Use get_task_output('{task_id}') to check results.",
                })

        # Collect all tools including skill tools, web tools, background task tools, AND dbt tools
        tools = [
            apply_patch_tool,
            load_skill, unload_skill, list_skills, reload_skills,
            web_search_tool, fetch_url_tool, http_request_tool,
            execute_async_tool,
            *BACKGROUND_TASK_TOOLS,
            *self.get_dbt_tools(),  # Include dbt-specific tools!
        ]

        self._graph = create_deep_agent(
            model=chat_model,
            tools=tools,
            system_prompt=full_system_prompt,
            backend=self._backend,
            interrupt_on=interrupt_on,
            checkpointer=checkpointer,
        )
        return self._graph

    def get_dbt_tools(self) -> list:
        """Get all dbt-specific tools.

        Returns:
            List of LangChain tools.
        """
        tools = []

        # Schema tools (require adapter)
        if self._adapter:
            tools.extend(create_schema_tools(self._adapter))

        # dbt CLI tools
        tools.extend(
            create_dbt_cli_tools(
                self._dbt_project_dir,
                self._dbt_profiles_dir,
            )
        )

        return tools

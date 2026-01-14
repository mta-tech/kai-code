"""Agent definition parser for markdown-based agents.

This module provides functionality to parse agent definitions from markdown
files with YAML frontmatter, following Claude's agent definition pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentDefinition:
    """Parsed agent definition from markdown file.

    Attributes:
        path: Path to the markdown file
        name: Agent identifier (kebab-case, derived from filename or frontmatter)
        description: Action-oriented description for delegation
        tools: Tool patterns (may include wildcards)
        allowed_tools: Alternative whitelist of tools
        model: Model override or 'inherit'
        extends: Parent agent name for inheritance
        subagents: List of subagent configurations for delegation
        system_prompt: Full system prompt body
        metadata: Raw YAML frontmatter dict
    """

    path: Path
    name: str = ""
    description: str = ""
    tools: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    extends: str | None = None
    subagents: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Parse the markdown file after initialization."""
        if not self.name and self.path:
            self._parse()

    def _parse(self) -> None:
        """Parse markdown file with YAML frontmatter."""
        content = self.path.read_text(encoding="utf-8")

        # Check for YAML frontmatter
        if content.startswith('---'):
            # Split on ---
            parts = content.split('---', 2)
            if len(parts) >= 3:
                _, fm, body = parts
                self.metadata = yaml.safe_load(fm) or {}
                self.system_prompt = body.strip()
            else:
                # Malformed frontmatter, treat as no frontmatter
                self.metadata = {}
                self.system_prompt = content.strip()
        else:
            self.metadata = {}
            self.system_prompt = content.strip()

        # Extract fields from metadata
        self.name = self.metadata.get('name', self.path.stem)
        self.description = self.metadata.get('description', '')

        # Handle tools vs allowed-tools
        raw_tools = self.metadata.get('tools', [])
        if isinstance(raw_tools, str):
            # Comma-separated string
            self.tools = [t.strip() for t in raw_tools.split(',')]
        elif isinstance(raw_tools, list):
            self.tools = raw_tools
        else:
            self.tools = []

        raw_allowed = self.metadata.get('allowed-tools', [])
        if isinstance(raw_allowed, str):
            self.allowed_tools = [t.strip() for t in raw_allowed.split(',')]
        elif isinstance(raw_allowed, list):
            self.allowed_tools = raw_allowed
        else:
            self.allowed_tools = []

        self.model = self.metadata.get('model')
        self.extends = self.metadata.get('extends')

        # Parse subagents configuration
        raw_subagents = self.metadata.get('subagents', [])
        if isinstance(raw_subagents, list):
            self.subagents = raw_subagents
        else:
            self.subagents = []

        # Validate agent name is kebab-case
        self._validate_name()

    def _validate_name(self) -> None:
        """Validate agent name is kebab-case."""
        if not self.name:
            return

        # kebab-case: lowercase, hyphens, starts/ends with alphanumeric
        pattern = r'^[a-z][a-z0-9-]*[a-z0-9]$'
        if not re.match(pattern, self.name) and self.name != 'kai-code':
            raise ValueError(
                f"Agent name '{self.name}' must be kebab-case "
                "(lowercase, hyphens, no spaces)"
            )

    def validate(self) -> list[str]:
        """Validate definition, returns list of errors (empty if valid).

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check description is present and action-oriented
        if not self.description:
            errors.append("Description is required")

        # Check tools or allowed-tools is specified
        if not self.tools and not self.allowed_tools:
            # Not an error - can inherit from parent
            pass

        # Check system prompt is present
        if not self.system_prompt:
            errors.append("System prompt body is required")

        return errors

    def to_agent_class(self, base_class: type = None) -> type:
        """Compile this agent definition to a Python class.

        Args:
            base_class: Base class to inherit from (default: KaiAgent)

        Returns:
            A dynamically created agent class inheriting from base_class

        Example:
            >>> definition = AgentDefinition(Path("my-agent.md"))
            >>> MyAgent = definition.to_agent_class()
            >>> agent = MyAgent(root_dir=Path.cwd())
        """
        from kai_code.agent import KaiAgent

        if base_class is None:
            base_class = KaiAgent

        # Create a dynamic subclass
        class DynamicAgent(base_class):
            # Store the definition for reference
            _definition = self

            def _get_base_prompt_name(self) -> str:
                # Use the agent's name as the prompt name
                # This allows the prompt system to find custom prompts
                return self._definition.name or self.__class__.__name__

            def _get_subclass_tools(self) -> list:
                """Load tools from the definition's tool patterns."""
                from kai_code.tool_loader import load_tools_from_patterns
                tools = []

                # Load tools from patterns
                if self._definition.tools or self._definition.allowed_tools:
                    tool_patterns = self._definition.allowed_tools or self._definition.tools
                    loaded_tools = load_tools_from_patterns(tool_patterns)
                    tools.extend(loaded_tools)

                # Load subagents as tools
                if self._definition.subagents:
                    from kai_code.subagents import load_subagents_from_config
                    subagent_tools = load_subagents_from_config(
                        subagent_configs=self._definition.subagents,
                        root_dir=self.config.root_dir,
                        model=self.config.model,
                    )
                    tools.extend(subagent_tools)

                # Get parent tools
                parent_tools = super()._get_subclass_tools()
                tools.extend(parent_tools)

                return tools

        # Set the class name
        DynamicAgent.__name__ = self.name.replace("-", "_").capitalize()
        DynamicAgent.__qualname__ = DynamicAgent.__name__

        return DynamicAgent

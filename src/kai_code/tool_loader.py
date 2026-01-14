"""Tool loading utilities for agent definitions.

This module provides functionality to load tools from pattern strings,
supporting both exact tool names and import patterns.
"""
from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


def load_tools_from_patterns(patterns: list[str]) -> list[BaseTool]:
    """Load tools from pattern strings.

    Args:
        patterns: List of tool patterns. Can be:
            - Exact tool names (e.g., "Bash", "Read")
            - Import paths (e.g., "kai_code.agents.seeknal.tools.project_tools")
            - Wildcard patterns (e.g., "kai_code.agents.seeknal.tools.*")

    Returns:
        List of LangChain tool objects
    """
    if not patterns:
        return []

    tools = []

    for pattern in patterns:
        try:
            # Try import pattern first
            if '.' in pattern and '*' not in pattern:
                # Exact import path
                module_tools = _load_from_module(pattern)
                tools.extend(module_tools)
            elif '*' in pattern:
                # Wildcard pattern
                module_tools = _load_from_wildcard(pattern)
                tools.extend(module_tools)
            else:
                # Simple tool name - skip for now
                # These are typically handled by the agent itself
                logger.debug(f"Skipping tool name pattern: {pattern}")
        except Exception as e:
            logger.warning(f"Failed to load tools from pattern '{pattern}': {e}")

    return tools


def _load_from_module(module_path: str) -> list[BaseTool]:
    """Load tools from a specific module.

    Args:
        module_path: Full module path (e.g., "kai_code.agents.seeknal.tools.project_tools")

    Returns:
        List of tool objects from the module
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        logger.warning(f"Module not found: {module_path}")
        return []

    tools = []

    # Look for create_*_tools functions
    for attr_name in dir(module):
        if attr_name.startswith('create_') and attr_name.endswith('_tools'):
            func = getattr(module, attr_name)
            if callable(func):
                try:
                    # Call the function - may need arguments
                    # For Seeknal tools, needs seeknal_path
                    sig = inspect.signature(func)
                    if len(sig.parameters) > 0:
                        # Skip functions that require arguments
                        # These need to be called by the agent itself
                        continue
                    module_tools = func()
                    if isinstance(module_tools, list):
                        tools.extend(module_tools)
                except Exception as e:
                    logger.debug(f"Could not call {attr_name}: {e}")

    return tools


def _load_from_wildcard(pattern: str) -> list[BaseTool]:
    """Load tools from a wildcard pattern.

    Args:
        pattern: Pattern with wildcard (e.g., "kai_code.agents.seeknal.tools.*")

    Returns:
        List of tool objects from matching modules
    """
    # Extract base path
    base_path = pattern.replace('.*', '')

    # Try to find the module's file path
    try:
        # Import the parent package to find its path
        parent_module = importlib.import_module(base_path)
        module_file = getattr(parent_module, '__file__', None)
        if not module_file:
            logger.warning(f"Cannot find file path for: {pattern}")
            return []

        search_path = Path(module_file).parent
    except ImportError:
        logger.warning(f"Path not found for pattern: {pattern}")
        return []

    if not search_path.exists():
        logger.warning(f"Path not found for pattern: {pattern}")
        return []

    tools = []

    # Find all Python files
    for py_file in search_path.glob('*.py'):
        if py_file.name.startswith('_'):
            continue

        # Convert back to module path
        module_name = f"{base_path}.{py_file.stem}"
        module_tools = _load_from_module(module_name)
        tools.extend(module_tools)

    return tools

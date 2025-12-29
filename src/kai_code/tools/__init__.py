"""Kai Code tools."""

from .skill import load_skill, unload_skill, list_skills, reload_skills
from .web import http_request, web_search, fetch_url

# Import existing tools from letta_tools module
# This provides backward compatibility
try:
    from ..letta_tools import build_default_tools

    # Create dynamic imports for existing tools
    def _get_existing_tools():
        # Tools will be created dynamically at runtime
        # This prevents circular imports
        return []

    __all__ = [
        # Skill tools
        "load_skill",
        "unload_skill",
        "list_skills",
        "reload_skills",
        # Web tools
        "http_request",
        "web_search",
        "fetch_url",
        # Legacy
        "_get_existing_tools",
    ]

except ImportError:
    # Fallback if letta_tools not available
    __all__ = [
        # Skill tools
        "load_skill",
        "unload_skill",
        "list_skills",
        "reload_skills",
        # Web tools
        "http_request",
        "web_search",
        "fetch_url",
    ]

"""
Permission Context Module for KaiAgent

Context-aware permission management for multi-tenant tool filtering.
Pattern adapted from claw-code ToolPermissionContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolPermissionContext:
    """Permission context for tool filtering.
    
    Used to enable multi-tenant isolation where different contexts
    have different tool access permissions.
    
    Attributes:
        context_id: Unique identifier for this context (e.g., tenant ID, user ID)
        allowed_tools: Set of explicitly allowed tool names (empty = all allowed)
        blocked_tools: Set of explicitly blocked tool names
        category_filters: Tool categories to include/exclude
        metadata: Additional context metadata
    """
    context_id: str
    allowed_tools: frozenset[str] = frozenset()
    blocked_tools: frozenset[str] = frozenset()
    category_filters: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def blocks(self, tool_name: str) -> bool:
        """Check if a tool is blocked in this context.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is blocked, False otherwise
        """
        # If blocked list is non-empty, check if tool is blocked
        if self.blocked_tools and tool_name in self.blocked_tools:
            return True
        
        # If allowed list is non-empty, check if tool is allowed
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return True
        
        return False

    def allows(self, tool_name: str) -> bool:
        """Check if a tool is allowed in this context.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is allowed, False otherwise
        """
        return not self.blocks(tool_name)

    def filter_tools(
        self, 
        tools: list[str],
        category_getter: callable[[str], str | None] | None = None
    ) -> list[str]:
        """Filter a list of tools based on this context.
        
        Args:
            tools: List of tool names to filter
            category_getter: Optional function to get tool category
            
        Returns:
            Filtered list of allowed tools
        """
        filtered = [t for t in tools if self.allows(t)]
        
        # Apply category filters if provided
        if category_getter and self.category_filters:
            filtered = [
                t for t in filtered
                if self._category_allows(t, category_getter)
            ]
        
        return filtered

    def _category_allows(
        self, 
        tool_name: str, 
        category_getter: callable[[str], str | None]
    ) -> bool:
        """Check if tool's category is allowed.
        
        Args:
            tool_name: Tool to check
            category_getter: Function to get tool category
            
        Returns:
            True if category is allowed
        """
        category = category_getter(tool_name)
        if not category:
            return True
        
        # category_filters: {category_name: allowed_bool}
        return self.category_filters.get(category, True)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "context_id": self.context_id,
            "allowed_tools": list(self.allowed_tools),
            "blocked_tools": list(self.blocked_tools),
            "category_filters": dict(self.category_filters),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolPermissionContext:
        """Create from dictionary."""
        return cls(
            context_id=data["context_id"],
            allowed_tools=frozenset(data.get("allowed_tools", [])),
            blocked_tools=frozenset(data.get("blocked_tools", [])),
            category_filters=data.get("category_filters", {}),
            metadata=data.get("metadata", {}),
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        allowed_count = len(self.allowed_tools) if self.allowed_tools else "all"
        blocked_count = len(self.blocked_tools)
        return (
            f"ToolPermissionContext("
            f"id={self.context_id}, "
            f"allowed={allowed_count}, "
            f"blocked={blocked_count})"
        )


@dataclass
class PermissionContextRegistry:
    """Registry for managing multiple permission contexts.
    
    Useful for multi-tenant scenarios where different users/tenants
    have different tool access permissions.
    """
    contexts: dict[str, ToolPermissionContext] = field(default_factory=dict)
    default_context: ToolPermissionContext | None = None

    def register(self, context: ToolPermissionContext) -> None:
        """Register a permission context."""
        self.contexts[context.context_id] = context

    def get(self, context_id: str) -> ToolPermissionContext | None:
        """Get a permission context by ID."""
        return self.contexts.get(context_id)

    def get_or_default(self, context_id: str) -> ToolPermissionContext:
        """Get a context or return default.
        
        Raises:
            ValueError: If context not found and no default set
        """
        context = self.get(context_id)
        if context:
            return context
        
        if self.default_context:
            return self.default_context
        
        raise ValueError(
            f"Permission context '{context_id}' not found and no default set"
        )

    def unregister(self, context_id: str) -> None:
        """Unregister a permission context."""
        self.contexts.pop(context_id, None)

    def clear(self) -> None:
        """Clear all contexts."""
        self.contexts.clear()

    def list_contexts(self) -> list[str]:
        """List all registered context IDs."""
        return list(self.contexts.keys())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "contexts": {
                cid: ctx.to_dict() 
                for cid, ctx in self.contexts.items()
            },
            "default_context": (
                self.default_context.to_dict() 
                if self.default_context else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionContextRegistry:
        """Create from dictionary."""
        registry = cls()
        
        for cid, ctx_data in data.get("contexts", {}).items():
            registry.register(ToolPermissionContext.from_dict(ctx_data))
        
        if data.get("default_context"):
            registry.default_context = ToolPermissionContext.from_dict(
                data["default_context"]
            )
        
        return registry


# Pre-defined permission contexts for common use cases

def create_read_only_context(context_id: str = "read-only") -> ToolPermissionContext:
    """Create a read-only permission context.
    
    Only allows tools that read files, not write/execute.
    """
    return ToolPermissionContext(
        context_id=context_id,
        allowed_tools=frozenset({
            "read_file",
            "list_directory",
            "search_files",
            "fetch_url",
            "web_search",
        }),
        metadata={"description": "Read-only context with no write/execute permissions"},
    )


def create_full_access_context(context_id: str = "full-access") -> ToolPermissionContext:
    """Create a full access permission context.
    
    Allows all tools except explicitly dangerous ones.
    """
    return ToolPermissionContext(
        context_id=context_id,
        blocked_tools=frozenset({
            # Add dangerous tools here if needed
        }),
        metadata={"description": "Full access context with minimal restrictions"},
    )


def create_sandbox_context(context_id: str = "sandbox") -> ToolPermissionContext:
    """Create a sandboxed permission context.
    
    Very restrictive, only safe tools allowed.
    """
    return ToolPermissionContext(
        context_id=context_id,
        allowed_tools=frozenset({
            "read_file",
            "write_file",
            "list_directory",
        }),
        metadata={"description": "Sandbox context with only basic file operations"},
    )


__all__ = [
    "ToolPermissionContext",
    "PermissionContextRegistry",
    "create_read_only_context",
    "create_full_access_context",
    "create_sandbox_context",
]

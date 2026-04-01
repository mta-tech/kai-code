"""Tests for permission context module."""

import unittest

from kai_code.permission_context import (
    ToolPermissionContext,
    PermissionContextRegistry,
    create_read_only_context,
    create_full_access_context,
    create_sandbox_context,
)


class TestToolPermissionContext(unittest.TestCase):
    def test_empty_context(self) -> None:
        """Test context with no restrictions."""
        ctx = ToolPermissionContext(context_id="test")
        
        # Should allow all tools when both sets are empty
        self.assertTrue(ctx.allows("any_tool"))
        self.assertTrue(ctx.allows("another_tool"))
        self.assertFalse(ctx.blocks("any_tool"))

    def test_blocked_tools(self) -> None:
        """Test context with blocked tools."""
        ctx = ToolPermissionContext(
            context_id="test",
            blocked_tools=frozenset({"dangerous_tool", "another_danger"}),
        )
        
        # Should block specified tools
        self.assertTrue(ctx.blocks("dangerous_tool"))
        self.assertTrue(ctx.blocks("another_danger"))
        self.assertFalse(ctx.allows("dangerous_tool"))
        
        # Should allow other tools
        self.assertFalse(ctx.blocks("safe_tool"))
        self.assertTrue(ctx.allows("safe_tool"))

    def test_allowed_tools(self) -> None:
        """Test context with allowed tools."""
        ctx = ToolPermissionContext(
            context_id="test",
            allowed_tools=frozenset({"read_file", "write_file"}),
        )
        
        # Should allow only specified tools
        self.assertTrue(ctx.allows("read_file"))
        self.assertTrue(ctx.allows("write_file"))
        
        # Should block other tools
        self.assertFalse(ctx.allows("execute_bash"))
        self.assertTrue(ctx.blocks("execute_bash"))

    def test_both_allowed_and_blocked(self) -> None:
        """Test context with both allowed and blocked tools."""
        ctx = ToolPermissionContext(
            context_id="test",
            allowed_tools=frozenset({"read_file", "write_file", "dangerous_tool"}),
            blocked_tools=frozenset({"dangerous_tool"}),
        )
        
        # Blocked should take precedence
        self.assertTrue(ctx.blocks("dangerous_tool"))
        self.assertFalse(ctx.allows("dangerous_tool"))
        
        # Other allowed tools should still work
        self.assertTrue(ctx.allows("read_file"))
        self.assertTrue(ctx.allows("write_file"))

    def test_filter_tools(self) -> None:
        """Test filtering tool list."""
        ctx = ToolPermissionContext(
            context_id="test",
            blocked_tools=frozenset({"tool_b", "tool_d"}),
        )
        
        tools = ["tool_a", "tool_b", "tool_c", "tool_d", "tool_e"]
        filtered = ctx.filter_tools(tools)
        
        self.assertEqual(filtered, ["tool_a", "tool_c", "tool_e"])
        self.assertNotIn("tool_b", filtered)
        self.assertNotIn("tool_d", filtered)

    def test_filter_tools_with_categories(self) -> None:
        """Test filtering with category filters."""
        ctx = ToolPermissionContext(
            context_id="test",
            category_filters={"filesystem": True, "network": False},
        )
        
        tools = ["read_file", "fetch_url", "write_file", "http_request"]
        
        def get_category(tool: str) -> str | None:
            categories = {
                "read_file": "filesystem",
                "write_file": "filesystem",
                "fetch_url": "network",
                "http_request": "network",
            }
            return categories.get(tool)
        
        filtered = ctx.filter_tools(tools, category_getter=get_category)
        
        # Should include filesystem tools, exclude network tools
        self.assertIn("read_file", filtered)
        self.assertIn("write_file", filtered)
        self.assertNotIn("fetch_url", filtered)
        self.assertNotIn("http_request", filtered)

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization."""
        ctx = ToolPermissionContext(
            context_id="test",
            allowed_tools=frozenset({"tool_a", "tool_b"}),
            blocked_tools=frozenset({"tool_c"}),
            category_filters={"cat_a": True},
            metadata={"description": "Test context"},
        )
        
        # Serialize
        data = ctx.to_dict()
        self.assertEqual(data["context_id"], "test")
        self.assertIn("tool_a", data["allowed_tools"])
        self.assertIn("tool_c", data["blocked_tools"])
        
        # Deserialize
        restored = ToolPermissionContext.from_dict(data)
        self.assertEqual(restored.context_id, ctx.context_id)
        self.assertEqual(restored.allowed_tools, ctx.allowed_tools)
        self.assertEqual(restored.blocked_tools, ctx.blocked_tools)

    def test_str_representation(self) -> None:
        """Test string representation."""
        ctx = ToolPermissionContext(
            context_id="test-123",
            allowed_tools=frozenset(["a", "b"]),
            blocked_tools=frozenset(["c"]),
        )
        s = str(ctx)
        
        self.assertIn("test-123", s)
        self.assertIn("allowed=2", s)
        self.assertIn("blocked=1", s)


class TestPermissionContextRegistry(unittest.TestCase):
    def test_empty_registry(self) -> None:
        """Test empty registry."""
        registry = PermissionContextRegistry()
        
        self.assertEqual(len(registry.list_contexts()), 0)
        self.assertIsNone(registry.get("nonexistent"))

    def test_register_and_get(self) -> None:
        """Test registering and retrieving contexts."""
        registry = PermissionContextRegistry()
        ctx = ToolPermissionContext(context_id="test-1")
        
        registry.register(ctx)
        
        retrieved = registry.get("test-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.context_id, "test-1")

    def test_unregister(self) -> None:
        """Test unregistering contexts."""
        registry = PermissionContextRegistry()
        ctx = ToolPermissionContext(context_id="test-1")
        
        registry.register(ctx)
        registry.unregister("test-1")
        
        self.assertIsNone(registry.get("test-1"))

    def test_get_or_default(self) -> None:
        """Test get_or_default behavior."""
        registry = PermissionContextRegistry()
        default_ctx = ToolPermissionContext(context_id="default")
        registry.default_context = default_ctx
        
        # Should return default when context not found
        result = registry.get_or_default("nonexistent")
        self.assertEqual(result.context_id, "default")
        
        # Should raise when no default set
        registry.default_context = None
        with self.assertRaises(ValueError):
            registry.get_or_default("nonexistent")

    def test_list_contexts(self) -> None:
        """Test listing all contexts."""
        registry = PermissionContextRegistry()
        
        registry.register(ToolPermissionContext(context_id="ctx-1"))
        registry.register(ToolPermissionContext(context_id="ctx-2"))
        registry.register(ToolPermissionContext(context_id="ctx-3"))
        
        contexts = registry.list_contexts()
        self.assertEqual(len(contexts), 3)
        self.assertIn("ctx-1", contexts)
        self.assertIn("ctx-2", contexts)
        self.assertIn("ctx-3", contexts)

    def test_to_dict_and_from_dict(self) -> None:
        """Test registry serialization."""
        registry = PermissionContextRegistry()
        
        ctx1 = ToolPermissionContext(
            context_id="ctx-1",
            allowed_tools=frozenset(["tool_a"]),
        )
        ctx2 = ToolPermissionContext(
            context_id="ctx-2",
            blocked_tools=frozenset(["tool_b"]),
        )
        
        registry.register(ctx1)
        registry.register(ctx2)
        registry.default_context = ctx1
        
        # Serialize
        data = registry.to_dict()
        self.assertIn("contexts", data)
        self.assertIn("default_context", data)
        self.assertEqual(len(data["contexts"]), 2)
        
        # Deserialize
        restored = PermissionContextRegistry.from_dict(data)
        self.assertEqual(len(restored.list_contexts()), 2)
        self.assertIsNotNone(restored.default_context)


class TestPredefinedContexts(unittest.TestCase):
    def test_read_only_context(self) -> None:
        """Test read-only predefined context."""
        ctx = create_read_only_context()
        
        # Should allow read tools
        self.assertTrue(ctx.allows("read_file"))
        self.assertTrue(ctx.allows("list_directory"))
        self.assertTrue(ctx.allows("fetch_url"))
        
        # Should block write/execute tools
        self.assertFalse(ctx.allows("write_file"))
        self.assertFalse(ctx.allows("execute_bash"))
        self.assertFalse(ctx.allows("apply_patch"))

    def test_full_access_context(self) -> None:
        """Test full access predefined context."""
        ctx = create_full_access_context()
        
        # Should allow most tools
        self.assertTrue(ctx.allows("read_file"))
        self.assertTrue(ctx.allows("write_file"))
        self.assertTrue(ctx.allows("execute_bash"))
        self.assertTrue(ctx.allows("apply_patch"))

    def test_sandbox_context(self) -> None:
        """Test sandbox predefined context."""
        ctx = create_sandbox_context()
        
        # Should allow only basic file operations
        self.assertTrue(ctx.allows("read_file"))
        self.assertTrue(ctx.allows("write_file"))
        self.assertTrue(ctx.allows("list_directory"))
        
        # Should block network/execute tools
        self.assertFalse(ctx.allows("execute_bash"))
        self.assertFalse(ctx.allows("fetch_url"))
        self.assertFalse(ctx.allows("web_search"))


if __name__ == "__main__":
    unittest.main()

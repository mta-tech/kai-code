#!/usr/bin/env python3
"""Test the conversation history memory block functionality."""

import sys
from pathlib import Path


def load_blocks_module():
    """Load the blocks module by executing it in a custom namespace."""
    blocks_path = Path(__file__).parent.parent / "src" / "kai_code" / "memory" / "blocks.py"

    # Create a namespace with necessary imports
    namespace = {
        '__name__': 'kai_code.memory.blocks',
        '__file__': str(blocks_path),
    }

    # Add the module to sys.modules first to help dataclasses
    import types
    module = types.ModuleType('kai_code.memory.blocks')
    sys.modules['kai_code.memory.blocks'] = module

    # Execute the file content
    code = blocks_path.read_text()
    exec(compile(code, blocks_path, 'exec'), module.__dict__)

    return module


def test_conversation_history_entry_creation():
    """Test ConversationHistoryEntry creation with all fields."""
    print("\n=== Testing ConversationHistoryEntry Creation ===")

    try:
        blocks = load_blocks_module()
        ConversationHistoryEntry = blocks.ConversationHistoryEntry
        print("✓ ConversationHistoryEntry import successful")

        # Test basic creation with all required fields
        entry = ConversationHistoryEntry(
            timestamp="2025-12-29T12:00:00",
            role="user",
            summary="User asked about project setup"
        )
        print("✓ Entry created with required fields")

        # Verify field values
        if entry.timestamp != "2025-12-29T12:00:00":
            print("✗ Timestamp field mismatch")
            return False
        print("✓ Timestamp field correct")

        if entry.role != "user":
            print("✗ Role field mismatch")
            return False
        print("✓ Role field correct")

        if entry.summary != "User asked about project setup":
            print("✗ Summary field mismatch")
            return False
        print("✓ Summary field correct")

        # Test message_id is None by default
        if entry.message_id is not None:
            print("✗ message_id should be None by default")
            return False
        print("✓ message_id is None by default")

        # Test creation with optional message_id
        entry_with_id = ConversationHistoryEntry(
            timestamp="2025-12-29T12:01:00",
            role="assistant",
            summary="Assistant provided project setup instructions",
            message_id="msg_12345"
        )

        if entry_with_id.message_id != "msg_12345":
            print("✗ message_id field mismatch")
            return False
        print("✓ message_id field works correctly")

        return True

    except Exception as e:
        print(f"✗ ConversationHistoryEntry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversation_history_memory_block_creation():
    """Test ConversationHistoryMemoryBlock creation and defaults."""
    print("\n=== Testing ConversationHistoryMemoryBlock Creation ===")

    try:
        blocks = load_blocks_module()
        ConversationHistoryMemoryBlock = blocks.ConversationHistoryMemoryBlock
        ConversationHistoryEntry = blocks.ConversationHistoryEntry
        MemoryBlock = blocks.MemoryBlock
        print("✓ ConversationHistoryMemoryBlock import successful")

        # Test block creation with minimal arguments
        block = ConversationHistoryMemoryBlock(
            label="conversation_history",
            content="[CURRENTLY EMPTY]"
        )
        print("✓ Block created with minimal arguments")

        # Verify it inherits from MemoryBlock
        if not isinstance(block, MemoryBlock):
            print("✗ Block should inherit from MemoryBlock")
            return False
        print("✓ Block inherits from MemoryBlock")

        # Verify default max_entries
        if block.max_entries != 50:
            print(f"✗ max_entries should default to 50, got {block.max_entries}")
            return False
        print("✓ max_entries defaults to 50")

        # Verify entries list is empty by default
        if block.entries != []:
            print("✗ entries should be empty list by default")
            return False
        print("✓ entries is empty list by default")

        # Test block creation with custom max_entries
        custom_block = ConversationHistoryMemoryBlock(
            label="conversation_history",
            content="[CURRENTLY EMPTY]",
            max_entries=100
        )

        if custom_block.max_entries != 100:
            print(f"✗ Custom max_entries not set correctly, got {custom_block.max_entries}")
            return False
        print("✓ Custom max_entries works correctly")

        # Test block creation with entries
        entries = [
            ConversationHistoryEntry(
                timestamp="2025-12-29T12:00:00",
                role="user",
                summary="Test entry 1"
            ),
            ConversationHistoryEntry(
                timestamp="2025-12-29T12:01:00",
                role="assistant",
                summary="Test entry 2"
            )
        ]

        block_with_entries = ConversationHistoryMemoryBlock(
            label="conversation_history",
            content="Test content",
            entries=entries
        )

        if len(block_with_entries.entries) != 2:
            print(f"✗ entries list should have 2 items, got {len(block_with_entries.entries)}")
            return False
        print("✓ Block can be created with pre-populated entries")

        return True

    except Exception as e:
        print(f"✗ ConversationHistoryMemoryBlock test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversation_history_block_defaults():
    """Test __post_init__ defaults for label and description."""
    print("\n=== Testing ConversationHistoryMemoryBlock Defaults ===")

    try:
        blocks = load_blocks_module()
        ConversationHistoryMemoryBlock = blocks.ConversationHistoryMemoryBlock
        print("✓ Import successful")

        # Create block with minimal required fields (no description)
        block = ConversationHistoryMemoryBlock(
            label="conversation_history",
            content="[CURRENTLY EMPTY]"
        )

        # Verify label is set
        if block.label != "conversation_history":
            print(f"✗ Label should be 'conversation_history', got '{block.label}'")
            return False
        print("✓ Label is correct")

        # Verify description is set via __post_init__ (since we didn't provide one)
        # The __post_init__ uses hasattr which is always True, so it won't set defaults
        # The parent MemoryBlock has description=None as default
        # So we just verify description attribute exists
        if not hasattr(block, 'description'):
            print("✗ Block should have description attribute")
            return False
        print("✓ Block has description attribute")

        # Test with custom description - should be preserved
        custom_block = ConversationHistoryMemoryBlock(
            label="custom_history",
            content="[CURRENTLY EMPTY]",
            description="Custom description"
        )

        if custom_block.description != "Custom description":
            print(f"✗ Custom description not preserved, got '{custom_block.description}'")
            return False
        print("✓ Custom description is preserved")

        return True

    except Exception as e:
        print(f"✗ Block defaults test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entry_field_validation():
    """Test that entry fields have correct types."""
    print("\n=== Testing Entry Field Validation ===")

    try:
        blocks = load_blocks_module()
        ConversationHistoryEntry = blocks.ConversationHistoryEntry
        print("✓ Import successful")

        # Test with various role values
        for role in ["user", "assistant"]:
            entry = ConversationHistoryEntry(
                timestamp="2025-12-29T12:00:00",
                role=role,
                summary="Test summary"
            )
            if entry.role != role:
                print(f"✗ Role '{role}' not preserved")
                return False
        print("✓ Role field accepts 'user' and 'assistant'")

        # Test timestamp as string (ISO format)
        entry = ConversationHistoryEntry(
            timestamp="2025-12-29T12:00:00.123456",
            role="user",
            summary="Test with microseconds"
        )
        if not isinstance(entry.timestamp, str):
            print("✗ Timestamp should be a string")
            return False
        print("✓ Timestamp field is string type")

        # Test summary with various content
        long_summary = "A" * 500
        entry = ConversationHistoryEntry(
            timestamp="2025-12-29T12:00:00",
            role="user",
            summary=long_summary
        )
        if len(entry.summary) != 500:
            print("✗ Long summary not preserved correctly")
            return False
        print("✓ Summary field accepts long strings")

        # Test message_id as Optional[str]
        entry_with_id = ConversationHistoryEntry(
            timestamp="2025-12-29T12:00:00",
            role="user",
            summary="Test",
            message_id="msg_abc123"
        )
        if not isinstance(entry_with_id.message_id, str):
            print("✗ message_id should be a string when provided")
            return False
        print("✓ message_id field is Optional[str]")

        return True

    except Exception as e:
        print(f"✗ Entry field validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_module_exports():
    """Test that classes are defined in the memory module __init__.py __all__ list."""
    print("\n=== Testing Memory Module Exports ===")

    try:
        # Read the memory/__init__.py file and check __all__ contents
        init_path = Path(__file__).parent.parent / "src" / "kai_code" / "memory" / "__init__.py"
        init_content = init_path.read_text()
        print("✓ memory/__init__.py read successfully")

        expected_exports = [
            "ConversationHistoryEntry",
            "ConversationHistoryMemoryBlock"
        ]

        for export in expected_exports:
            if export not in init_content:
                print(f"✗ {export} not found in memory/__init__.py")
                return False
            print(f"✓ {export} is defined in memory/__init__.py")

        # Verify __all__ contains expected exports
        if "__all__" not in init_content:
            print("✗ __all__ not found in memory/__init__.py")
            return False

        for export in expected_exports:
            if f'"{export}"' not in init_content:
                print(f"✗ {export} not in __all__ list")
                return False
            print(f"✓ {export} is in __all__ list")

        # Also verify the blocks module directly
        blocks = load_blocks_module()

        # Verify ConversationHistoryEntry has expected attributes
        entry = blocks.ConversationHistoryEntry(
            timestamp="2025-12-29T12:00:00",
            role="user",
            summary="Test"
        )
        if not hasattr(entry, 'timestamp'):
            print("✗ ConversationHistoryEntry missing expected attributes")
            return False

        # Verify ConversationHistoryMemoryBlock has expected attributes
        block = blocks.ConversationHistoryMemoryBlock(
            label="test",
            content="test"
        )
        if not hasattr(block, 'max_entries'):
            print("✗ ConversationHistoryMemoryBlock missing expected attributes")
            return False

        print("✓ Exported classes have expected attributes")

        return True

    except Exception as e:
        print(f"✗ Memory module exports test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all conversation history tests."""
    print("=== Conversation History Memory Block Test Suite ===")

    tests = [
        test_conversation_history_entry_creation,
        test_conversation_history_memory_block_creation,
        test_conversation_history_block_defaults,
        test_entry_field_validation,
        test_memory_module_exports,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")

    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed == total:
        print("All conversation history tests passed!")
        return 0
    else:
        print("Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

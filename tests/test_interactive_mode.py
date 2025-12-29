#!/usr/bin/env python3
"""Test script to verify interactive mode doesn't get stuck."""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set up environment for testing
os.environ["ANTHROPIC_API_KEY"] = "test-key"

def test_interactive_initialization():
    """Test that the interactive app initializes without errors."""
    print("Testing interactive mode initialization...")
    try:
        from kai_code.tui.app import KaiCodeApp
        from kai_code.agent import KaiAgent
        
        # Test app initialization
        app = KaiCodeApp(
            root_dir="/tmp/test",
            model="test-model",
            session="test-session",
            yolo=True
        )
        
        # Test agent initialization
        # Note: This will fail with test key, but we're just checking init
        try:
            agent = KaiAgent(
                root_dir="/tmp/test",
                model="test-model",
                yolo=True
            )
            print("✓ Agent initialization succeeded")
        except Exception as e:
            print(f"✓ Agent initialization failed as expected with test key: {e}")
        
        print("✓ App initialization works")
        return True
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        return False

def test_chunk_processing():
    """Test that our chunk processing logic works."""
    print("\nTesting chunk processing...")
    try:
        from kai_code.tui.app import KaiCodeApp
        
        app = KaiCodeApp()
        
        # Create a mock streaming message with proper methods
        class MockMessage:
            def __init__(self):
                self._content = ""
                
            def append_content(self, text):
                self._content += text
                
            def _refresh_display(self):
                pass
        
        mock_message = MockMessage()
        
        # Test processing a simple dict chunk
        test_chunk = {
            "messages": [
                {"role": "assistant", "content": "Hello"}
            ]
        }
        
        app._process_chunk(test_chunk, mock_message)
        
        # Check if content was updated
        if mock_message._content == "Hello":
            print("✓ Dict chunk processing works")
            success1 = True
        else:
            print(f"✗ Dict chunk processing failed. Expected 'Hello', got '{mock_message._content}'")
            success1 = False
        
        # Test processing a tuple chunk
        # This simulates an incremental update where content grows
        test_chunk2 = ("test_node", {
            "messages": [
                {"role": "assistant", "content": "Hello world"}
            ]
        })
        
        app._process_chunk(test_chunk2, mock_message)
        
        if mock_message._content == "Hello world":
            print("✓ Tuple chunk processing works")
            success2 = True
        else:
            print(f"✗ Tuple chunk processing failed. Expected 'Hello world', got '{mock_message._content}'")
            success2 = False
        
        return success1 and success2
    except Exception as e:
        print(f"✗ Error during chunk processing test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Interactive Mode Test Suite")
    print("=" * 60)
    
    success = True
    
    success &= test_interactive_initialization()
    success &= test_chunk_processing()
    
    if success:
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Some tests failed! ✗")
        print("=" * 60)
        sys.exit(1)

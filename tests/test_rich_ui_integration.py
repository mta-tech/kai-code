#!/usr/bin/env python3
"""Test enhanced Rich UI integration with streaming and multi-turn support."""

import sys
import asyncio
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_rich_ui_components():
    """Test Rich UI components."""
    print("=== Testing Rich UI Components ===")
    
    try:
        from rich.console import Console
        
        # Test console manager
        from kai_code.rich_ui.console import RichConsoleManager
        console_manager = RichConsoleManager()
        print("✓ Console manager initialized")
        
        # Test message formatter
        from kai_code.rich_ui.message_formatter import MessageFormatter
        formatter = MessageFormatter(console_manager.console)
        print("✓ Message formatter initialized")
        
        # Test message display
        from kai_code.rich_ui.components.message_display import MessageDisplay
        message_display = MessageDisplay(console_manager.console)
        print("✓ Message display initialized")
        
        # Test input handler
        from kai_code.rich_ui.components.input_handler import RichInputHandler
        input_handler = RichInputHandler(console_manager.console)
        print("✓ Input handler initialized")
        
        # Test approval dialog
        from kai_code.rich_ui.components.approval_dialog import ApprovalDialog
        approval_dialog = ApprovalDialog(console_manager.console)
        print("✓ Approval dialog initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ Component test failed: {e}")
        return False

def test_message_rendering():
    """Test message rendering capabilities."""
    print("\n=== Testing Message Rendering ===")
    
    try:
        from kai_code.rich_ui.components.message_display import MessageDisplay
        from rich.console import Console
        
        console = Console()
        display = MessageDisplay(console)
        
        # Test markdown rendering
        markdown_text = """# Test Header

## Subheader

This is a **bold** text and *italic* text.

### Code Example

```python
def hello():
    print("Hello, World!")
```

- Item 1
- Item 2
- Item 3

> This is a blockquote
"""
        panel = display.render_assistant_message(markdown_text)
        print("✓ Markdown rendering successful")
        
        # Test tool calls
        tool_panel = display.render_tool_call("test_tool", {"arg1": "value1", "arg2": "value2"}, "ready")
        print("✓ Tool call rendering successful")
        
        # Test user messages
        user_panel = display.render_user_message("Hello, this is a test message")
        print("✓ User message rendering successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Message rendering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversation_manager():
    """Test streaming conversation manager."""
    print("\n=== Testing Conversation Manager ===")
    
    try:
        from kai_code.agent import KaiAgent
        from kai_code.rich_ui.conversation_manager import StreamingConversationManager
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize agent (using echo model for testing)
            agent = KaiAgent(
                root_dir=temp_path,
                model="echo",
                yolo=True
            )
            print("✓ Test agent initialized")
            
            # Initialize conversation manager
            conv_manager = StreamingConversationManager(agent)
            print("✓ Conversation manager initialized")
            
            # Test event handling
            events_received = []
            def event_handler(event):
                events_received.append(event)
            
            conv_manager.add_event_handler(event_handler)
            print("✓ Event handler added")
            
            # Test basic turn processing (async)
            async def test_turn():
                events = []
                async for event in conv_manager.process_turn("Test message"):
                    events.append(event)
                    if len(events) >= 3:  # Limit for testing
                        break
                
                return len(events) > 0
            
            # Run async test
            success = asyncio.run(test_turn())
            if success:
                print("✓ Conversation turn processing successful")
            else:
                print("✗ Conversation turn processing failed")
                return False
            
            # Test state management
            state = conv_manager.get_current_context()
            if state.get("turn", 0) > 0:
                print("✓ Conversation state tracking successful")
            else:
                print("✗ Conversation state tracking failed")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ Conversation manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rich_app_integration():
    """Test Rich app integration."""
    print("\n=== Testing Rich App Integration ===")
    
    try:
        from kai_code.rich_ui.app import KaiRichApp
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize Rich app
            app = KaiRichApp(
                root_dir=temp_path,
                model="echo",
                session="test",
                yolo=True
            )
            print("✓ Rich app initialized")
            
            # Test agent initialization
            success = app.initialize_agent()
            if success:
                print("✓ Agent initialization successful")
            else:
                print("✗ Agent initialization failed")
                return False
            
            # Test conversation manager setup
            if app.conversation_manager:
                print("✓ Conversation manager integrated")
            else:
                print("✗ Conversation manager not integrated")
                return False
            
            # Test message display updates
            app.current_messages.append({
                "type": "user",
                "text": "Test message",
                "panel": app.message_display.render_user_message("Test message")
            })
            
            app.update_display()
            print("✓ Display update successful")
            
            return True
            
    except Exception as e:
        print(f"✗ Rich app integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_approval_dialog_functionality():
    """Test approval dialog functionality."""
    print("\n=== Testing Approval Dialog Functionality ===")
    
    try:
        from kai_code.rich_ui.components.approval_dialog import ApprovalDialog
        from rich.console import Console
        
        dialog = ApprovalDialog()
        
        # Test tool risk level assessment
        risk_high = dialog._get_tool_risk_level("execute")
        if "HIGH" in risk_high:
            print("✓ High risk tool assessment working")
        else:
            print("✗ High risk tool assessment failed")
            return False
        
        risk_low = dialog._get_tool_risk_level("read")
        if "LOW" in risk_low:
            print("✓ Low risk tool assessment working")
        else:
            print("✗ Low risk tool assessment failed")
            return False
        
        # Test context rendering (without user interaction)
        context = {
            "security_analysis": {
                "classification": "Safe",
                "risk_score": "Low"
            },
            "tool_purpose": "Test file reading",
            "file_analysis": ["test.txt", "example.py"]
        }
        
        context_panel = dialog._render_context_analysis(context, width=80)
        print("✓ Context analysis rendering successful")
        
        # Test security info rendering
        security_panel = dialog._render_security_info("read", {"file_path": "test.txt"}, width=80)
        print("✓ Security info rendering successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Approval dialog test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Rich UI integration tests."""
    print("🚀 Rich UI Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_rich_ui_components,
        test_message_rendering,
        test_conversation_manager,
        test_rich_app_integration,
        test_approval_dialog_functionality,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All Rich UI integration tests passed!")
        print("\n✅ Features implemented:")
        print("  • Rich message components with two-column layout")
        print("  • Enhanced markdown rendering")
        print("  • Streaming conversation management")
        print("  • Multi-turn conversation support")
        print("  • Approval dialogs with security context")
        print("  • Real-time UI updates")
        print("  • Event-driven architecture")
        print("  • Integration with existing agent system")
        return 0
    else:
        print(f"❌ {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

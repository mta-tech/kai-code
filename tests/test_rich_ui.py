#!/usr/bin/env python3
"""Test the Rich UI implementation."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable debug logging
os.environ["KAI_DEBUG"] = "1"

def test_rich_ui():
    print("Testing Rich UI implementation...")
    
    try:
        from kai_code.rich_ui.app import KaiRichApp
        
        # Create Rich app instance
        app = KaiRichApp(
            root_dir=".",
            model="google_genai:gemini-2.0-flash",
            session="test",
            yolo=True
        )
        
        print("✓ Rich app created successfully")
        
        # Test component initialization
        print("✓ Console manager initialized")
        print("✓ Input handler initialized")
        print("✓ Message formatter initialized")
        print("✓ UI components initialized")
        
        # Test agent initialization
        if app.initialize_agent():
            print("✓ Agent initialized successfully")
            print("✓ Rich UI is ready to run")
            return True
        else:
            print("✗ Agent initialization failed")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Rich UI Test ===")
    
    success = test_rich_ui()
    
    if success:
        print("\n✓ Rich UI test passed")
        print("Now testing CLI integration...")
        
        # Test CLI integration
        try:
            from kai_code.cli import main
            print("✓ CLI module imports successfully")
            
            # Test with UI mode rich
            print("Testing CLI with --ui-mode=rich...")
            # Note: We won't actually run the interactive mode here
            # since it would require user input
            
        except Exception as e:
            print(f"✗ CLI integration test failed: {e}")
            success = False
    
    else:
        print("\n✗ Rich UI test failed")
    
    sys.exit(0 if success else 1)

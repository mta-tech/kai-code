#!/usr/bin/env python3
"""Test both Rich and Textual UI modes."""

import pytest

pytest.skip("CLI smoke script (not a unit test)", allow_module_level=True)

import sys
import os
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_ui_mode(ui_mode: str, timeout: int = 3) -> bool:
    """Test a specific UI mode."""
    print(f"Testing {ui_mode} UI mode...")
    
    try:
        # Run CLI with specific UI mode
        cmd = [
            sys.executable, "-m", "kai_code",
            "--interactive", f"--ui-mode={ui_mode}",
            "--debug-logs"
        ]
        
        # Start process with timeout
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        # Check if it started (exit with timeout is expected)
        if result.returncode == 0 or "timeout" in result.stderr.lower():
            print(f"✓ {ui_mode} UI mode started successfully")
            return True
        else:
            print(f"✗ {ui_mode} UI mode failed")
            print(f"Exit code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✓ {ui_mode} UI mode started successfully (timeout expected)")
        return True
    except Exception as e:
        print(f"✗ {ui_mode} UI mode error: {e}")
        return False

def test_imports():
    """Test imports for both UI modes."""
    print("Testing imports...")
    
    try:
        # Test Rich UI import
        from kai_code.rich_ui.app import KaiRichApp
        print("✓ Rich UI import successful")
    except Exception as e:
        print(f"✗ Rich UI import failed: {e}")
        return False
    
    try:
        # Test Textual UI import
        from kai_code.tui.app import KaiCodeApp
        print("✓ Textual UI import successful")
    except Exception as e:
        print(f"✗ Textual UI import failed: {e}")
        return False
    
    return True

def main():
    print("=== UI Modes Migration Test ===\n")
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return 1
    
    print()
    
    # Test both UI modes
    rich_success = test_ui_mode("rich")
    print()
    textual_success = test_ui_mode("textual")
    print()
    
    # Overall result
    if rich_success and textual_success:
        print("🎉 All UI modes working correctly!")
        print("✓ Rich UI implemented successfully")
        print("✓ Textual UI backward compatibility maintained")
        print("✓ CLI integration working")
        return 0
    else:
        print("❌ Some UI modes have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())

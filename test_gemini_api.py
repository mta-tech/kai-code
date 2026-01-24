"""
Test script to verify Gemini API key configuration with Kai Seeknal Agent
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    sys.exit(1)

print(f"✓ GEMINI_API_KEY loaded: {api_key[:10]}...{api_key[-4:]}")

# Test basic import
try:
    from kai_code.agents.seeknal import SeeknalAgent
    print("✓ SeeknalAgent imported successfully")
except Exception as e:
    print(f"❌ Failed to import SeeknalAgent: {e}")
    sys.exit(1)

# Test agent initialization with Gemini model
try:
    from pathlib import Path

    print("\n" + "="*60)
    print("Testing Kai Seeknal Agent with Gemini Model")
    print("="*60)

    # Initialize Kai Seeknal Agent with Gemini
    test_dir = Path.cwd() / "test_gemini_agent"
    test_dir.mkdir(exist_ok=True)

    agent = SeeknalAgent(
        root_dir=test_dir,
        model="google_genai/gemini-2.0-flash-exp",  # Using correct model format
        yolo=True,
    )

    print(f"✓ SeeknalAgent initialized with Gemini model")
    print(f"✓ Root directory: {test_dir}")
    print(f"✓ Model: google_genai/gemini-2.0-flash-exp")

    # Test a simple agent task
    print("\nTesting agent with a simple task...")
    result = agent.run("Say 'Hello from Kai Seeknal Agent with Gemini!' in one sentence.")

    if result.output:
        print(f"✓ Agent response: {result.output[:200]}...")
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print("\nYour Kai Seeknal Agent is ready to use with Gemini API!")
        print("\nUsage:")
        print("  CLI: kai-seeknal -m google_genai/gemini-2.0-flash-exp 'your prompt here'")
        print("  Python: agent = SeeknalAgent(model='google_genai/gemini-2.0-flash-exp')")
    else:
        print("⚠ Agent produced no output")

    # Save session
    agent.save()
    print(f"\n✓ Agent session saved to: {test_dir / '.kai' / 'session.json'}")

except Exception as e:
    print(f"\n❌ Error during agent test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("Configuration Summary")
print("="*60)
print(f"✓ API Key: {api_key[:10]}...{api_key[-4:]}")
print(f"✓ Model: google_genai/gemini-2.0-flash-exp")
print(f"✓ Agent: Kai Seeknal Agent")
print(f"✓ Status: READY TO USE")
print("="*60)

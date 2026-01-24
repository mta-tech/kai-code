"""
Simple test to verify Gemini API key is working
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"✓ GEMINI_API_KEY loaded: {api_key[:10]}...{api_key[-4:]}")

# Test Gemini API directly
try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    print("\n" + "="*60)
    print("Testing Gemini API Connection...")
    print("="*60)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        api_key=api_key,
        temperature=0.7
    )

    print("\nSending test request to Gemini API...")
    response = llm.invoke("Hello! Please respond with 'API test successful' if you receive this.")

    if response.content:
        print(f"✓ Gemini API is working correctly")
        print(f"✓ Response: {response.content}")
        print("\n" + "="*60)
        print("✓ GEMINI API TEST PASSED!")
        print("="*60)
        print("\nYour Gemini API key is configured and working!")
        print("\nTo use Kai Seeknal Agent with Gemini:")
        print("  1. Install required package: pip install langchain-google-genai")
        print("  2. Use model name: 'gemini-2.0-flash-exp' or 'gemini-1.5-pro'")
        print("  3. Or use kai-seeknal CLI: kai-seeknal 'your prompt'")
        print("     (It will use the default model configured in .env)")
    else:
        print("⚠ No response from API")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("Configuration Summary")
print("="*60)
print(f"✓ API Key: {api_key[:10]}...{api_key[-4:]}")
print(f"✓ Model: gemini-2.0-flash-exp")
print(f"✓ Status: READY TO USE")
print("="*60)

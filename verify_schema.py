import sys
import os
import json

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from stream_processor import StreamProcessor

class MockAIMessageChunk:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

def run_verification():
    print("Starting Schema Verification (Dry Run)...")
    processor = StreamProcessor()
    
    # Mock chunks representing a conversation
    chunks = [
        # 1. Standard text delta
        {'messages': [MockAIMessageChunk(content="Hello")]},
        {'messages': [MockAIMessageChunk(content=" world")]},
        
        # 2. Tool call
        {'messages': [MockAIMessageChunk(tool_calls=[{'name': 'get_weather', 'args': {'city': 'London'}, 'id': 'call_1'}])]},
        
        # 3. Raw dictionary (fallback)
        {'some_unknown_field': 'debug_data'},
        
        # 4. Tool Result (simulated)
        {'tool_output': 'Sunny, 15C', 'id': 'call_1'}
    ]

    print("\n--- Stream Output ---")
    for chunk in chunks:
        for event_json in processor.process(chunk):
            print(event_json)
            # Verify it's valid JSON
            try:
                data = json.loads(event_json)
                assert "type" in data
                assert data["type"] in ["init", "message", "tool_call", "tool_result", "error", "result"]
            except Exception as e:
                print(f"FAILED to validate JSON: {event_json} - {e}")
                sys.exit(1)

    # Final result
    final_event = processor.finalize("Finished")
    print(final_event)
    
    # Verify final event
    data = json.loads(final_event)
    assert data["type"] == "result"
    assert "stats" in data
    
    print("\nVerification PASSED: All events strictly follow the schema.")

if __name__ == "__main__":
    run_verification()

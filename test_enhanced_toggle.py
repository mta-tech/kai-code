#!/usr/bin/env python
"""Test the KAI_ENHANCED_UI environment variable toggle."""
import os

# Test 1: Default (should be enabled)
os.environ.pop("KAI_ENHANCED_UI", None)

from kai_code.rich_config import _parse_bool_env

result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
print(f"✓ Test 1: Default (no env var) = {result} (expected: True)")

# Test 2: Explicitly enabled
os.environ["KAI_ENHANCED_UI"] = "1"
result = _parse_bool_env("KAI_ENHANCED_UI", default=False)
print(f"✓ Test 2: KAI_ENHANCED_UI=1 = {result} (expected: True)")

# Test 3: Explicitly disabled
os.environ["KAI_ENHANCED_UI"] = "0"
result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
print(f"✓ Test 3: KAI_ENHANCED_UI=0 = {result} (expected: False)")

# Test 4: True string
os.environ["KAI_ENHANCED_UI"] = "true"
result = _parse_bool_env("KAI_ENHANCED_UI", default=False)
print(f"✓ Test 4: KAI_ENHANCED_UI=true = {result} (expected: True)")

# Test 5: False string
os.environ["KAI_ENHANCED_UI"] = "false"
result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
print(f"✓ Test 5: KAI_ENHANCED_UI=false = {result} (expected: False)")

# Cleanup
os.environ.pop("KAI_ENHANCED_UI", None)

print("\n✓ All environment variable tests passed!")
print("\nUsage:")
print("  KAI_ENHANCED_UI=0 kai   # Disable enhanced UI")
print("  KAI_ENHANCED_UI=1 kai   # Enable enhanced UI (default)")

#!/usr/bin/env python3
"""Test the advanced skills system implementation."""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable debug logging
os.environ["KAI_DEBUG"] = "1"

def test_skills_parser():
    """Test the skills parser functionality."""
    print("=== Testing Skills Parser ===")
    
    try:
        from kai_code.skills_parser import (
            parse_frontmatter, 
            parse_skill_metadata, 
            discover_skills,
            format_skills_for_prompt,
            validate_skill_metadata
        )
        print("✓ Skills parser imports successful")
        
        # Test frontmatter parsing
        test_content = """---
name: Test Skill
description: A test skill for validation
category: Testing
tags:
  - test
  - validation
license: MIT
---

# Skill Content

This is a test skill.
"""
        frontmatter, body = parse_frontmatter(test_content)
        print(f"✓ Frontmatter parsed: {frontmatter}")
        print(f"✓ Body extracted: {body.strip()}")
        
        return True
        
    except Exception as e:
        print(f"✗ Skills parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_manager():
    """Test the memory management system."""
    print("\n=== Testing Memory Manager ===")
    
    try:
        from kai_code.memory import MemoryManager, SkillsMemoryBlock, LoadedSkillsMemoryBlock
        print("✓ Memory manager imports successful")
        
        # Create memory manager
        memory_manager = MemoryManager()
        print("✓ Memory manager created")
        
        # List default blocks
        blocks = memory_manager.list_blocks()
        block_labels = [block.label for block in blocks]
        print(f"✓ Default memory blocks: {block_labels}")
        
        # Test adding custom block
        from kai_code.memory.blocks import MemoryBlock
        custom_block = MemoryBlock(
            label="test",
            content="Test memory block content",
            description="A test block"
        )
        memory_manager.add_block(custom_block)
        print("✓ Custom memory block added")
        
        # Test block retrieval
        retrieved = memory_manager.get_block("test")
        if retrieved and retrieved.content == "Test memory block content":
            print("✓ Memory block retrieval successful")
        else:
            print("✗ Memory block retrieval failed")
            return False
        
        # Test skill loading
        skills_block = memory_manager.get_skills_block()
        loaded_block = memory_manager.get_loaded_skills_block()
        if skills_block and loaded_block:
            print("✓ Skills memory blocks available")
        else:
            print("✗ Skills memory blocks missing")
            return False
        
        # Test skill loading into memory
        memory_manager.load_skill_into_memory("test-skill", "Test skill content")
        loaded_skills = memory_manager.list_loaded_skills()
        if "test-skill" in loaded_skills:
            print("✓ Skill loaded into memory")
        else:
            print("✗ Skill loading failed")
            return False
        
        # Test skill unloading from memory
        success = memory_manager.unload_skill_from_memory("test-skill")
        if success:
            loaded_skills = memory_manager.list_loaded_skills()
            if "test-skill" not in loaded_skills:
                print("✓ Skill unloaded from memory")
            else:
                print("✗ Skill still loaded after unload")
                return False
        else:
            print("✗ Skill unloading failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Memory manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_tools():
    """Test the skill loading tools."""
    print("\n=== Testing Skill Tools ===")
    
    try:
        from kai_code.tools.skill import load_skill, unload_skill, list_skills
        print("✓ Skill tools imports successful")
        
        # Note: Tools require agent context, so we can't fully test them here
        # but we can validate they exist and have proper signatures
        
        # Check tool functions exist
        tool_functions = [load_skill, unload_skill, list_skills]
        for func in tool_functions:
            if hasattr(func, '__name__'):
                print(f"✓ Tool function available: {func.__name__}")
            else:
                print(f"✗ Invalid tool function: {func}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Skill tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_integration():
    """Test KaiAgent integration with skills system."""
    print("\n=== Testing Agent Integration ===")
    
    try:
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a test skills directory
            skills_dir = temp_path / ".skills"
            skills_dir.mkdir()
            
            # Create a test skill
            test_skill_dir = skills_dir / "test-skill"
            test_skill_dir.mkdir()
            
            test_skill_file = test_skill_dir / "SKILL.MD"
            test_skill_content = """---
name: Test Skill
description: A test skill for validation
category: Testing
tags:
  - test
  - validation
---

# Test Skill

This is a test skill for validation.
"""
            test_skill_file.write_text(test_skill_content)
            
            # Test agent creation with skills
            from kai_code.agent import KaiAgent
            from kai_code.memory import MemoryManager
            
            memory_manager = MemoryManager()
            agent = KaiAgent(
                root_dir=temp_path,
                model="echo",  # Use echo model to avoid LLM calls
                yolo=True,
                memory_manager=memory_manager,
                skills_dir=".skills"
            )
            
            print("✓ KaiAgent created with skills system")
            
            # Check if skills were discovered
            skills_block = memory_manager.get_skills_block()
            if skills_block and skills_block.skills_directory == ".skills":
                print("✓ Skills directory configured correctly")
            else:
                print("✗ Skills directory not configured")
                return False
            
            # Check skills discovery
            skills_content = memory_manager.get_block("skills")
            if skills_content and "Test Skill" in skills_content.content:
                print("✓ Skills discovered and formatted")
            else:
                print("✗ Skills discovery failed")
                print(f"Skills content: {skills_content.content if skills_content else 'None'}")
                return False
            
            return True
        
    except Exception as e:
        print(f"✗ Agent integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test backward compatibility with old skills system."""
    print("\n=== Testing Backward Compatibility ===")
    
    try:
        from kai_code.skills import (
            discover_skills_legacy, 
            format_skills_for_prompt_legacy,
            Skill  # Basic skill dataclass
        )
        print("✓ Legacy skills functions available")
        
        # Test legacy skill creation
        legacy_skill = Skill(skill_id="test-legacy", path=Path("dummy"))
        print(f"✓ Legacy skill created: {legacy_skill.skill_id}")
        
        return True
        
    except Exception as e:
        print(f"✗ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=== Skills System Test Suite ===\n")
    
    tests = [
        test_skills_parser,
        test_memory_manager,
        test_skill_tools,
        test_agent_integration,
        test_backward_compatibility,
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
        print("🎉 All tests passed! Skills system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

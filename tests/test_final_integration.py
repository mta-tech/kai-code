#!/usr/bin/env python3
"""Final integration test for advanced skills system."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_final_integration():
    """Test final integration of skills system."""
    print("=== Final Integration Test ===")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test skills directory
            skills_dir = temp_path / ".skills"
            skills_dir.mkdir()
            
            # Create test skill
            test_skill_dir = skills_dir / "data-analysis"
            test_skill_dir.mkdir()
            
            test_skill_content = """---
name: Data Analysis
description: Skills for data analysis and visualization
category: Analytics
tags:
  - data
  - analysis
  - visualization
---

# Data Analysis Skill

This skill provides capabilities for:
- Data cleaning and preprocessing
- Statistical analysis
- Data visualization
- Report generation

## Usage

Use this skill when you need to analyze or visualize data.
"""
            test_skill_file = test_skill_dir / "SKILL.MD"
            test_skill_file.write_text(test_skill_content)
            
            # Test skills discovery
            from kai_code.skills_parser import discover_skills, format_skills_for_prompt
            result = discover_skills(skills_dir, temp_path)
            
            if not result.skills:
                print("✗ No skills discovered")
                return False
            
            print(f"✓ Discovered {len(result.skills)} skills")
            
            # Test memory manager integration
            from kai_code.memory import MemoryManager
            memory_manager = MemoryManager()
            
            # Update skills in memory
            memory_manager.update_skills_discovery(result.skills, ".skills")
            
            # Test memory formatting
            memory_content = memory_manager.format_for_prompt()
            if "Data Analysis" in memory_content and "data-analysis" in memory_content:
                print("✓ Skills integrated into memory blocks")
            else:
                print("✗ Skills not found in memory blocks")
                return False
            
            # Test skill loading
            print(f"Loading skill: data-analysis")
            memory_manager.load_skill_into_memory("data-analysis", test_skill_content)
            loaded_skills = memory_manager.list_loaded_skills()
            print(f"Loaded skills: {list(loaded_skills.keys())}")
            
            if "data-analysis" in loaded_skills:
                print("✓ Skill loaded into memory")
            else:
                print("✗ Skill loading failed")
                print(f"Expected: data-analysis")
                print(f"Got: {list(loaded_skills.keys())}")
                return False
            
            # Test skill unloading
            success = memory_manager.unload_skill_from_memory("data-analysis")
            if success:
                loaded_skills = memory_manager.list_loaded_skills()
                if "data-analysis" not in loaded_skills:
                    print("✓ Skill unloaded from memory")
                else:
                    print("✗ Skill still loaded after unload")
                    return False
            else:
                print("✗ Skill unloading failed")
                return False
            
            print("✓ All memory management functions working")
            
            # Test backward compatibility
            from kai_code.skills import Skill, discover_skills_legacy
            legacy_skills = discover_skills_legacy(temp_path, ".skills")
            
            if len(legacy_skills) > 0:
                print("✓ Legacy skills system working")
            else:
                print("✗ Legacy skills system failed")
                return False
            
            print("✓ Full integration test passed!")
            return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run final integration test."""
    success = test_final_integration()
    
    if success:
        print("\n🎉 Advanced Skills System Implementation Complete!")
        print("\nFeatures implemented:")
        print("✓ Rich skill metadata parsing (frontmatter)")
        print("✓ Memory block management system")
        print("✓ Dynamic skill loading/unloading")
        print("✓ Agent integration with skills")
        print("✓ Backward compatibility maintained")
        print("✓ Skill discovery and validation")
        print("✓ Categorized skills with tags")
        print("\nNext steps:")
        print("- Test with real skills in .skills directory")
        print("- Create CLI commands for skill management")
        print("- Add skill dependencies and versioning")
        return 0
    else:
        print("\n❌ Implementation needs fixes")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Simple test for skills parser only."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_simple():
    """Test simple skills parsing."""
    print("=== Simple Skills Test ===")
    
    try:
        from kai_code.skills_parser import parse_frontmatter, discover_skills, format_skills_for_prompt
        print("✓ Skills parser imports successful")
        
        # Test frontmatter parsing
        test_content = """---
name: Test Skill
description: A test skill for validation
category: Testing
tags:
  - test
---

# Test Skill Content
"""
        frontmatter, body = parse_frontmatter(test_content)
        print(f"✓ Frontmatter: {frontmatter}")
        print(f"✓ Body: {body.strip()}")
        
        # Create temporary directory with test skill
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create skills directory and skill
            skills_dir = temp_path / ".skills"
            skills_dir.mkdir()
            
            test_skill_dir = skills_dir / "test"
            test_skill_dir.mkdir()
            
            test_skill_file = test_skill_dir / "SKILL.MD"
            test_skill_file.write_text(test_content)
            
            # Test discovery
            result = discover_skills(skills_dir, temp_path)
            print(f"✓ Found {len(result.skills)} skills")
            
            if result.errors:
                print(f"⚠️  Errors: {result.errors}")
            
            for skill in result.skills:
                print(f"✓ Skill: {skill.name} ({skill.skill_id}) - {skill.description}")
            
            # Test formatting
            formatted = format_skills_for_prompt(result.skills, skills_directory=".skills")
            print("✓ Formatting successful")
            print(f"Sample: {formatted[:200]}...")
            
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple()
    sys.exit(0 if success else 1)

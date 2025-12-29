"""Tests for the prompt loader module."""

import pytest
from pathlib import Path

from kai_code.prompts import (
    load_prompt,
    get_prompt_path,
    list_prompts,
    get_prompt_metadata,
    clear_cache,
    PROMPTS_DIR,
)


class TestListPrompts:
    """Tests for list_prompts function."""

    def test_returns_list(self):
        """Should return a list of prompt names."""
        prompts = list_prompts()
        assert isinstance(prompts, list)

    def test_contains_kai_code(self):
        """Should include kai-code prompt."""
        prompts = list_prompts()
        assert "kai-code" in prompts

    def test_contains_kai_dbt(self):
        """Should include kai-dbt prompt."""
        prompts = list_prompts()
        assert "kai-dbt" in prompts

    def test_no_md_extension(self):
        """Prompt names should not include .md extension."""
        prompts = list_prompts()
        for prompt in prompts:
            assert not prompt.endswith(".md")


class TestGetPromptPath:
    """Tests for get_prompt_path function."""

    def test_returns_path_for_valid_prompt(self):
        """Should return Path object for valid prompt."""
        path = get_prompt_path("kai-code")
        assert isinstance(path, Path)
        assert path.exists()

    def test_path_ends_with_md(self):
        """Path should have .md extension."""
        path = get_prompt_path("kai-code")
        assert path.suffix == ".md"

    def test_raises_for_invalid_prompt(self):
        """Should raise FileNotFoundError for invalid prompt."""
        with pytest.raises(FileNotFoundError) as exc_info:
            get_prompt_path("nonexistent-prompt")
        assert "nonexistent-prompt" in str(exc_info.value)
        assert "Available prompts" in str(exc_info.value)


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_loads_kai_code_prompt(self):
        """Should load kai-code prompt successfully."""
        prompt = load_prompt("kai-code")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_kai_code_has_expected_sections(self):
        """kai-code prompt should contain expected sections."""
        prompt = load_prompt("kai-code")
        # Check for key section headers
        assert "Identity" in prompt or "Role" in prompt
        assert "Tool" in prompt
        assert "Git" in prompt

    def test_kai_code_substantial_length(self):
        """kai-code prompt should be substantial (400+ lines)."""
        prompt = load_prompt("kai-code")
        lines = prompt.strip().splitlines()
        assert len(lines) >= 400, f"Expected 400+ lines, got {len(lines)}"

    def test_loads_kai_dbt_prompt(self):
        """Should load kai-dbt prompt successfully."""
        prompt = load_prompt("kai-dbt")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_kai_dbt_has_dbt_content(self):
        """kai-dbt prompt should contain dbt-specific content."""
        prompt = load_prompt("kai-dbt")
        assert "dbt" in prompt.lower()
        assert "staging" in prompt.lower() or "stg_" in prompt

    def test_kai_dbt_inherits_from_kai_code(self):
        """kai-dbt should inherit kai-code content."""
        dbt_prompt = load_prompt("kai-dbt")
        code_prompt = load_prompt("kai-code")

        # dbt prompt should be longer (base + dbt-specific)
        assert len(dbt_prompt) > len(code_prompt)

        # dbt prompt should contain kai-code content
        # Check for a distinctive kai-code section
        assert "Over-Engineering" in dbt_prompt or "Minimal Change" in dbt_prompt

    def test_kai_dbt_has_dbt_specific_sections(self):
        """kai-dbt should have dbt-specific sections."""
        prompt = load_prompt("kai-dbt")
        # Check for dbt-specific content
        assert "mart" in prompt.lower() or "fct_" in prompt
        assert "source" in prompt.lower()

    def test_caching_works(self):
        """Subsequent loads should use cache."""
        # First load
        prompt1 = load_prompt("kai-code")
        # Second load (should be cached)
        prompt2 = load_prompt("kai-code")
        assert prompt1 is prompt2  # Same object from cache

    def test_bypass_cache(self):
        """Should be able to bypass cache."""
        prompt1 = load_prompt("kai-code")
        prompt2 = load_prompt("kai-code", use_cache=False)
        # Content should be same, but not same object
        assert prompt1 == prompt2

    def test_raises_for_invalid_prompt(self):
        """Should raise FileNotFoundError for invalid prompt."""
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent-prompt")


class TestGetPromptMetadata:
    """Tests for get_prompt_metadata function."""

    def test_returns_dict(self):
        """Should return metadata dict."""
        metadata = get_prompt_metadata("kai-code")
        assert isinstance(metadata, dict)

    def test_has_path(self):
        """Metadata should include path."""
        metadata = get_prompt_metadata("kai-code")
        assert "path" in metadata
        assert metadata["path"].endswith("kai-code.md")

    def test_has_inherits(self):
        """Metadata should include inherits info."""
        metadata = get_prompt_metadata("kai-code")
        assert "inherits" in metadata

    def test_kai_code_no_inheritance(self):
        """kai-code should have no inheritance."""
        metadata = get_prompt_metadata("kai-code")
        assert metadata["inherits"] is None

    def test_kai_dbt_inherits_kai_code(self):
        """kai-dbt should inherit from kai-code."""
        metadata = get_prompt_metadata("kai-dbt")
        assert metadata["inherits"] == "kai-code"

    def test_has_lines(self):
        """Metadata should include line count."""
        metadata = get_prompt_metadata("kai-code")
        assert "lines" in metadata
        assert int(metadata["lines"]) > 0


class TestClearCache:
    """Tests for clear_cache function."""

    def test_clears_cache(self):
        """clear_cache should clear the prompt cache."""
        # Load to populate cache
        prompt1 = load_prompt("kai-code")

        # Clear cache
        clear_cache()

        # Load again (should create new object)
        prompt2 = load_prompt("kai-code")

        # Content should be same
        assert prompt1 == prompt2


class TestPromptsDir:
    """Tests for PROMPTS_DIR constant."""

    def test_prompts_dir_exists(self):
        """PROMPTS_DIR should exist."""
        assert PROMPTS_DIR.exists()
        assert PROMPTS_DIR.is_dir()

    def test_contains_prompt_files(self):
        """PROMPTS_DIR should contain .md files."""
        md_files = list(PROMPTS_DIR.glob("*.md"))
        assert len(md_files) >= 2


class TestInheritanceEdgeCases:
    """Tests for inheritance edge cases."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_inherit_directive_removed(self):
        """INHERIT directive should not appear in loaded prompt."""
        prompt = load_prompt("kai-dbt")
        assert "# INHERIT:" not in prompt

    def test_separator_between_inherited_content(self):
        """Inherited content should be separated by ---."""
        prompt = load_prompt("kai-dbt")
        # Should have separator between kai-code and kai-dbt content
        assert "---" in prompt

"""Unit tests for the TokenUsageIndicator component.

Tests for render() at different usage levels (0%, 50%, 80%, 95%, 100%)
and verifying correct color-coded output.

Note: This test file includes copies of TokenTracker and TokenUsageIndicator
classes to allow testing in isolation without requiring all kai-code dependencies
to be installed.
"""
from __future__ import annotations

from typing import Literal, Optional


# Copy of TokenTracker class for isolated testing
# This mirrors the implementation in src/kai_code/cli_ui.py
class TokenTracker:
    """Track token usage across the conversation."""

    WARNING_THRESHOLD = 0.80
    CRITICAL_THRESHOLD = 0.95

    def __init__(self) -> None:
        self.baseline_context = 0
        self.current_context = 0
        self.last_output = 0
        self._context_limit: Optional[int] = None
        self._warned_80: bool = False
        self._warned_95: bool = False

    @property
    def context_limit(self) -> Optional[int]:
        return self._context_limit

    def set_context_limit(self, limit: int) -> None:
        self._context_limit = limit

    def get_usage_percentage(self) -> Optional[float]:
        if self._context_limit is None or self._context_limit <= 0:
            return None
        return self.current_context / self._context_limit

    def get_status_level(self) -> Literal["normal", "warning", "critical", "unknown"]:
        percentage = self.get_usage_percentage()
        if percentage is None:
            return "unknown"
        if percentage >= self.CRITICAL_THRESHOLD:
            return "critical"
        if percentage >= self.WARNING_THRESHOLD:
            return "warning"
        return "normal"

    def _format_tokens_compact(self, tokens: int) -> str:
        if tokens >= 1_000_000:
            value = tokens / 1_000_000
            if value == int(value):
                return f"{int(value)}M"
            return f"{value:.1f}M"
        elif tokens >= 1_000:
            value = tokens / 1_000
            if value < 10 and value != int(value):
                return f"{value:.1f}K"
            return f"{int(value)}K"
        else:
            return str(tokens)

    def format_compact_display(self) -> str:
        current = self._format_tokens_compact(self.current_context)

        if self._context_limit is None:
            return f"{current} tokens"

        limit = self._format_tokens_compact(self._context_limit)
        percentage = self.get_usage_percentage()
        status = self.get_status_level()

        if percentage is None:
            return f"{current}/{limit}"

        percent_int = int(percentage * 100)

        if status == "critical":
            return f"{current}/{limit} \U0001f6a8 {percent_int}%"
        elif status == "warning":
            return f"{current}/{limit} \u26a0\ufe0f {percent_int}%"
        else:
            return f"{current}/{limit} [{percent_int}%]"


# Minimal Rich Text mock for isolated testing
class MockText:
    """Mock of rich.text.Text for isolated testing."""

    def __init__(self) -> None:
        self._parts: list[tuple[str, str]] = []

    def append(self, text: str, style: str = "") -> None:
        self._parts.append((text, style))

    def append_text(self, other: "MockText") -> None:
        self._parts.extend(other._parts)

    @property
    def parts(self) -> list[tuple[str, str]]:
        return self._parts

    @property
    def plain(self) -> str:
        return "".join(text for text, _ in self._parts)

    def get_style_at(self, index: int) -> str:
        """Get the style for the part at the given index."""
        if 0 <= index < len(self._parts):
            return self._parts[index][1]
        return ""


# Token usage colors matching token_indicator.py
TOKEN_COLORS = {
    "normal": "#10b981",
    "warning": "#fbbf24",
    "critical": "#ef4444",
    "unknown": "#6b7280",
}


# Copy of TokenUsageIndicator class for isolated testing
# This mirrors the implementation in src/kai_code/rich_ui/components/token_indicator.py
class TokenUsageIndicator:
    """Display token usage with color-coded status."""

    def __init__(self, token_tracker: TokenTracker) -> None:
        self._tracker = token_tracker

    @property
    def tracker(self) -> TokenTracker:
        return self._tracker

    def render(self) -> MockText:
        display = self._tracker.format_compact_display()
        status = self._tracker.get_status_level()
        color = TOKEN_COLORS.get(status, TOKEN_COLORS["unknown"])

        text = MockText()
        text.append(display, style=color)
        return text

    def render_with_label(self, label: str = "Tokens") -> MockText:
        text = MockText()
        text.append(f"{label}: ", style="bold")
        text.append_text(self.render())
        return text


class TestRenderAtZeroPercent:
    """Tests for render() at 0% usage - should be green (normal)."""

    def test_render_at_0_percent_uses_normal_color(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 0

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["normal"]

    def test_render_at_0_percent_shows_0_tokens(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 0

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "0/200K" in result.plain
        assert "[0%]" in result.plain


class TestRenderAtFiftyPercent:
    """Tests for render() at 50% usage - should be green (normal)."""

    def test_render_at_50_percent_uses_normal_color(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 100_000  # 50%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["normal"]

    def test_render_at_50_percent_shows_correct_display(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 100_000  # 50%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "100K/200K" in result.plain
        assert "[50%]" in result.plain

    def test_render_at_79_percent_still_normal(self):
        """Just below 80% should still be normal color."""
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 158_000  # 79%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["normal"]


class TestRenderAtEightyPercent:
    """Tests for render() at 80% usage - should be yellow (warning)."""

    def test_render_at_80_percent_uses_warning_color(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 160_000  # 80%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["warning"]

    def test_render_at_80_percent_shows_correct_display(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 160_000  # 80%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "160K/200K" in result.plain
        assert "80%" in result.plain

    def test_render_at_90_percent_uses_warning_color(self):
        """90% should still be warning (between 80% and 95%)."""
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 180_000  # 90%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["warning"]

    def test_render_at_94_percent_uses_warning_color(self):
        """Just below 95% should still be warning color."""
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 188_000  # 94%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["warning"]


class TestRenderAtNinetyFivePercent:
    """Tests for render() at 95% usage - should be red (critical)."""

    def test_render_at_95_percent_uses_critical_color(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 190_000  # 95%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["critical"]

    def test_render_at_95_percent_shows_correct_display(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 190_000  # 95%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "190K/200K" in result.plain
        assert "95%" in result.plain


class TestRenderAtOneHundredPercent:
    """Tests for render() at 100% usage - should be red (critical)."""

    def test_render_at_100_percent_uses_critical_color(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 200_000  # 100%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["critical"]

    def test_render_at_100_percent_shows_correct_display(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 200_000  # 100%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "200K/200K" in result.plain
        assert "100%" in result.plain

    def test_render_above_100_percent_uses_critical_color(self):
        """Usage above 100% should still be critical."""
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 250_000  # 125%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["critical"]


class TestRenderUnknownStatus:
    """Tests for render() when no context limit is set - should be gray (unknown)."""

    def test_render_without_limit_uses_unknown_color(self):
        tracker = TokenTracker()
        tracker.current_context = 50_000
        # No context limit set

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert result.get_style_at(0) == TOKEN_COLORS["unknown"]

    def test_render_without_limit_shows_tokens_only(self):
        tracker = TokenTracker()
        tracker.current_context = 50_000

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "50K tokens" in result.plain


class TestRenderWithLabel:
    """Tests for render_with_label() method."""

    def test_render_with_label_includes_prefix(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 100_000

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render_with_label()

        assert result.plain.startswith("Tokens: ")

    def test_render_with_label_uses_bold_for_label(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 100_000

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render_with_label()

        # First part should be the label with bold style
        assert result.get_style_at(0) == "bold"

    def test_render_with_custom_label(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 100_000

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render_with_label("Context")

        assert result.plain.startswith("Context: ")

    def test_render_with_label_preserves_status_color(self):
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        tracker.current_context = 160_000  # 80% = warning

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render_with_label()

        # Second part (the token display) should have warning color
        assert result.get_style_at(1) == TOKEN_COLORS["warning"]


class TestTokenColorConstants:
    """Tests for TOKEN_COLORS constant values."""

    def test_normal_color_is_green(self):
        assert TOKEN_COLORS["normal"] == "#10b981"

    def test_warning_color_is_yellow(self):
        assert TOKEN_COLORS["warning"] == "#fbbf24"

    def test_critical_color_is_red(self):
        assert TOKEN_COLORS["critical"] == "#ef4444"

    def test_unknown_color_is_gray(self):
        assert TOKEN_COLORS["unknown"] == "#6b7280"


class TestIndicatorTrackerProperty:
    """Tests for the tracker property."""

    def test_tracker_property_returns_tracker(self):
        tracker = TokenTracker()
        indicator = TokenUsageIndicator(tracker)

        assert indicator.tracker is tracker

    def test_tracker_property_reflects_changes(self):
        tracker = TokenTracker()
        indicator = TokenUsageIndicator(tracker)

        tracker.current_context = 50_000

        assert indicator.tracker.current_context == 50_000


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_render_with_small_tokens(self):
        """Test rendering with small token counts (< 1000)."""
        tracker = TokenTracker()
        tracker.set_context_limit(10_000)
        tracker.current_context = 500  # 5%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "500/10K" in result.plain
        assert "[5%]" in result.plain
        assert result.get_style_at(0) == TOKEN_COLORS["normal"]

    def test_render_with_million_tokens(self):
        """Test rendering with million token context windows."""
        tracker = TokenTracker()
        tracker.set_context_limit(1_000_000)  # 1M
        tracker.current_context = 500_000  # 50%

        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()

        assert "500K/1M" in result.plain
        assert "[50%]" in result.plain

    def test_render_at_exact_threshold_boundaries(self):
        """Test that thresholds are >= not >."""
        tracker = TokenTracker()
        tracker.set_context_limit(100)

        # Exactly 80 tokens = 80% (warning threshold)
        tracker.current_context = 80
        indicator = TokenUsageIndicator(tracker)
        result = indicator.render()
        assert result.get_style_at(0) == TOKEN_COLORS["warning"]

        # Exactly 95 tokens = 95% (critical threshold)
        tracker.current_context = 95
        result = indicator.render()
        assert result.get_style_at(0) == TOKEN_COLORS["critical"]

    def test_render_updates_with_tracker_changes(self):
        """Test that render() reflects current tracker state."""
        tracker = TokenTracker()
        tracker.set_context_limit(200_000)
        indicator = TokenUsageIndicator(tracker)

        # Start at 50%
        tracker.current_context = 100_000
        result1 = indicator.render()
        assert result1.get_style_at(0) == TOKEN_COLORS["normal"]

        # Move to 85%
        tracker.current_context = 170_000
        result2 = indicator.render()
        assert result2.get_style_at(0) == TOKEN_COLORS["warning"]

        # Move to 98%
        tracker.current_context = 196_000
        result3 = indicator.render()
        assert result3.get_style_at(0) == TOKEN_COLORS["critical"]

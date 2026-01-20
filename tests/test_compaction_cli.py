"""Tests for compaction CLI flags."""

import pytest
from kai_code.rich_main import parse_args


def test_no_compact_flag():
    """--no-compact flag disables compaction."""
    args = parse_args(["--no-compact"])

    assert args.no_compact is True


def test_compact_threshold_flag():
    """--compact-threshold sets custom threshold."""
    args = parse_args(["--compact-threshold", "0.90"])

    assert args.compact_threshold == 0.90


def test_default_compact_values():
    """Default values when no flags provided."""
    args = parse_args([])

    assert args.no_compact is False
    assert args.compact_threshold is None

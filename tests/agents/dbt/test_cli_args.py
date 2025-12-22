"""Tests for kai-dbt CLI argument parsing."""
import pytest

from kai_code.agents.dbt.cli import parse_args


def test_parse_args_defaults():
    """Default arguments are set correctly."""
    args = parse_args([])
    assert args.auto_approve is False
    assert args.no_splash is False
    assert args.db is None
    assert args.env == "default"


def test_parse_args_db_flag():
    """--db flag is parsed correctly."""
    args = parse_args(["--db", "analytics.duckdb"])
    assert args.db == "analytics.duckdb"


def test_parse_args_profile_flag():
    """--profile flag is parsed correctly."""
    args = parse_args(["--profile", "dev"])
    assert args.profile == "dev"


def test_parse_args_target_flag():
    """--target flag is parsed correctly."""
    args = parse_args(["--target", "prod"])
    assert args.target == "prod"


def test_parse_args_env_flag():
    """--env flag is parsed correctly."""
    args = parse_args(["--env", "production"])
    assert args.env == "production"


def test_parse_args_schema_flag():
    """--schema flag is parsed correctly."""
    args = parse_args(["--schema", "analytics"])
    assert args.schema == "analytics"


def test_parse_args_docs_dir_flag():
    """--docs-dir flag is parsed correctly."""
    args = parse_args(["--docs-dir", "/path/to/docs"])
    assert args.docs_dir == "/path/to/docs"


def test_parse_args_project_dir_flag():
    """--project-dir flag is parsed correctly."""
    args = parse_args(["--project-dir", "/path/to/project"])
    assert args.project_dir == "/path/to/project"


def test_parse_args_prompt():
    """Positional prompt arguments are parsed."""
    args = parse_args(["create", "staging", "model"])
    assert args.prompt == ["create", "staging", "model"]


def test_parse_args_auto_approve():
    """--yes flag enables auto-approve."""
    args = parse_args(["-y"])
    assert args.auto_approve is True

    args = parse_args(["--yes"])
    assert args.auto_approve is True


def test_parse_args_no_splash():
    """--no-splash flag is parsed."""
    args = parse_args(["--no-splash"])
    assert args.no_splash is True


def test_parse_args_version():
    """--version flag is parsed."""
    args = parse_args(["-v"])
    assert args.version is True

    args = parse_args(["--version"])
    assert args.version is True


def test_parse_args_combined():
    """Multiple flags can be combined."""
    args = parse_args([
        "--db", "test.duckdb",
        "--profile", "dev",
        "--target", "local",
        "--env", "development",
        "-y",
        "create", "model",
    ])
    assert args.db == "test.duckdb"
    assert args.profile == "dev"
    assert args.target == "local"
    assert args.env == "development"
    assert args.auto_approve is True
    assert args.prompt == ["create", "model"]

# kai-dbt CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `kai-dbt` CLI, a dedicated entry point for the dbt data engineering agent with specialized features for database introspection, dbt workflow, and environment-aware configuration.

**Architecture:** The CLI extends the existing Rich CLI pattern with dbt-specific features: environment-aware config loading, database connection handling, auto-detect dbt projects, dbt-themed banner, auto-schema summary, and dbt slash commands.

**Tech Stack:** Python 3.11+, Rich, prompt-toolkit, argparse, PyYAML

**Design Reference:** Brainstorming session decisions (2024-12-22)

---

## Task 1: Create CLI Module Structure

**Files:**
- Create: `src/kai_code/agents/dbt/cli.py`
- Create: `src/kai_code/agents/dbt/config.py`
- Test: `tests/agents/dbt/test_cli.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_cli.py`:

```python
"""Tests for kai-dbt CLI."""
import pytest
from kai_code.agents.dbt.cli import parse_args, DbtCliConfig


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


def test_parse_args_prompt():
    """Positional prompt arguments are parsed."""
    args = parse_args(["create", "staging", "model"])
    assert args.prompt == ["create", "staging", "model"]
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_cli.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/cli.py`:

```python
"""kai-dbt CLI - Data Engineering Agent Entry Point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

__all__ = ["parse_args", "main", "cli_main"]


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for kai-dbt CLI.

    Args:
        args: Optional list of arguments (defaults to sys.argv[1:])

    Returns:
        Parsed namespace with CLI options
    """
    parser = argparse.ArgumentParser(
        prog="kai-dbt",
        description="Kai dbt Engineer - AI-powered data engineering assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        help="Initial prompt to send to the agent (optional)",
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        dest="auto_approve",
        help="Auto-approve all tool actions (dangerous, use with caution)",
    )

    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Skip the startup banner",
    )

    # Database connection
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Database connection string (e.g., analytics.duckdb, postgresql://...)",
    )

    # dbt configuration
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="dbt profile name to use",
    )

    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="dbt target environment",
    )

    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Path to dbt project directory (auto-detected if not specified)",
    )

    parser.add_argument(
        "--docs-dir",
        type=str,
        default=None,
        help="Path to dbt documentation directory",
    )

    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Default schema to explore",
    )

    # Environment configuration
    parser.add_argument(
        "--env",
        type=str,
        default="default",
        help="Configuration environment (from .kai/dbt.yaml)",
    )

    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="Show version information",
    )

    parser.add_argument(
        "--help-commands",
        action="store_true",
        help="Show available slash commands",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for kai-dbt CLI.

    Args:
        args: Optional list of command line arguments

    Returns:
        Exit code (0 for success)
    """
    parsed = parse_args(args)

    # Handle --version
    if parsed.version:
        try:
            from kai_code import __version__
            print(f"kai-dbt {__version__}")
        except ImportError:
            print("kai-dbt (development)")
        return 0

    # TODO: Implement main CLI loop
    print("kai-dbt CLI not yet implemented")
    return 0


def cli_main() -> None:
    """CLI entry point that handles exit codes properly."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_cli.py -v
```

Expected: PASS (8 tests)

**Step 5: Commit**

```bash
git add src/kai_code/agents/dbt/cli.py tests/agents/dbt/test_cli.py
git commit -m "feat(dbt-cli): add argument parsing for kai-dbt CLI"
```

---

## Task 2: Create Configuration Loader

**Files:**
- Create: `src/kai_code/agents/dbt/config.py`
- Test: `tests/agents/dbt/test_config.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_config.py`:

```python
"""Tests for dbt CLI configuration loader."""
import pytest
import os
from pathlib import Path

from kai_code.agents.dbt.config import DbtCliConfig, load_config


@pytest.fixture
def config_dir(tmp_path):
    """Create a .kai directory with dbt.yaml config."""
    kai_dir = tmp_path / ".kai"
    kai_dir.mkdir()

    config_content = """
default:
  connection: analytics.duckdb
  profile: dev

production:
  connection: postgresql://prod-db/analytics
  profile: prod
  target: prod
"""
    (kai_dir / "dbt.yaml").write_text(config_content)
    return tmp_path


def test_dbt_cli_config_defaults():
    """DbtCliConfig has sensible defaults."""
    config = DbtCliConfig()
    assert config.connection is None
    assert config.profile is None
    assert config.target is None
    assert config.env == "default"


def test_load_config_from_file(config_dir):
    """load_config reads from .kai/dbt.yaml."""
    config = load_config(project_dir=config_dir, env="default")
    assert config.connection == "analytics.duckdb"
    assert config.profile == "dev"


def test_load_config_production_env(config_dir):
    """load_config loads production environment."""
    config = load_config(project_dir=config_dir, env="production")
    assert config.connection == "postgresql://prod-db/analytics"
    assert config.profile == "prod"
    assert config.target == "prod"


def test_load_config_env_override(config_dir, monkeypatch):
    """Environment variables override config file."""
    monkeypatch.setenv("KAI_DBT_CONNECTION", "override.duckdb")
    config = load_config(project_dir=config_dir, env="default")
    assert config.connection == "override.duckdb"


def test_load_config_cli_override(config_dir):
    """CLI arguments override environment and config."""
    config = load_config(
        project_dir=config_dir,
        env="default",
        cli_overrides={"connection": "cli.duckdb"},
    )
    assert config.connection == "cli.duckdb"


def test_load_config_missing_file(tmp_path):
    """load_config returns empty config when file is missing."""
    config = load_config(project_dir=tmp_path)
    assert config.connection is None


def test_load_config_env_selection(config_dir, monkeypatch):
    """KAI_DBT_ENV environment variable selects config environment."""
    monkeypatch.setenv("KAI_DBT_ENV", "production")
    config = load_config(project_dir=config_dir)
    assert config.profile == "prod"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_config.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/config.py`:

```python
"""Configuration loader for kai-dbt CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class DbtCliConfig:
    """Configuration for kai-dbt CLI.

    Priority (highest to lowest):
    1. CLI arguments
    2. Environment variables
    3. Config file (.kai/dbt.yaml)
    4. Defaults
    """

    connection: str | None = None
    profile: str | None = None
    target: str | None = None
    docs_dir: str | None = None
    schema: str | None = None
    env: str = "default"
    project_dir: Path | None = None

    def merge_with(self, other: dict[str, Any]) -> "DbtCliConfig":
        """Merge with another config, other takes priority."""
        merged = DbtCliConfig(
            connection=other.get("connection") or self.connection,
            profile=other.get("profile") or self.profile,
            target=other.get("target") or self.target,
            docs_dir=other.get("docs_dir") or self.docs_dir,
            schema=other.get("schema") or self.schema,
            env=other.get("env") or self.env,
            project_dir=other.get("project_dir") or self.project_dir,
        )
        return merged


def _load_config_file(config_path: Path, env: str) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to dbt.yaml config file.
        env: Environment name to load.

    Returns:
        Dictionary with configuration values.
    """
    if yaml is None:
        return {}

    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        # Get environment-specific config
        env_config = data.get(env, {})
        if isinstance(env_config, dict):
            return env_config
        return {}
    except Exception:
        return {}


def _get_env_overrides() -> dict[str, Any]:
    """Get configuration from environment variables.

    Environment variables:
    - KAI_DBT_CONNECTION: Database connection string
    - KAI_DBT_PROFILE: dbt profile name
    - KAI_DBT_TARGET: dbt target
    - KAI_DBT_DOCS_DIR: Documentation directory
    - KAI_DBT_SCHEMA: Default schema
    - KAI_DBT_ENV: Configuration environment

    Returns:
        Dictionary with environment variable values.
    """
    overrides = {}

    env_map = {
        "KAI_DBT_CONNECTION": "connection",
        "KAI_DBT_PROFILE": "profile",
        "KAI_DBT_TARGET": "target",
        "KAI_DBT_DOCS_DIR": "docs_dir",
        "KAI_DBT_SCHEMA": "schema",
    }

    for env_var, key in env_map.items():
        value = os.environ.get(env_var)
        if value:
            overrides[key] = value

    return overrides


def load_config(
    project_dir: Path | str | None = None,
    env: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> DbtCliConfig:
    """Load dbt CLI configuration with proper priority.

    Priority (highest to lowest):
    1. CLI arguments (cli_overrides)
    2. Environment variables
    3. Config file (.kai/dbt.yaml)
    4. Defaults

    Args:
        project_dir: Project directory containing .kai/dbt.yaml.
        env: Configuration environment name.
        cli_overrides: CLI argument overrides.

    Returns:
        Merged DbtCliConfig instance.
    """
    # Determine project directory
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    # Determine environment (check env var if not specified)
    if env is None:
        env = os.environ.get("KAI_DBT_ENV", "default")

    # Start with defaults
    config = DbtCliConfig(env=env, project_dir=project_dir)

    # Load from config file
    config_path = project_dir / ".kai" / "dbt.yaml"
    file_config = _load_config_file(config_path, env)
    if file_config:
        config = config.merge_with(file_config)

    # Apply environment variable overrides
    env_overrides = _get_env_overrides()
    if env_overrides:
        config = config.merge_with(env_overrides)

    # Apply CLI overrides (highest priority)
    if cli_overrides:
        config = config.merge_with(cli_overrides)

    return config
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_config.py -v
```

Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/kai_code/agents/dbt/config.py tests/agents/dbt/test_config.py
git commit -m "feat(dbt-cli): add configuration loader with priority chain"
```

---

## Task 3: Create dbt Project Auto-Detection

**Files:**
- Modify: `src/kai_code/agents/dbt/config.py`
- Test: `tests/agents/dbt/test_project_detection.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_project_detection.py`:

```python
"""Tests for dbt project auto-detection."""
import pytest
from pathlib import Path

from kai_code.agents.dbt.config import find_dbt_project, DbtProjectInfo


@pytest.fixture
def dbt_project(tmp_path):
    """Create a minimal dbt project structure."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    (project_dir / "dbt_project.yml").write_text("""
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
model-paths: ["models"]
""")

    models_dir = project_dir / "models"
    models_dir.mkdir()
    (models_dir / "stg_orders.sql").write_text("SELECT 1")

    return project_dir


def test_find_dbt_project_in_current_dir(dbt_project):
    """find_dbt_project finds project in current directory."""
    result = find_dbt_project(dbt_project)
    assert result is not None
    assert result.project_dir == dbt_project
    assert result.project_name == "test_project"


def test_find_dbt_project_in_parent_dir(dbt_project):
    """find_dbt_project finds project in parent directory."""
    subdir = dbt_project / "models" / "staging"
    subdir.mkdir(parents=True)

    result = find_dbt_project(subdir)
    assert result is not None
    assert result.project_dir == dbt_project


def test_find_dbt_project_not_found(tmp_path):
    """find_dbt_project returns None when no project found."""
    result = find_dbt_project(tmp_path)
    assert result is None


def test_dbt_project_info_model_paths(dbt_project):
    """DbtProjectInfo includes model paths."""
    result = find_dbt_project(dbt_project)
    assert result.model_paths == ["models"]


def test_dbt_project_info_profile(dbt_project):
    """DbtProjectInfo includes profile name."""
    result = find_dbt_project(dbt_project)
    assert result.profile == "test"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_project_detection.py -v
```

Expected: FAIL with "cannot import name 'find_dbt_project'"

**Step 3: Add project detection to config.py**

Update `src/kai_code/agents/dbt/config.py`:

```python
# Add these imports at the top
from dataclasses import dataclass

# Add after DbtCliConfig class:

@dataclass
class DbtProjectInfo:
    """Information about a detected dbt project."""

    project_dir: Path
    project_name: str
    profile: str | None = None
    model_paths: list[str] = field(default_factory=lambda: ["models"])
    version: str | None = None


def find_dbt_project(start_dir: Path | str | None = None) -> DbtProjectInfo | None:
    """Find dbt project by searching for dbt_project.yml.

    Searches current directory and parent directories up to filesystem root.

    Args:
        start_dir: Directory to start search from (defaults to cwd).

    Returns:
        DbtProjectInfo if found, None otherwise.
    """
    if yaml is None:
        return None

    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)

    current = start_dir.resolve()

    while current != current.parent:
        project_file = current / "dbt_project.yml"

        if project_file.exists():
            try:
                with open(project_file) as f:
                    data = yaml.safe_load(f) or {}

                return DbtProjectInfo(
                    project_dir=current,
                    project_name=data.get("name", "unknown"),
                    profile=data.get("profile"),
                    model_paths=data.get("model-paths", ["models"]),
                    version=data.get("version"),
                )
            except Exception:
                return None

        current = current.parent

    return None
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_project_detection.py -v
```

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/kai_code/agents/dbt/config.py tests/agents/dbt/test_project_detection.py
git commit -m "feat(dbt-cli): add dbt project auto-detection"
```

---

## Task 4: Create dbt-Themed ASCII Banner

**Files:**
- Create: `src/kai_code/agents/dbt/banner.py`
- Test: `tests/agents/dbt/test_banner.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_banner.py`:

```python
"""Tests for dbt CLI banner."""
import pytest

from kai_code.agents.dbt.banner import DBT_ASCII_BANNER, create_startup_info


def test_banner_exists():
    """ASCII banner is defined."""
    assert DBT_ASCII_BANNER is not None
    assert len(DBT_ASCII_BANNER) > 0


def test_banner_contains_dbt():
    """Banner contains dbt branding."""
    assert "dbt" in DBT_ASCII_BANNER.lower() or "data" in DBT_ASCII_BANNER.lower()


def test_create_startup_info_connected():
    """create_startup_info shows connection status."""
    info = create_startup_info(
        db_connected=True,
        db_name="analytics.duckdb",
        table_count=15,
        project_name="my_project",
    )
    assert "analytics.duckdb" in info
    assert "15" in info
    assert "my_project" in info


def test_create_startup_info_not_connected():
    """create_startup_info handles no connection."""
    info = create_startup_info(db_connected=False)
    assert "No database connected" in info or "not connected" in info.lower()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_banner.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/banner.py`:

```python
"""ASCII banner and startup info for kai-dbt CLI."""
from __future__ import annotations

# dbt-themed ASCII art banner
DBT_ASCII_BANNER = r"""
    ╦╔═╔═╗╦  ╔╦╗╔╗ ╔╦╗
    ╠╩╗╠═╣║   ║║╠╩╗ ║
    ╩ ╩╩ ╩╩  ═╩╝╚═╝ ╩
    ┌─────────────────────┐
    │  Data Engineering   │
    │       Agent         │
    └─────────────────────┘
"""

# Alternative compact banner
DBT_ASCII_BANNER_COMPACT = r"""
╔═══════════════════════════════╗
║  KAI dbt  │  Data Engineer    ║
╚═══════════════════════════════╝
"""


def create_startup_info(
    db_connected: bool = False,
    db_name: str | None = None,
    table_count: int | None = None,
    project_name: str | None = None,
    profile: str | None = None,
    target: str | None = None,
) -> str:
    """Create startup information string.

    Args:
        db_connected: Whether database is connected.
        db_name: Database name/path.
        table_count: Number of tables in database.
        project_name: dbt project name.
        profile: dbt profile name.
        target: dbt target environment.

    Returns:
        Formatted startup information string.
    """
    lines = []

    # Project info
    if project_name:
        lines.append(f"Project: {project_name}")
        if profile:
            lines.append(f"Profile: {profile}")
        if target:
            lines.append(f"Target: {target}")

    # Database info
    if db_connected and db_name:
        db_line = f"Database: {db_name}"
        if table_count is not None:
            db_line += f" ({table_count} tables)"
        lines.append(db_line)
    else:
        lines.append("Database: Not connected")

    return "\n".join(lines)


def format_schema_summary(tables: list[dict]) -> str:
    """Format schema summary as a compact table.

    Args:
        tables: List of table info dictionaries with name, columns, rows.

    Returns:
        Formatted table string for Rich console.
    """
    if not tables:
        return "No tables found."

    # Calculate column widths
    max_name = max(len(t.get("name", "")) for t in tables)
    max_name = max(max_name, 5)  # Minimum "Table" header

    lines = []
    lines.append(f"┌{'─' * (max_name + 2)}┬─────────┬──────────┐")
    lines.append(f"│ {'Table':<{max_name}} │ Columns │ Rows     │")
    lines.append(f"├{'─' * (max_name + 2)}┼─────────┼──────────┤")

    for table in tables:
        name = table.get("name", "")[:max_name]
        cols = str(table.get("column_count", "-"))[:7]
        rows = _format_row_count(table.get("row_count"))
        lines.append(f"│ {name:<{max_name}} │ {cols:>7} │ {rows:>8} │")

    lines.append(f"└{'─' * (max_name + 2)}┴─────────┴──────────┘")

    return "\n".join(lines)


def _format_row_count(count: int | None) -> str:
    """Format row count with K/M suffixes."""
    if count is None:
        return "-"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_banner.py -v
```

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/kai_code/agents/dbt/banner.py tests/agents/dbt/test_banner.py
git commit -m "feat(dbt-cli): add dbt-themed ASCII banner and schema summary"
```

---

## Task 5: Create dbt Slash Commands

**Files:**
- Create: `src/kai_code/agents/dbt/commands.py`
- Test: `tests/agents/dbt/test_commands.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_commands.py`:

```python
"""Tests for dbt slash commands."""
import pytest
from unittest.mock import Mock, MagicMock

from kai_code.agents.dbt.commands import (
    DbtCommandHandler,
    parse_dbt_command,
)


@pytest.fixture
def mock_agent():
    """Create a mock DbtAgent."""
    agent = Mock()
    agent.adapter = Mock()
    agent.adapter.get_tables.return_value = [
        Mock(name="orders", schema="main", full_name="main.orders", row_count=1000, column_count=5),
        Mock(name="customers", schema="main", full_name="main.customers", row_count=500, column_count=3),
    ]
    return agent


def test_parse_dbt_command_run():
    """Parse /dbt run command."""
    cmd, args = parse_dbt_command("/dbt run")
    assert cmd == "run"
    assert args == {}


def test_parse_dbt_command_run_with_select():
    """Parse /dbt run with select argument."""
    cmd, args = parse_dbt_command("/dbt run stg_orders")
    assert cmd == "run"
    assert args["select"] == "stg_orders"


def test_parse_dbt_command_test():
    """Parse /dbt test command."""
    cmd, args = parse_dbt_command("/dbt test")
    assert cmd == "test"


def test_parse_dbt_command_compile():
    """Parse /dbt compile command."""
    cmd, args = parse_dbt_command("/dbt compile my_model")
    assert cmd == "compile"
    assert args["model"] == "my_model"


def test_parse_dbt_command_list():
    """Parse /dbt list command."""
    cmd, args = parse_dbt_command("/dbt list")
    assert cmd == "list"


def test_parse_schema_command():
    """Parse /schema command."""
    cmd, args = parse_dbt_command("/schema")
    assert cmd == "schema"


def test_parse_model_command():
    """Parse /model command with name."""
    cmd, args = parse_dbt_command("/model stg_orders")
    assert cmd == "model"
    assert args["name"] == "stg_orders"


def test_command_handler_schema(mock_agent):
    """Command handler executes /schema."""
    handler = DbtCommandHandler(mock_agent)
    result = handler.handle("/schema")
    assert result is not None
    assert "orders" in result.lower() or "table" in result.lower()


def test_command_handler_unknown():
    """Command handler returns None for unknown commands."""
    handler = DbtCommandHandler(Mock())
    result = handler.handle("/unknown")
    assert result is None
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/agents/dbt/test_commands.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/kai_code/agents/dbt/commands.py`:

```python
"""Slash command handlers for kai-dbt CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .banner import format_schema_summary

if TYPE_CHECKING:
    from .agent import DbtAgent


def parse_dbt_command(command: str) -> tuple[str, dict[str, Any]]:
    """Parse a dbt slash command into command name and arguments.

    Args:
        command: Full command string (e.g., "/dbt run stg_orders").

    Returns:
        Tuple of (command_name, arguments_dict).
    """
    parts = command.strip().split()

    if not parts:
        return "", {}

    # Handle /dbt subcommands
    if parts[0] == "/dbt" and len(parts) >= 2:
        subcommand = parts[1]
        args = {}

        if subcommand == "run" and len(parts) > 2:
            args["select"] = parts[2]
        elif subcommand == "test" and len(parts) > 2:
            args["select"] = parts[2]
        elif subcommand == "compile" and len(parts) > 2:
            args["model"] = parts[2]
        elif subcommand == "show" and len(parts) > 2:
            args["model"] = parts[2]

        return subcommand, args

    # Handle direct commands
    if parts[0] == "/schema":
        return "schema", {}

    if parts[0] == "/model" and len(parts) > 1:
        return "model", {"name": parts[1]}

    return parts[0].lstrip("/"), {}


class DbtCommandHandler:
    """Handler for dbt-specific slash commands."""

    def __init__(self, agent: "DbtAgent"):
        """Initialize command handler.

        Args:
            agent: DbtAgent instance.
        """
        self.agent = agent

    def handle(self, command: str) -> str | None:
        """Handle a slash command.

        Args:
            command: Command string.

        Returns:
            Command output string, or None if command not recognized.
        """
        cmd, args = parse_dbt_command(command)

        handlers = {
            "schema": self._handle_schema,
            "model": self._handle_model,
            "run": self._handle_dbt_run,
            "test": self._handle_dbt_test,
            "compile": self._handle_dbt_compile,
            "list": self._handle_dbt_list,
            "show": self._handle_dbt_show,
        }

        handler = handlers.get(cmd)
        if handler:
            return handler(args)

        return None

    def _handle_schema(self, args: dict) -> str:
        """Handle /schema command."""
        if not self.agent.adapter:
            return "No database connected. Use --db to connect."

        try:
            tables = self.agent.adapter.get_tables()
            table_data = [
                {
                    "name": t.name,
                    "column_count": t.column_count,
                    "row_count": t.row_count,
                }
                for t in tables
            ]
            return format_schema_summary(table_data)
        except Exception as e:
            return f"Error fetching schema: {e}"

    def _handle_model(self, args: dict) -> str:
        """Handle /model <name> command."""
        model_name = args.get("name")
        if not model_name:
            return "Usage: /model <model_name>"

        if not self.agent.adapter:
            return "No database connected."

        try:
            columns = self.agent.adapter.get_columns(model_name)
            if not columns:
                return f"Model '{model_name}' not found."

            lines = [f"Model: {model_name}", ""]
            lines.append("Columns:")
            for col in columns:
                pk = " (PK)" if col.is_primary_key else ""
                nullable = " NULL" if col.is_nullable else " NOT NULL"
                lines.append(f"  - {col.name}: {col.data_type}{pk}{nullable}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def _handle_dbt_run(self, args: dict) -> str:
        """Handle /dbt run command."""
        return self._run_dbt_command(["run"], args.get("select"))

    def _handle_dbt_test(self, args: dict) -> str:
        """Handle /dbt test command."""
        return self._run_dbt_command(["test"], args.get("select"))

    def _handle_dbt_compile(self, args: dict) -> str:
        """Handle /dbt compile command."""
        return self._run_dbt_command(["compile"], args.get("model"))

    def _handle_dbt_list(self, args: dict) -> str:
        """Handle /dbt list command."""
        return self._run_dbt_command(["list"])

    def _handle_dbt_show(self, args: dict) -> str:
        """Handle /dbt show command."""
        model = args.get("model")
        if not model:
            return "Usage: /dbt show <model_name>"
        return self._run_dbt_command(["show", "--select", model])

    def _run_dbt_command(
        self,
        command: list[str],
        select: str | None = None,
    ) -> str:
        """Run a dbt CLI command.

        Args:
            command: dbt command arguments.
            select: Optional model selection.

        Returns:
            Command output.
        """
        full_command = ["dbt"] + command

        if select:
            full_command.extend(["--select", select])

        full_command.extend([
            "--project-dir",
            str(self.agent.dbt_project_dir),
        ])

        if self.agent.dbt_profiles_dir:
            full_command.extend([
                "--profiles-dir",
                str(self.agent.dbt_profiles_dir),
            ])

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.agent.dbt_project_dir),
            )

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error:\n{result.stderr or result.stdout}"

        except subprocess.TimeoutExpired:
            return "Command timed out after 5 minutes."
        except FileNotFoundError:
            return "dbt command not found. Ensure dbt is installed."
        except Exception as e:
            return f"Error: {e}"
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/agents/dbt/test_commands.py -v
```

Expected: PASS (10 tests)

**Step 5: Commit**

```bash
git add src/kai_code/agents/dbt/commands.py tests/agents/dbt/test_commands.py
git commit -m "feat(dbt-cli): add dbt slash commands handler"
```

---

## Task 6: Implement Main CLI Loop

**Files:**
- Modify: `src/kai_code/agents/dbt/cli.py`
- Test: `tests/agents/dbt/test_cli_integration.py`

**Step 1: Write the failing test**

Create `tests/agents/dbt/test_cli_integration.py`:

```python
"""Integration tests for kai-dbt CLI."""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from pathlib import Path

from kai_code.agents.dbt.cli import main, _create_dbt_agent, _show_startup_banner


@pytest.fixture
def dbt_project(tmp_path):
    """Create a minimal dbt project."""
    (tmp_path / "dbt_project.yml").write_text("""
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
""")
    return tmp_path


def test_main_version_flag():
    """--version flag shows version and exits."""
    result = main(["--version"])
    assert result == 0


def test_main_help_commands_flag():
    """--help-commands flag shows commands."""
    with patch("kai_code.agents.dbt.cli._show_help_commands") as mock_help:
        result = main(["--help-commands"])
        mock_help.assert_called_once()
        assert result == 0


def test_create_dbt_agent_without_db(dbt_project):
    """_create_dbt_agent works without database."""
    with patch.dict("os.environ", {"KAI_DBT_CONNECTION": ""}):
        agent, graph = _create_dbt_agent(
            project_dir=dbt_project,
            db_connection=None,
        )
        assert agent is not None
        assert agent.adapter is None


def test_create_dbt_agent_with_db(dbt_project, tmp_path):
    """_create_dbt_agent connects to database."""
    import duckdb
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()

    agent, graph = _create_dbt_agent(
        project_dir=dbt_project,
        db_connection=str(db_path),
    )
    assert agent is not None
    assert agent.adapter is not None
    agent.adapter.close()


def test_show_startup_banner_with_db(capsys, dbt_project, tmp_path):
    """Startup banner shows database info."""
    import duckdb
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE orders (id INTEGER)")
    conn.execute("CREATE TABLE customers (id INTEGER)")
    conn.close()

    from kai_code.agents.dbt.adapters import DuckDBAdapter
    adapter = DuckDBAdapter(str(db_path))

    _show_startup_banner(
        project_name="test_project",
        adapter=adapter,
        no_splash=False,
    )

    captured = capsys.readouterr()
    assert "test_project" in captured.out or "orders" in captured.out
    adapter.close()
```

**Step 2: Update CLI implementation**

Update `src/kai_code/agents/dbt/cli.py` with the full implementation:

```python
"""kai-dbt CLI - Data Engineering Agent Entry Point."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from .banner import DBT_ASCII_BANNER, create_startup_info, format_schema_summary
from .config import DbtCliConfig, load_config, find_dbt_project
from .commands import DbtCommandHandler

if TYPE_CHECKING:
    from .agent import DbtAgent
    from .adapters import DatabaseAdapter
    from langgraph.graph.state import CompiledStateGraph

console = Console()

__all__ = ["parse_args", "main", "cli_main"]

# ... (parse_args remains the same as Task 1)


def _show_help_commands() -> None:
    """Show available dbt slash commands."""
    console.print("\n[bold]dbt Slash Commands:[/bold]\n")
    commands = [
        ("/schema", "Show database schema summary"),
        ("/model <name>", "Show model details and columns"),
        ("/dbt run [model]", "Run dbt models"),
        ("/dbt test [model]", "Run dbt tests"),
        ("/dbt compile [model]", "Compile dbt models"),
        ("/dbt list", "List dbt resources"),
        ("/dbt show <model>", "Preview model output"),
    ]
    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:<25}[/cyan] {desc}")
    console.print()


def _show_startup_banner(
    project_name: str | None = None,
    adapter: "DatabaseAdapter | None" = None,
    no_splash: bool = False,
) -> None:
    """Display startup banner and schema summary."""
    if no_splash:
        return

    # Show ASCII banner
    console.print(DBT_ASCII_BANNER, style="cyan")

    # Get database info
    db_connected = adapter is not None
    db_name = None
    table_count = None
    tables = []

    if adapter:
        try:
            tables = adapter.get_tables()
            table_count = len(tables)
            # Get db name from adapter (varies by type)
            if hasattr(adapter, "database_path"):
                db_name = str(adapter.database_path)
            elif hasattr(adapter, "_connection_string"):
                db_name = adapter._connection_string.split("/")[-1].split("?")[0]
        except Exception:
            pass

    # Show startup info
    info = create_startup_info(
        db_connected=db_connected,
        db_name=db_name,
        table_count=table_count,
        project_name=project_name,
    )
    console.print(info, style="dim")

    # Show schema summary table if connected
    if tables:
        console.print()
        table_data = [
            {
                "name": t.name,
                "column_count": t.column_count,
                "row_count": t.row_count,
            }
            for t in tables[:10]  # Limit to 10 tables
        ]
        console.print(format_schema_summary(table_data))
        if len(tables) > 10:
            console.print(f"  ... and {len(tables) - 10} more tables", style="dim")

    console.print()
    console.print("Type /help for commands, Ctrl+C twice to exit.", style="dim")
    console.print()


def _create_dbt_agent(
    project_dir: Path,
    db_connection: str | None = None,
    profile: str | None = None,
    target: str | None = None,
    yolo: bool = False,
) -> tuple["DbtAgent", "CompiledStateGraph"]:
    """Create DbtAgent instance.

    Args:
        project_dir: dbt project directory.
        db_connection: Database connection string.
        profile: dbt profile name.
        target: dbt target.
        yolo: Auto-approve mode.

    Returns:
        Tuple of (DbtAgent, compiled graph).
    """
    from .agent import DbtAgent
    from kai_code.model import get_default_model, resolve_model

    # Get model
    default_model = get_default_model()
    model_string = resolve_model(default_model)

    # Create agent
    agent = DbtAgent(
        root_dir=project_dir,
        model=model_string,
        db_connection=db_connection,
        dbt_project_dir=project_dir,
        yolo=yolo,
    )

    # Build graph
    graph = agent._build_graph()

    return agent, graph


async def dbt_cli_loop(
    agent: "DbtAgent",
    graph: "CompiledStateGraph",
    initial_prompt: str | None = None,
    auto_approve: bool = False,
) -> None:
    """Main CLI loop for kai-dbt.

    Args:
        agent: DbtAgent instance.
        graph: Compiled LangGraph.
        initial_prompt: Optional initial prompt.
        auto_approve: Auto-approve mode.
    """
    from prompt_toolkit import PromptSession
    from kai_code.rich_execution import execute_task
    from kai_code.rich_config import SessionState
    from kai_code.cli_ui import TokenTracker
    from kai_code.rich_input import ImageTracker

    command_handler = DbtCommandHandler(agent)
    session_state = SessionState(auto_approve=auto_approve)
    token_tracker = TokenTracker()
    image_tracker = ImageTracker()
    prompt_session = PromptSession()

    # Handle initial prompt
    if initial_prompt:
        await execute_task(
            initial_prompt,
            graph,
            "kai-dbt",
            session_state,
            token_tracker=token_tracker,
            backend=agent.backend,
            image_tracker=image_tracker,
        )

    # Main loop
    while True:
        try:
            user_input = await asyncio.to_thread(
                prompt_session.prompt,
                "kai-dbt> ",
            )
            user_input = user_input.strip()

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                if user_input == "/exit" or user_input == "/quit":
                    console.print("Goodbye!", style="dim")
                    break

                if user_input == "/help":
                    _show_help_commands()
                    continue

                result = command_handler.handle(user_input)
                if result:
                    console.print(result)
                else:
                    console.print(f"Unknown command: {user_input}", style="yellow")
                continue

            # Execute through agent
            await execute_task(
                user_input,
                graph,
                "kai-dbt",
                session_state,
                token_tracker=token_tracker,
                backend=agent.backend,
                image_tracker=image_tracker,
            )

        except KeyboardInterrupt:
            console.print()
            continue
        except EOFError:
            console.print("\nGoodbye!", style="dim")
            break


def main(args: list[str] | None = None) -> int:
    """Main entry point for kai-dbt CLI."""
    parsed = parse_args(args)

    # Handle --version
    if parsed.version:
        try:
            from kai_code import __version__
            console.print(f"kai-dbt {__version__}")
        except ImportError:
            console.print("kai-dbt (development)")
        return 0

    # Handle --help-commands
    if parsed.help_commands:
        _show_help_commands()
        return 0

    # Load configuration
    config = load_config(
        project_dir=parsed.project_dir or Path.cwd(),
        env=parsed.env,
        cli_overrides={
            "connection": parsed.db,
            "profile": parsed.profile,
            "target": parsed.target,
            "docs_dir": parsed.docs_dir,
            "schema": parsed.schema,
        },
    )

    # Find dbt project
    project_info = find_dbt_project(config.project_dir)
    project_dir = project_info.project_dir if project_info else Path.cwd()
    project_name = project_info.project_name if project_info else None

    # Create agent
    try:
        agent, graph = _create_dbt_agent(
            project_dir=project_dir,
            db_connection=config.connection,
            profile=config.profile,
            target=config.target,
            yolo=parsed.auto_approve,
        )
    except Exception as e:
        console.print(f"[red]Error creating agent: {e}[/red]")
        # Warn and continue without db if connection failed
        if config.connection:
            console.print("[yellow]Continuing without database connection.[/yellow]")
            agent, graph = _create_dbt_agent(
                project_dir=project_dir,
                db_connection=None,
                yolo=parsed.auto_approve,
            )
        else:
            return 1

    # Show banner
    _show_startup_banner(
        project_name=project_name,
        adapter=agent.adapter,
        no_splash=parsed.no_splash,
    )

    # Get initial prompt
    initial_prompt = " ".join(parsed.prompt) if parsed.prompt else None

    # Run CLI
    try:
        asyncio.run(dbt_cli_loop(
            agent=agent,
            graph=graph,
            initial_prompt=initial_prompt,
            auto_approve=parsed.auto_approve,
        ))
        return 0
    except KeyboardInterrupt:
        console.print("\nGoodbye!", style="dim")
        return 0
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        return 1
    finally:
        if agent.adapter:
            agent.adapter.close()


def cli_main() -> None:
    """CLI entry point that handles exit codes properly."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
```

**Step 3: Run tests**

```bash
python -m pytest tests/agents/dbt/test_cli_integration.py -v
```

Expected: PASS (5 tests)

**Step 4: Commit**

```bash
git add src/kai_code/agents/dbt/cli.py tests/agents/dbt/test_cli_integration.py
git commit -m "feat(dbt-cli): implement main CLI loop with commands and banner"
```

---

## Task 7: Add Entry Point to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

Add the `kai-dbt` entry point:

```toml
[project.scripts]
kai = "kai_code.rich_main:cli_main"
kai-code = "kai_code.rich_main:cli_main"
kai-basic = "kai_code.cli:main"
kai-dbt = "kai_code.agents.dbt.cli:cli_main"
```

**Step 2: Add PyYAML dependency**

Ensure PyYAML is in dependencies:

```toml
dependencies = [
  # ... existing deps
  "pyyaml>=6.0",
]
```

**Step 3: Verify installation**

```bash
pip install -e .
kai-dbt --help
kai-dbt --version
```

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat(dbt-cli): add kai-dbt entry point"
```

---

## Task 8: Update dbt Package Exports

**Files:**
- Modify: `src/kai_code/agents/dbt/__init__.py`

**Step 1: Update exports**

Update `src/kai_code/agents/dbt/__init__.py`:

```python
"""DbtAgent - specialized agent for dbt data engineering."""
from .models import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    CardinalityInfo,
    QueryResult,
)
from .adapters import (
    DatabaseAdapter,
    DuckDBAdapter,
    PostgreSQLAdapter,
    get_adapter,
)
from .agent import DbtAgent
from .config import DbtCliConfig, DbtProjectInfo, load_config, find_dbt_project
from .banner import DBT_ASCII_BANNER, create_startup_info, format_schema_summary
from .commands import DbtCommandHandler, parse_dbt_command
from .cli import parse_args, main, cli_main

__all__ = [
    # Agent
    "DbtAgent",
    # Models
    "TableInfo",
    "ColumnInfo",
    "ForeignKeyInfo",
    "CardinalityInfo",
    "QueryResult",
    # Adapters
    "DatabaseAdapter",
    "DuckDBAdapter",
    "PostgreSQLAdapter",
    "get_adapter",
    # Config
    "DbtCliConfig",
    "DbtProjectInfo",
    "load_config",
    "find_dbt_project",
    # Banner
    "DBT_ASCII_BANNER",
    "create_startup_info",
    "format_schema_summary",
    # Commands
    "DbtCommandHandler",
    "parse_dbt_command",
    # CLI
    "parse_args",
    "main",
    "cli_main",
]
```

**Step 2: Commit**

```bash
git add src/kai_code/agents/dbt/__init__.py
git commit -m "feat(dbt-cli): export CLI modules from dbt package"
```

---

## Summary

This implementation plan covers:

1. **Task 1**: CLI argument parsing with all flags (--db, --profile, --target, etc.)
2. **Task 2**: Configuration loader with priority chain (CLI > env > config file)
3. **Task 3**: dbt project auto-detection
4. **Task 4**: dbt-themed ASCII banner and schema summary
5. **Task 5**: dbt slash commands (/dbt run, /schema, /model, etc.)
6. **Task 6**: Main CLI loop with agent integration
7. **Task 7**: pyproject.toml entry point
8. **Task 8**: Package exports

Each task follows TDD with failing tests first, then implementation.

---

**Plan complete and saved. Ready for execution.**

**Execution options:**

**1. Subagent-Driven (this session)** - Dispatch fresh subagent per task, review between tasks

**2. Parallel Session (separate)** - Open new session with executing-plans skill

**Which approach?**

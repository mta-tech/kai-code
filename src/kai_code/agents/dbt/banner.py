"""ASCII banner and startup info for kai-dbt CLI."""
from __future__ import annotations

# dbt-themed ASCII art banner (matching kai-code block style)
DBT_ASCII_BANNER = """
 ██╗  ██╗  █████╗  ██╗
 ██║ ██╔╝ ██╔══██╗ ██║
 █████╔╝  ███████║ ██║
 ██╔═██╗  ██╔══██║ ██║
 ██║  ██╗ ██║  ██║ ██║
 ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝

 ██████╗  ██████╗  ████████╗
 ██╔══██╗ ██╔══██╗ ╚══██╔══╝
 ██║  ██║ ██████╔╝    ██║
 ██║  ██║ ██╔══██╗    ██║
 ██████╔╝ ██████╔╝    ██║
 ╚═════╝  ╚═════╝     ╚═╝
"""

# Compact banner alternative
DBT_ASCII_BANNER_COMPACT = """
 ╔═══════════════════════════════════╗
 ║  KAI dbt  │  Data Engineering     ║
 ╚═══════════════════════════════════╝
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
        tables: List of table info dictionaries with name, column_count, row_count.

    Returns:
        Formatted table string.
    """
    if not tables:
        return "No tables found."

    # Calculate column widths
    max_name = max(len(t.get("name", "")) for t in tables)
    max_name = max(max_name, 5)  # Minimum "Table" header width
    max_name = min(max_name, 25)  # Maximum width

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
    """Format row count with K/M suffixes.

    Args:
        count: Row count, or None.

    Returns:
        Formatted string (e.g., "1.5M", "45K", "500", "-").
    """
    if count is None:
        return "-"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)

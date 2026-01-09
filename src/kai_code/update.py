"""Auto-update functionality for kai-code.

Provides mechanisms to update kai-code from GitHub without manual reinstallation.
Supports both editable (development) installs and regular pip installs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import distribution, PackageNotFoundError
from pathlib import Path
from typing import Any


# GitHub repository URL
GITHUB_REPO = "https://github.com/mta-tech/kai-code.git"
GITHUB_API_URL = "https://api.github.com/repos/mta-tech/kai-code"


@dataclass
class UpdateResult:
    """Result of an update operation."""
    success: bool
    message: str
    updated: bool = False
    old_version: str | None = None
    new_version: str | None = None
    details: str | None = None


def get_current_version() -> str:
    """Get the currently installed version of kai-code."""
    try:
        dist = distribution("kai-code")
        return dist.version
    except PackageNotFoundError:
        return "unknown"


def is_editable_install() -> tuple[bool, Path | None]:
    """Check if kai-code is installed in editable (development) mode.

    Returns:
        Tuple of (is_editable, source_path).
        source_path is the path to the source directory if editable.
    """
    try:
        dist = distribution("kai-code")

        # Check for direct_url.json (PEP 610) - indicates editable install
        try:
            direct_url_text = dist.read_text("direct_url.json")
            if direct_url_text:
                direct_url = json.loads(direct_url_text)
                if direct_url.get("dir_info", {}).get("editable", False):
                    url = direct_url.get("url", "")
                    if url.startswith("file://"):
                        source_path = Path(url[7:])
                        if source_path.exists():
                            return True, source_path
        except FileNotFoundError:
            pass

        # Fallback: check if the package location has a .git directory
        if hasattr(dist, "_path"):
            pkg_path = Path(dist._path)
            # Navigate up to find the source root
            for parent in [pkg_path] + list(pkg_path.parents):
                if (parent / ".git").is_dir():
                    return True, parent

        return False, None

    except PackageNotFoundError:
        return False, None


def get_git_info(source_path: Path) -> dict[str, Any]:
    """Get git information from the source directory.

    Returns:
        Dict with branch, commit, remote info.
    """
    info: dict[str, Any] = {}

    try:
        # Current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=source_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()

        # Current commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            info["commit"] = result.stdout.strip()[:8]

        # Remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=source_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            info["remote"] = result.stdout.strip()

    except Exception:
        pass

    return info


def check_for_updates(source_path: Path | None = None) -> UpdateResult:
    """Check if updates are available.

    Args:
        source_path: Path to source directory for editable installs.

    Returns:
        UpdateResult with update availability info.
    """
    is_editable, detected_path = is_editable_install()
    source_path = source_path or detected_path

    current_version = get_current_version()

    if is_editable and source_path:
        # For editable installs, check git
        try:
            # Fetch latest
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=source_path,
                capture_output=True,
                check=True,
            )

            # Check if behind
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..origin/main"],
                cwd=source_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                commits_behind = int(result.stdout.strip())
                if commits_behind > 0:
                    return UpdateResult(
                        success=True,
                        message=f"Updates available: {commits_behind} new commit(s)",
                        updated=False,
                        old_version=current_version,
                        details=f"Run 'kai update' to update from GitHub",
                    )
                else:
                    return UpdateResult(
                        success=True,
                        message="Already up to date",
                        updated=False,
                        old_version=current_version,
                    )

        except subprocess.CalledProcessError as e:
            return UpdateResult(
                success=False,
                message=f"Failed to check for updates: {e}",
                old_version=current_version,
            )
    else:
        # For regular installs, we can't easily check without fetching
        return UpdateResult(
            success=True,
            message="Run 'kai update' to check and install updates from GitHub",
            old_version=current_version,
        )

    return UpdateResult(
        success=True,
        message="Unable to determine update status",
        old_version=current_version,
    )


def update_editable(source_path: Path) -> UpdateResult:
    """Update an editable install using git pull.

    Args:
        source_path: Path to the source directory.

    Returns:
        UpdateResult with update status.
    """
    old_version = get_current_version()
    git_info = get_git_info(source_path)
    old_commit = git_info.get("commit", "unknown")

    try:
        # Fetch latest
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=source_path,
            capture_output=True,
            check=True,
        )

        # Check current branch
        branch = git_info.get("branch", "main")

        # Pull latest
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=source_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return UpdateResult(
                success=False,
                message=f"Git pull failed: {result.stderr}",
                old_version=old_version,
            )

        # Get new commit
        new_git_info = get_git_info(source_path)
        new_commit = new_git_info.get("commit", "unknown")
        new_version = get_current_version()

        if old_commit == new_commit:
            return UpdateResult(
                success=True,
                message="Already up to date",
                updated=False,
                old_version=old_version,
                new_version=new_version,
            )

        # Get log of changes
        log_result = subprocess.run(
            ["git", "log", "--oneline", f"{old_commit}..{new_commit}"],
            cwd=source_path,
            capture_output=True,
            text=True,
        )
        changes = log_result.stdout.strip() if log_result.returncode == 0 else None

        return UpdateResult(
            success=True,
            message=f"Updated from {old_commit} to {new_commit}",
            updated=True,
            old_version=old_version,
            new_version=new_version,
            details=changes,
        )

    except subprocess.CalledProcessError as e:
        return UpdateResult(
            success=False,
            message=f"Update failed: {e}",
            old_version=old_version,
        )


def update_pip() -> UpdateResult:
    """Update using pip install from GitHub.

    Returns:
        UpdateResult with update status.
    """
    old_version = get_current_version()

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--upgrade",
                f"git+{GITHUB_REPO}",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return UpdateResult(
                success=False,
                message=f"Pip upgrade failed: {result.stderr}",
                old_version=old_version,
            )

        # Get new version (need to reimport)
        new_version = get_current_version()

        if old_version == new_version:
            return UpdateResult(
                success=True,
                message="Already up to date",
                updated=False,
                old_version=old_version,
                new_version=new_version,
            )

        return UpdateResult(
            success=True,
            message=f"Updated from {old_version} to {new_version}",
            updated=True,
            old_version=old_version,
            new_version=new_version,
            details=result.stdout,
        )

    except Exception as e:
        return UpdateResult(
            success=False,
            message=f"Update failed: {e}",
            old_version=old_version,
        )


def update(force_pip: bool = False) -> UpdateResult:
    """Update kai-code from GitHub.

    Automatically detects whether the install is editable (development mode)
    or a regular pip install, and uses the appropriate update method.

    Args:
        force_pip: If True, force pip install even for editable installs.

    Returns:
        UpdateResult with update status and details.
    """
    is_editable, source_path = is_editable_install()

    if is_editable and source_path and not force_pip:
        return update_editable(source_path)
    else:
        return update_pip()


def format_update_result(result: UpdateResult) -> str:
    """Format an UpdateResult for display.

    Args:
        result: The UpdateResult to format.

    Returns:
        Formatted string for terminal output.
    """
    lines = []

    if result.success:
        if result.updated:
            lines.append(f"✓ {result.message}")
        else:
            lines.append(f"• {result.message}")
    else:
        lines.append(f"✗ {result.message}")

    if result.old_version:
        if result.new_version and result.old_version != result.new_version:
            lines.append(f"  Version: {result.old_version} → {result.new_version}")
        else:
            lines.append(f"  Version: {result.old_version}")

    if result.details:
        lines.append("")
        lines.append("Changes:")
        for line in result.details.split("\n")[:10]:  # Limit to 10 lines
            lines.append(f"  {line}")
        if result.details.count("\n") > 10:
            lines.append(f"  ... and {result.details.count(chr(10)) - 10} more")

    return "\n".join(lines)

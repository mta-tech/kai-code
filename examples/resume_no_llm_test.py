"""No-LLM test for the `kai resume` subcommand.

This test validates CLI argument parsing, state resolution, and error handling
without actually calling an LLM. It simulates interrupt states by creating
the necessary session and checkpoint files.

Run with:
    python examples/resume_no_llm_test.py
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

# Get the directory of this script to find the src directory
THIS_DIR = Path(__file__).parent.absolute()
SRC_DIR = THIS_DIR.parent / "src"


def run_cli(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run kai CLI and return the result."""
    env = os.environ.copy()
    # Ensure our local src is used, not any globally installed version
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    return subprocess.run(
        [sys.executable, "-m", "kai_code"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


def create_mock_session(root_dir: Path, *, thread_id: str = "test-thread-123") -> Path:
    """Create a mock session state file."""
    kai_dir = root_dir / ".kai"
    kai_dir.mkdir(parents=True, exist_ok=True)

    session_path = kai_dir / "session.json"
    state = {
        "messages": [
            {"role": "user", "content": "Test prompt"},
            {"role": "assistant", "content": "I need to execute a command."},
        ],
        "thread_id": thread_id,
        "model": "test:mock-model",
        "system_prompt": None,
        "skills_dir": ".skills",
    }
    session_path.write_text(json.dumps(state, indent=2))
    return session_path


def create_mock_checkpoint(root_dir: Path, *, thread_id: str = "test-thread-123") -> Path:
    """Create a mock checkpoint file that simulates an interrupted state."""
    kai_dir = root_dir / ".kai"
    kai_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = kai_dir / "checkpoints.pkl"

    # Create a minimal checkpoint structure that mimics KaiFileCheckpointer
    # This won't be a fully valid checkpoint, but it demonstrates the file exists
    storage: dict = defaultdict(lambda: defaultdict(dict))
    storage[thread_id][""]["checkpoint"] = {
        "v": 1,
        "ts": "2025-01-01T00:00:00.000000+00:00",
        "channel_values": {
            "messages": [
                {"role": "user", "content": "Test prompt"},
                {"role": "assistant", "content": "I need to execute a command."},
            ],
        },
        "pending_sends": [],
    }

    payload = {
        "storage": dict(storage),
        "writes": {},
        "blobs": {},
    }
    checkpoint_path.write_bytes(pickle.dumps(payload))
    return checkpoint_path


def create_mock_local_settings(root_dir: Path) -> Path:
    """Create a mock local settings file with last_session."""
    kai_dir = root_dir / ".kai"
    kai_dir.mkdir(parents=True, exist_ok=True)

    settings_path = kai_dir / "settings.local.json"
    settings = {
        "last_session": ".kai/session.json",
        "agents": {},
    }
    settings_path.write_text(json.dumps(settings, indent=2))
    return settings_path


def test_resume_help() -> None:
    """Test that resume --help works."""
    result = run_cli(["resume", "--help"])
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
    assert "resume" in result.stdout.lower()
    assert "--approve" in result.stdout
    assert "--reject" in result.stdout
    assert "--edit" in result.stdout
    print("  [PASS] resume --help")


def test_resume_missing_decision() -> None:
    """Test that resume fails without a decision flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_checkpoint(root)
        create_mock_local_settings(root)

        result = run_cli(["resume"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        # argparse outputs "one of the arguments" for required mutually exclusive groups
        assert ("required" in result.stderr.lower() or
                "approve" in result.stderr.lower() or
                "one of the arguments" in result.stderr.lower()), f"Unexpected stderr: {result.stderr}"
    print("  [PASS] resume without decision fails")


def test_resume_conflicting_decisions() -> None:
    """Test that resume fails with multiple decision flags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_checkpoint(root)
        create_mock_local_settings(root)

        result = run_cli(["resume", "--approve", "--reject"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        # argparse outputs "not allowed with argument"
        assert "not allowed" in result.stderr.lower(), f"Unexpected stderr: {result.stderr}"
    print("  [PASS] resume with conflicting decisions fails")


def test_resume_no_session() -> None:
    """Test that resume fails when no session exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Don't create any session files

        result = run_cli(["resume", "--approve"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        # Could be "no interrupted session" or "no session found"
        assert ("session" in result.stderr.lower() or
                "no" in result.stderr.lower()), f"Unexpected stderr: {result.stderr}"
    print("  [PASS] resume without session fails")


def test_resume_no_checkpoint() -> None:
    """Test that resume fails when checkpoint is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_local_settings(root)
        # Don't create checkpoint file

        result = run_cli(["resume", "--approve"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        assert "checkpoint" in result.stderr.lower()
    print("  [PASS] resume without checkpoint fails")


def test_resume_edit_invalid_json() -> None:
    """Test that resume --edit fails with invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_checkpoint(root)
        create_mock_local_settings(root)

        result = run_cli(["resume", "--edit", "not-valid-json"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        assert "json" in result.stderr.lower()
    print("  [PASS] resume --edit with invalid JSON fails")


def test_resume_edit_non_object() -> None:
    """Test that resume --edit fails when JSON is not an object."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_checkpoint(root)
        create_mock_local_settings(root)

        result = run_cli(["resume", "--edit", '["array", "not", "object"]'], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        assert "object" in result.stderr.lower() or "dict" in result.stderr.lower()
    print("  [PASS] resume --edit with non-object JSON fails")


def test_resume_named_agent_not_found() -> None:
    """Test that resume --agent fails when agent doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create local settings without the agent
        kai_dir = root / ".kai"
        kai_dir.mkdir(parents=True, exist_ok=True)
        settings_path = kai_dir / "settings.local.json"
        settings = {"last_session": None, "agents": {}}
        settings_path.write_text(json.dumps(settings))

        result = run_cli(["resume", "--approve", "--agent", "nonexistent"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        assert ("nonexistent" in result.stderr.lower() or
                "no session" in result.stderr.lower() or
                "agent" in result.stderr.lower()), f"Unexpected stderr: {result.stderr}"
    print("  [PASS] resume --agent with unknown agent fails")


def test_resume_explicit_state_path_not_found() -> None:
    """Test that resume --state-path fails when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        result = run_cli(["resume", "--approve", "--state-path", "/nonexistent/path.json"], cwd=root)
        assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
        assert ("not found" in result.stderr.lower() or
                "no such" in result.stderr.lower() or
                "state" in result.stderr.lower()), f"Unexpected stderr: {result.stderr}"
    print("  [PASS] resume --state-path with missing file fails")


def test_cli_backwards_compat() -> None:
    """Test that old-style CLI invocation still works (no subcommand)."""
    result = run_cli(["--dry-run", "-p", "hello", "--output-format", "json"])
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}\nstderr: {result.stderr}"

    payload = json.loads(result.stdout)
    assert payload["type"] == "dry-run"
    print("  [PASS] backwards-compatible CLI invocation")


def test_run_subcommand() -> None:
    """Test that 'kai run' subcommand works."""
    result = run_cli(["run", "--dry-run", "-p", "hello", "--output-format", "json"])
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}\nstderr: {result.stderr}"

    payload = json.loads(result.stdout)
    assert payload["type"] == "dry-run"
    print("  [PASS] 'kai run' subcommand")


def test_resume_dry_run() -> None:
    """Test that resume --dry-run works and outputs config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_checkpoint(root)
        create_mock_local_settings(root)

        result = run_cli(["resume", "--approve", "--dry-run", "--output-format", "json"], cwd=root)
        assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}\nstderr: {result.stderr}"

        payload = json.loads(result.stdout)
        assert payload["type"] == "dry-run"
        assert payload["command"] == "resume"
        assert payload["decision"] == "approve"
        assert "state_path" in payload
        assert "checkpoint_path" in payload
    print("  [PASS] resume --dry-run with JSON output")


def test_resume_dry_run_stream_json() -> None:
    """Test that resume --dry-run works with stream-json output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        create_mock_session(root)
        create_mock_checkpoint(root)
        create_mock_local_settings(root)

        result = run_cli(["resume", "--approve", "--dry-run", "--output-format", "stream-json"], cwd=root)
        assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}\nstderr: {result.stderr}"

        lines = [json.loads(line) for line in result.stdout.strip().splitlines()]
        assert len(lines) == 2
        assert lines[0]["type"] == "init"
        assert lines[0]["dry_run"] is True
        assert lines[1]["type"] == "result"
        assert lines[1]["dry_run"] is True
    print("  [PASS] resume --dry-run with stream-json output")


def main() -> int:
    """Run all no-LLM resume tests."""
    print("Running kai resume no-LLM tests...")
    print()

    tests = [
        test_resume_help,
        test_resume_missing_decision,
        test_resume_conflicting_decisions,
        test_resume_no_session,
        test_resume_no_checkpoint,
        test_resume_edit_invalid_json,
        test_resume_edit_non_object,
        test_resume_named_agent_not_found,
        test_resume_explicit_state_path_not_found,
        test_cli_backwards_compat,
        test_run_subcommand,
        test_resume_dry_run,
        test_resume_dry_run_stream_json,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

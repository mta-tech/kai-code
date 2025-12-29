from __future__ import annotations

import argparse
import os
import subprocess
import sys
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path


NO_LLM_EXAMPLES = [
    # Curated to avoid any LLM calls. (Exclude examples/basic_run.py)
    "cli_aliases_no_llm.py",
    "continue_default_session_no_llm.py",
    "event_id_monotonic_no_llm.py",
    "exit_codes_no_llm.py",
    "json_error_forced_no_llm.py",
    "json_schema_no_llm.py",
    "library_parity.py",
    "phase2_no_llm_cli.py",
    "resume_no_llm_cli.py",
    "resume_tools_override_no_llm.py",
    "stats_aggregate_no_llm.py",
    "stream_events_no_llm.py",
    "stream_events_non_openai_no_llm.py",
    "stream_json_traceback_no_llm.py",
    "tools_metadata_no_llm.py",
    "tool_call_id_synthesis_no_llm.py",
    "tool_latency_no_llm.py",
    "tool_result_fields_no_llm.py",
    "tool_result_pairing_mixed_ids_no_llm.py",
    "tool_result_pairing_no_llm.py",
    "turn_step_events_no_llm.py",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m kai_code.verify_no_llm",
        description="Run curated no-LLM example suite (suitable for CI).",
    )
    parser.add_argument("--list", action="store_true", help="List examples that will be run")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    repo_examples_dir = repo_root / "examples"

    @contextmanager
    def _get_examples_dir():
        if repo_examples_dir.exists():
            yield repo_examples_dir
            return

        with as_file(files("kai_code._examples")) as pkg_examples_dir:
            yield pkg_examples_dir

    with _get_examples_dir() as examples_dir:
        missing = [x for x in NO_LLM_EXAMPLES if not (Path(examples_dir) / x).exists()]
        if missing:
            print("Missing expected example files:", ", ".join(missing), file=sys.stderr)
            return 2

        if args.list:
            for ex in NO_LLM_EXAMPLES:
                print(ex)
            return 0

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(repo_root / "src"), env.get("PYTHONPATH", "")]
        ).strip(os.pathsep)

        failed: list[str] = []
        for ex in NO_LLM_EXAMPLES:
            path = Path(examples_dir) / ex
            print(f"== {ex}")
            proc = subprocess.run([sys.executable, str(path)], env=env)
            if proc.returncode != 0:
                failed.append(ex)

        if failed:
            print("Failed examples:", ", ".join(failed), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

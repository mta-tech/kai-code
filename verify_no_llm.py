import os
import sys


def main() -> int:
    repo_root = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(repo_root, "src"))
    from kai_code.verify_no_llm import main as _main

    return _main()


if __name__ == "__main__":
    raise SystemExit(main())


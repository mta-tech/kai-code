from __future__ import annotations

import os

from kai_code import KaiAgent


def main() -> int:
    # IMPORTANT: Do not hardcode keys. Provide via env.
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        raise SystemExit(
            "Missing GOOGLE_API_KEY (or GOOGLE_GENERATIVE_AI_API_KEY). Set it in your environment to run this live smoke test."
        )

    agent = KaiAgent(root_dir=".", model="google_genai:gemini-2.0-flash", yolo=True)
    result = agent.run("Reply with exactly: OK")
    print(result.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

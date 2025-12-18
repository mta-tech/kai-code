from kai_code import KaiAgent


def main() -> None:
    agent = KaiAgent(root_dir=".", model="openai:gpt-4o", yolo=True)
    result = agent.run("List the top-level files and summarize what this project does.")
    print(result.output)


if __name__ == "__main__":
    main()

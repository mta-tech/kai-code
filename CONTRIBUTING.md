# Contributing to Kai Code

Thank you for your interest in contributing to Kai Code! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- An API key for at least one LLM provider (OpenAI, Anthropic, or Google)

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR-USERNAME/kai-code.git
cd kai-code
```

2. **Create a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install in development mode**

```bash
pip install -e '.[openai]'  # or your preferred LLM provider
pip install pytest pytest-asyncio  # dev dependencies
```

4. **Configure API keys**

```bash
export OPENAI_API_KEY=your-key-here
# or create a .env file
```

5. **Verify installation**

```bash
python verify_no_llm.py  # Run no-LLM tests
kai --help               # Check CLI works
```

## Development Workflow

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/prompts/test_prompts.py -v

# No-LLM verification (fast, safe for CI)
python verify_no_llm.py
```

### Code Style

We follow these conventions:

- **Type hints**: Required for all function parameters and return values
- **Docstrings**: Required for public APIs, use Google style
- **Line length**: 100 characters max
- **Imports**: stdlib, third-party, local (separated by blank lines)

### Commit Messages

Use clear, descriptive commit messages:

```
feat: Add support for Claude 3.5 Sonnet
fix: Handle empty response from LLM gracefully
docs: Update README with new CLI flags
refactor: Simplify permission checking logic
test: Add tests for brainstorming workflow
```

## Types of Contributions

### Bug Reports

1. Check existing issues first
2. Use the bug report template
3. Include:
   - Python version
   - Kai Code version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/tracebacks

### Feature Requests

1. Check existing issues/discussions
2. Describe the use case
3. Explain why it would benefit users
4. Consider implementation approach

### Pull Requests

1. **Create an issue first** for significant changes
2. **Fork and branch** from `main`
3. **Keep PRs focused** - one feature/fix per PR
4. **Add tests** for new functionality
5. **Update documentation** if needed
6. **Follow code style** guidelines

## Architecture Guidelines

### Adding a New Agent

See [Custom Agents Guide](docs/guides/custom-agents.md) for detailed instructions.

1. Create agent class in `src/kai_code/agents/your_agent/`
2. Extend `KaiAgent` base class
3. Create system prompt in `src/kai_code/prompts/your-agent.md`
4. Add CLI entry point
5. Register in `pyproject.toml`

### Adding Tools

```python
from langchain_core.tools import tool

@tool("my_tool")
def my_tool(arg: str) -> str:
    """Clear description for the LLM.

    Args:
        arg: What this argument is for

    Returns:
        Description of return value
    """
    # Implementation
    return result
```

### Modifying Prompts

1. Edit files in `src/kai_code/prompts/`
2. Use `# INHERIT: parent-prompt` for inheritance
3. Test with different LLMs
4. Keep prompts focused and clear

## Testing Guidelines

### Test Structure

```
tests/
├── agents/           # Agent-specific tests
├── prompts/          # Prompt loading tests
├── e2e/              # End-to-end tests
└── test_*.py         # Unit tests
```

### Writing Tests

```python
import pytest
from kai_code import KaiAgent

def test_agent_creation():
    """Test that agent can be created with default settings."""
    agent = KaiAgent(root_dir=".", yolo=True)
    assert agent is not None

def test_tool_execution():
    """Test that custom tool returns expected result."""
    # Test implementation
    pass
```

### Running Specific Tests

```bash
# Run tests matching a pattern
python -m pytest tests/ -k "test_agent" -v

# Run with coverage
python -m pytest tests/ --cov=kai_code --cov-report=html
```

## Documentation

### Structure

```
docs/
├── tutorials/        # Step-by-step guides for beginners
├── guides/           # In-depth topic guides
└── api/              # API reference
```

### Writing Documentation

- Use clear, concise language
- Include code examples
- Test all examples work
- Link to related docs

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. After merge, tag the release
5. GitHub Actions builds and publishes

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Security**: Email security@kai-code.dev

## Code of Conduct

Be respectful and constructive. We're all here to build something useful together.

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 license.

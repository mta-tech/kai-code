"""Prompt templates for compaction summarization."""

# Default system prompt for message summarization
SUMMARIZATION_SYSTEM_PROMPT = """You are compacting AI conversation history to save tokens while preserving critical information.

SUMMARIZE the following conversation messages into a concise representation that:
- Preserves all file paths, function names, variable names, error messages
- Captures the core intent and outcome of each exchange
- Removes redundant explanations and conversational filler
- Uses bullet points for structured information
- Keeps code snippets only if they show unique patterns or solutions

Your output will replace the original messages in the conversation history."""


def build_summarization_prompt(messages: list[str]) -> str:
    """Build a prompt for summarizing a batch of messages.

    Args:
        messages: Formatted message strings to summarize

    Returns:
        Complete prompt for LLM
    """
    messages_text = "\n\n".join(messages)

    return f"""{SUMMARIZATION_SYSTEM_PROMPT}

INPUT MESSAGES:
{messages_text}

OUTPUT FORMAT:
[COMPACTED] Summary of {len(messages)} message exchange
- Key points extracted
- Important technical details preserved
- File references: list paths mentioned
- Next context: what should be remembered for continuation"""

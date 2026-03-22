import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.gemini_client import call
from config import (
    MODEL_FLASH,
    DEFAULT_MAX_CONTEXT_TOKENS,
    DEFAULT_ROLLING_WINDOW,
    SUMMARIZE_THRESHOLD_TOKENS,
    L5_SUMMARIZE_SYSTEM,
    L5_SUMMARIZE_KEEP_LAST,
)
from metrics import estimate_tokens


def estimate_history_tokens(messages: list) -> int:
    return sum(estimate_tokens(m.get("content", "")) for m in messages)


def rolling_window(messages: list, max_turns: int = DEFAULT_ROLLING_WINDOW) -> list:
    system = [m for m in messages if m.get("role") == "system"]
    convo = [m for m in messages if m.get("role") != "system"]
    return system + convo[-max_turns:]


def summarize_history(messages: list, keep_last: int = L5_SUMMARIZE_KEEP_LAST) -> list:
    if estimate_history_tokens(messages) < SUMMARIZE_THRESHOLD_TOKENS:
        return messages

    system = [m for m in messages if m.get("role") == "system"]
    convo = [m for m in messages if m.get("role") != "system"]

    if len(convo) <= keep_last:
        return messages

    to_summarize = convo[:-keep_last]
    to_keep = convo[-keep_last:]
    formatted = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in to_summarize)

    summary = call(
        prompt=formatted,
        model=MODEL_FLASH,
        system=L5_SUMMARIZE_SYSTEM,
        max_tokens=300,
        temperature=0.1,
    )

    summary_message = {
        "role": "assistant",
        "content": f"[Summary of prior conversation]\n{summary.strip()}",
    }

    return system + [summary_message] + to_keep


def enforce_token_budget(messages: list, max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS) -> list:
    trimmed = list(messages)

    while estimate_history_tokens(trimmed) > max_tokens:
        removed = False
        for i, m in enumerate(trimmed):
            if m.get("role") != "system":
                trimmed.pop(i)
                removed = True
                break
        if not removed:
            break

    return trimmed

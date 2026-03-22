import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import L2_AUDIT_FILLER_PHRASES

SYSTEM_PROMPTS = {
    "simple_qa": "Answer concisely. Acknowledge uncertainty.",
    "code_gen": "Write code only. No prose unless asked.",
    "code_review": "Strict reviewer. List issues only.",
    "analysis": "Analyst. Be precise. Cite assumptions.",
    "explain": "Teacher. Simple language. Examples first.",
    "creative": "Creative writer. Original ideas.",
    "default": "Answer concisely and accurately.",
}


def get_system_prompt(intent: str) -> str:
    return SYSTEM_PROMPTS.get(intent, SYSTEM_PROMPTS["default"])


def get_system_with_context(intent: str, static_document: str = None) -> str:
    base = get_system_prompt(intent)
    if not static_document:
        return base
    return f"{base}\n\nContext:\n{static_document}"


def audit_system_prompt(prompt: str) -> dict:
    tokens = len(prompt.split()) * 1.3
    issues = [
        f"Contains filler: '{pattern}'"
        for pattern in L2_AUDIT_FILLER_PHRASES
        if pattern in prompt.lower()
    ]
    return {
        "tokens": int(tokens),
        "issues": issues,
        "recommendation": "compress" if tokens > 50 or issues else "ok",
    }

# api/layers/l1.py
import sys, os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.gemini_client import call
from config import MODEL_FLASH, L1_STRIP_PREFIXES, L1_INLINE_NOISE_WORDS
from metrics import estimate_tokens

COMPRESSION_SYSTEM = """You are a prompt compression engine. Rewrite to MINIMUM tokens while preserving intent.

REMOVE immediately:
- Hedging phrases: "or maybe", "i think", "something like", "maybe not", "possibly"
- Uncertainty qualifiers: "i know", "i guess", "i believe", "it seems"
- Conversational filler: "can you", "could you", "i want you to", "please", "thanks"
- Redundant restatements: if the same request appears 2+ times in different words, keep ONCE
- Meta-instructions: "in your response", "make sure to include", "don't forget"
- Role preambles: "you are a senior engineer", "pretend to be", "act as a"
- Examples prefixes: "for example", "e.g.", "such as" (keep the examples, remove prefixes)

KEEP all:
- Technical requirements, constraints, logic
- All numbers, identifiers, names, URLs
- Output format specs (JSON, bullets, code, etc)

Output ONLY the compressed prompt. No explanation, no preamble, no quotes."""

FILLER_PATTERNS = L1_STRIP_PREFIXES


def rule_based_compress(prompt: str) -> str:
    """Fast rule-based pre-pass. Zero API calls."""
    lines = prompt.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower in FILLER_PATTERNS:
            continue

        updated = stripped
        prefix_removed = True
        while prefix_removed and updated:
            prefix_removed = False
            lower_updated = updated.lower()
            for pattern in FILLER_PATTERNS:
                if lower_updated.startswith(pattern):
                    updated = updated[len(pattern):].lstrip(" ,:-")
                    prefix_removed = True
                    break

        for noise_word in L1_INLINE_NOISE_WORDS:
            updated = re.sub(rf"\b{re.escape(noise_word)}\b", "", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\s+", " ", updated).strip(" ,:-")

        if updated and any(ch.isalnum() for ch in updated):
            cleaned.append(updated)

    result = "\n".join(cleaned).strip()
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result


def llm_compress(prompt: str) -> str:
    """LLM compression via Gemini Flash. Always compress for max savings."""
    try:
        return call(
            prompt=prompt,
            model=MODEL_FLASH,
            system=COMPRESSION_SYSTEM,
            max_tokens=300,
            temperature=0.1,
        )
    except Exception:
        return prompt


def compress(prompt: str, use_llm: bool = True) -> dict:
    """
    Full pipeline: rule-based pre-pass then optional LLM compression.

    Returns:
        {"original", "compressed", "tokens_before", "tokens_after", "savings_pct"}
    """
    tokens_before = estimate_tokens(prompt)
    after_rules = rule_based_compress(prompt)
    compressed = llm_compress(after_rules) if use_llm else after_rules
    tokens_after = estimate_tokens(compressed)
    savings_pct = round((1 - tokens_after / tokens_before) * 100) if tokens_before > 0 else 0

    return {
        "original": prompt,
        "compressed": compressed,
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "savings_pct": savings_pct,
    }

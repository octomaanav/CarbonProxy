import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import MAX_TOKENS_BY_INTENT

OUTPUT_CONSTRAINTS = {
    "one_sentence": "Answer in exactly one sentence.",
    "two_sentences": "Answer in 1-2 sentences.",
    "bullets_3": "Respond with exactly 3 bullet points. No prose.",
    "bullets_5": "Respond with up to 5 bullet points. No prose.",
    "code_only": "Output code only. No explanation unless asked.",
    "json_only": "Output valid JSON only. No prose. No markdown fences.",
    "tldr": "TL;DR only. Maximum 30 words.",
    "word_limit_50": "Answer in under 50 words.",
    "word_limit_100": "Answer in under 100 words.",
}


def get_max_tokens(intent: str, output_format: str = None) -> int:
    base = MAX_TOKENS_BY_INTENT.get(intent, MAX_TOKENS_BY_INTENT["default"])
    
    # Structured output formats need more room to complete properly
    if output_format == "bullets":
        return max(base, 1200)  # Bullets need substantial space for 3-5 complete points
    elif output_format == "json":
        return max(base, 800)  # JSON needs structure + data
    elif output_format == "code":
        return max(base, 1500)  # Code often needs more space
    
    return base


def build_structured_prompt(
    prompt: str,
    output_format: str = None,
    max_words: int = None,
    bullet_count: int = None,
) -> str:
    constraints = []
    if output_format == "json":
        constraints.append("Output valid JSON only. No prose.")
    elif output_format == "code":
        constraints.append("Output code only. No explanation.")
    elif output_format == "bullets" and bullet_count:
        constraints.append(f"Respond with exactly {bullet_count} bullet points.")

    if max_words:
        constraints.append(f"Answer in under {max_words} words.")

    if not constraints:
        return prompt

    return prompt + "\n\n" + " ".join(constraints)


def build_json_prompt(prompt: str, schema: dict) -> str:
    schema_str = ", ".join(f'"{k}": {v}' for k, v in schema.items())
    return f"{prompt}\n\nRespond with ONLY valid JSON: {{{schema_str}}}\nNo prose. No markdown."

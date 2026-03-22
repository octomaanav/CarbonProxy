# api/layers/l1.py
import sys, os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.gemini_client import call
from config import MODEL_FLASH, L1_STRIP_PREFIXES, L1_INLINE_NOISE_WORDS
from metrics import estimate_tokens_for_model

COMPRESSION_SYSTEM = """You are a prompt compression engine.
Rewrite to minimum tokens while FULLY preserving intent.

Remove: filler, politeness, hedging, role preambles,
        apologies, redundant restatements, meta-instructions.

NEVER remove:
- JSON schemas, field names, or data structures
- Specific numbers, IDs, or technical values
- Negative constraints ("do not use X", "without Y")
- Action verbs that define the task (review vs design vs implement)
- Security or error handling requirements
- Named algorithms, libraries, or technologies

When a prompt contains JSON: keep all field names compressed
into inline notation like {field1, field2, nested{a,b}}.

Output ONLY the compressed prompt. No explanation."""

FILLER_PATTERNS = L1_STRIP_PREFIXES
ACTION_VERBS = {
    "review", "design", "implement", "explain", "analyze", "compare",
    "audit", "debug", "refactor", "suggest", "improve", "flag",
    "write", "filter", "group", "calculate", "sort"
}

CONSTRAINT_PHRASES = [
    "do not use recursion",
    "do not use pandas",
    "do not use numpy",
    "stateless between runs",
    "do not cache any intermediate computation results",
    "must not change",
]


def _extract_action_verbs(text: str) -> set[str]:
    lower = text.lower()
    verbs = set()

    directive_matches = re.findall(
        r"\b(?:need to|want to|must|should|please|can you|could you|to)\s+([a-z]+)\b",
        lower,
    )
    for verb in directive_matches:
        if verb in ACTION_VERBS:
            verbs.add(verb)

    imperative_matches = re.findall(
        r"(?:^|[\.!?]\s+|\n)\s*([a-z]+)\b",
        lower,
    )
    for verb in imperative_matches:
        if verb in ACTION_VERBS:
            verbs.add(verb)

    return verbs


def _extract_schema_fields(text: str) -> list[str]:
    line_fields = re.findall(
        r"(?m)^\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?\s*:\s*(?:[\"'\{\[\d\-tfn])",
        text,
    )
    inline_fields = re.findall(
        r"[\{,]\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?\s*:",
        text,
    )
    inline_list_fields = []
    for block in re.findall(r"\{([^{}]+)\}", text):
        for token in block.split(","):
            candidate = token.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate):
                continue
            inline_list_fields.append(candidate)

    fields = line_fields + inline_fields + inline_list_fields
    skip = {
        "request", "response", "schema", "schemas",
        "important", "input", "output", "cache", "config",
    }
    seen = set()
    ordered = []
    for field in fields:
        normalized = field.strip()
        if not normalized:
            continue
        if normalized.lower() in skip:
            continue
        if normalized not in seen:
            seen.add(normalized)
            ordered.append(field)
    return ordered


def _extract_complexity(original: str) -> str | None:
    match = re.search(r"\bO\([^\)]*\)", original)
    if match:
        return match.group(0)
    return None


def _enforce_semantic_safety(original: str, compressed: str, fallback: str) -> str:
    original_verbs = _extract_action_verbs(original)
    compressed_verbs = _extract_action_verbs(compressed)

    if original_verbs and not (original_verbs.intersection(compressed_verbs)):
        return fallback

    original_lower = original.lower()
    compressed_lower = compressed.lower()

    needs_review = "review" in original_lower
    needs_redesign = "redesign" in original_lower or "design" in original_lower
    if needs_review and "review" not in compressed_lower:
        compressed = "Review existing pipeline. " + compressed.lstrip()
        compressed_lower = compressed.lower()
    if needs_redesign and not ("redesign" in compressed_lower or "design" in compressed_lower):
        compressed = compressed.rstrip(" .") + ". Redesign from scratch."
        compressed_lower = compressed.lower()

    complexity = _extract_complexity(original)
    if complexity and complexity.lower() not in compressed_lower:
        compressed = compressed.rstrip(" .") + f" Complexity: {complexity} or better."
        compressed_lower = compressed.lower()

    for phrase in CONSTRAINT_PHRASES:
        if phrase in original_lower and phrase not in compressed_lower:
            compressed = compressed.rstrip(" .") + f" Constraint: {phrase}."
            compressed_lower = compressed.lower()

    if "security" in original_lower and "security" not in compressed_lower:
        compressed = compressed.rstrip(" .") + ". Flag security concerns."
        compressed_lower = compressed.lower()

    original_fields = _extract_schema_fields(original)
    compressed_fields = set(_extract_schema_fields(compressed))

    if len(original_fields) >= 3:
        kept = [field for field in original_fields if field in compressed_fields]
        if len(kept) < min(3, len(original_fields)):
            inline_fields = ", ".join(original_fields[:20])
            compressed = compressed.rstrip(" .") + f" Schemas: {{{inline_fields}}}."

    return compressed


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


def compress(
    prompt: str,
    use_llm: bool = True,
    token_model: str = MODEL_FLASH,
    token_provider: str = "google",
) -> dict:
    """
    Full pipeline: rule-based pre-pass then optional LLM compression.

    Returns:
        {"original", "compressed", "tokens_before", "tokens_after", "savings_pct"}
    """
    tokens_before = estimate_tokens_for_model(
        prompt,
        model=token_model,
        provider=token_provider,
    )
    after_rules = rule_based_compress(prompt)
    compressed = llm_compress(after_rules) if use_llm else after_rules
    compressed = _enforce_semantic_safety(prompt, compressed, after_rules)
    tokens_after = estimate_tokens_for_model(
        compressed,
        model=token_model,
        provider=token_provider,
    )
    savings_pct = round((1 - tokens_after / tokens_before) * 100) if tokens_before > 0 else 0

    return {
        "original": prompt,
        "compressed": compressed,
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "savings_pct": savings_pct,
    }

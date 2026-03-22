import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.gemini_client import call
from config import (
    MODEL_FLASH,
    MODEL_PRO,
    ROUTE_FLASH_MAX_TOKENS,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    META_API_KEY,
    PROVIDER_MODEL_CATALOG,
    L4_INTENT_KEYWORDS,
)
from metrics import estimate_tokens

TASK_TYPE_ROUTES = {
    "simple_qa": MODEL_FLASH,
    "code_gen": MODEL_FLASH,
    "code_review": MODEL_FLASH,
    "analysis": MODEL_FLASH,
    "explain": MODEL_FLASH,
    "creative": MODEL_FLASH,
    "architecture": MODEL_PRO,
    "default": MODEL_FLASH,
}

_PROVIDER_KEYS = {
    "google": GEMINI_API_KEY,
    "openai": OPENAI_API_KEY,
    "anthropic": ANTHROPIC_API_KEY,
    "meta": META_API_KEY,
}

CLASSIFY_SYSTEM = """Classify this prompt into one category:
simple_qa, code_gen, code_review, analysis, explain, creative, architecture
Reply with ONLY the category name. Nothing else."""


def _heuristic_intent(prompt: str) -> str:
    p = prompt.lower()

    for intent, keywords in L4_INTENT_KEYWORDS.items():
        if any(keyword in p for keyword in keywords):
            return intent

    return "simple_qa"


def classify_intent(prompt: str) -> str:
    heuristic = _heuristic_intent(prompt)
    if heuristic in TASK_TYPE_ROUTES and heuristic != "simple_qa":
        return heuristic

    try:
        result = call(
            prompt=prompt[:300],
            model=MODEL_FLASH,
            system=CLASSIFY_SYSTEM,
            max_tokens=15,
            temperature=0.0,
        )
        intent = result.strip().lower().split()[0]
        if intent in TASK_TYPE_ROUTES:
            return intent
    except Exception:
        pass

    return heuristic if heuristic in TASK_TYPE_ROUTES else "default"


def _provider_available(provider: str) -> bool:
    key = _PROVIDER_KEYS.get(provider, "")
    return bool(key)


def _pick_best_model(intent: str) -> dict:
    candidates = PROVIDER_MODEL_CATALOG.get(intent, PROVIDER_MODEL_CATALOG["default"])
    for candidate in candidates:
        provider = candidate["provider"]
        if _provider_available(provider):
            return candidate

    return {
        "provider": "google",
        "model": TASK_TYPE_ROUTES.get(intent, MODEL_FLASH),
    }


def route(prompt: str, task_type: str = None, use_classifier: bool = True) -> dict:
    if task_type and task_type in TASK_TYPE_ROUTES:
        picked = _pick_best_model(task_type)
        return {
            "provider": picked["provider"],
            "model": picked["model"],
            "intent": task_type,
            "reason": f"explicit override: {task_type}",
        }

    if use_classifier:
        intent = classify_intent(prompt)
        picked = _pick_best_model(intent)
        return {
            "provider": picked["provider"],
            "model": picked["model"],
            "intent": intent,
            "reason": f"classifier: {intent}; provider: {picked['provider']}",
        }

    tokens = estimate_tokens(prompt)
    intent = "simple_qa" if tokens <= ROUTE_FLASH_MAX_TOKENS else "architecture"
    picked = _pick_best_model(intent)
    return {
        "provider": picked["provider"],
        "model": picked["model"],
        "intent": "default",
        "reason": f"token count: {tokens}",
    }

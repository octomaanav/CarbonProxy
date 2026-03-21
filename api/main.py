from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from math import ceil
from typing import Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel


def estimate_tokens(text: str) -> int:
    if not text.strip():
        return 0
    return ceil(len(text.split()) * 1.3)


def estimate_co2(tokens_in: int, tokens_out: int, model: str) -> float:
    kwh_per_token = 0.0000002
    grid_intensity = 400
    model_multiplier = {
        "claude-haiku-4-5": 0.1,
        "claude-haiku-3": 0.1,
        "claude-sonnet-4-5": 1.0,
        "claude-sonnet-3-5": 1.0,
        "claude-opus-4-5": 3.0,
        "claude-opus-3": 3.0,
        "gpt-4o-mini": 0.2,
        "gpt-4o": 1.5,
        "gpt-4": 2.0,
        "cache": 0.0,
    }
    total = tokens_in + tokens_out
    mult = model_multiplier.get(model, 1.0)
    co2 = total * kwh_per_token * mult * grid_intensity
    return round(co2, 6)


def co2_to_equivalent(grams: float) -> str:
    if grams == 0:
        return "nothing — cache hit"
    if grams < 0.001:
        return "less than a breath of air"
    if grams < 0.01:
        return f"{(grams * 1000):.1f}mg — a few keystrokes of energy"
    if grams < 0.1:
        return f"{(grams * 30):.1f}m of phone scrolling"
    if grams < 1.0:
        return f"{(grams * 0.5):.2f} seconds of laptop use"
    if grams < 10:
        return f"{(grams / 10):.2f}g of coal equivalent"
    return f"{(grams / 1000):.3f}kg CO₂"


def compress_prompt(prompt: str) -> str:
    text = " ".join(prompt.split())
    max_words = 32
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


def choose_model(tokens_after: int) -> str:
    if tokens_after <= 30:
        return "claude-haiku-4-5"
    if tokens_after <= 120:
        return "claude-sonnet-4-5"
    return "gpt-4o"


class PromptRequest(BaseModel):
    prompt: str


class CacheStoreRequest(BaseModel):
    prompt: str
    response: str


class CacheRecord(BaseModel):
    prompt: str
    response: str


@dataclass
class SessionState:
    requests: int = 0
    tokens_saved: int = 0
    co2_saved_g: float = 0.0
    cache_hits: int = 0
    history: List[Dict[str, object]] = field(default_factory=list)
    cache: List[CacheRecord] = field(default_factory=list)


state = SessionState()

app = FastAPI(title="CarbonProxy API", version="0.1.0")


@app.get("/api/health")
def health() -> Dict[str, object]:
    return {"status": "ok", "cache_size": len(state.cache)}


@app.post("/api/cache/check")
def cache_check(body: PromptRequest) -> Dict[str, object]:
    prompt = body.prompt.strip()
    if not prompt:
        return {"hit": False, "cached_response": None, "similarity": 0.0}

    best: Optional[CacheRecord] = None
    best_score = 0.0

    for item in state.cache:
        score = SequenceMatcher(None, prompt.lower(), item.prompt.lower()).ratio()
        if score > best_score:
            best_score = score
            best = item

    if best and best_score >= 0.92:
        state.requests += 1
        state.cache_hits += 1
        state.history.append({"model": "cache", "co2_g": 0.0, "cached": True})
        return {"hit": True, "cached_response": best.response, "similarity": round(best_score, 4)}

    return {"hit": False, "cached_response": None, "similarity": round(best_score, 4)}


@app.post("/api/cache/store")
def cache_store(body: CacheStoreRequest) -> Dict[str, bool]:
    if body.prompt.strip() and body.response.strip():
        state.cache.append(CacheRecord(prompt=body.prompt, response=body.response))
    return {"stored": True}


@app.post("/api/optimize")
def optimize(body: PromptRequest) -> Dict[str, object]:
    prompt = body.prompt.strip()

    tokens_before = estimate_tokens(prompt)
    optimized_prompt = compress_prompt(prompt)
    tokens_after = estimate_tokens(optimized_prompt)
    savings_pct = 0 if tokens_before == 0 else max(0, round(((tokens_before - tokens_after) / tokens_before) * 100))

    model = choose_model(tokens_after)

    response = (
        "CarbonProxy backend demo response:\n\n"
        f"Optimized prompt: {optimized_prompt}\n"
        f"Suggested model: {model}\n"
        "(Connect your real LLM pipeline here.)"
    )
    tokens_out = estimate_tokens(response)
    co2_g = estimate_co2(tokens_after, tokens_out, model)

    state.requests += 1
    state.tokens_saved += max(0, tokens_before - tokens_after)
    state.co2_saved_g = round(state.co2_saved_g + co2_g, 6)
    state.history.append({"model": model, "co2_g": co2_g, "cached": False})

    return {
        "original_prompt": prompt,
        "optimized_prompt": optimized_prompt,
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "savings_pct": savings_pct,
        "cache_hit": False,
        "cached_response": None,
        "response": response,
        "co2_g": co2_g,
        "model": model,
    }


@app.get("/api/metrics")
def metrics() -> Dict[str, object]:
    return {
        "requests": state.requests,
        "tokens_saved": state.tokens_saved,
        "co2_saved_g": round(state.co2_saved_g, 6),
        "cache_hits": state.cache_hits,
        "co2_equivalent": co2_to_equivalent(state.co2_saved_g),
        "history": state.history,
    }


@app.post("/api/demo/reset")
def demo_reset() -> Dict[str, bool]:
    state.requests = 0
    state.tokens_saved = 0
    state.co2_saved_g = 0.0
    state.cache_hits = 0
    state.history = []
    state.cache = []
    return {"ok": True}

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from math import ceil
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    if not text.strip():
        return 0
    return ceil(len(text.split()) * 1.3)


MODEL_MULTIPLIER = {
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

# Approximate $/1K tokens for input (rough estimates for demo)
MODEL_COST_PER_1K = {
    "claude-haiku-4-5": 0.00025,
    "claude-haiku-3": 0.00025,
    "claude-sonnet-4-5": 0.003,
    "claude-sonnet-3-5": 0.003,
    "claude-opus-4-5": 0.015,
    "claude-opus-3": 0.015,
    "gpt-4o-mini": 0.00015,
    "gpt-4o": 0.005,
    "gpt-4": 0.03,
    "cache": 0.0,
}

KWH_PER_TOKEN = 0.0000002
GRID_INTENSITY = 400  # gCO2/kWh


def estimate_co2(tokens_in: int, tokens_out: int, model: str) -> float:
    total = tokens_in + tokens_out
    mult = MODEL_MULTIPLIER.get(model, 1.0)
    co2 = total * KWH_PER_TOKEN * mult * GRID_INTENSITY
    return round(co2, 6)


def estimate_kwh(tokens_in: int, tokens_out: int, model: str) -> float:
    total = tokens_in + tokens_out
    mult = MODEL_MULTIPLIER.get(model, 1.0)
    return round(total * KWH_PER_TOKEN * mult, 10)


def estimate_cost_usd(tokens_in: int, tokens_out: int, model: str) -> float:
    total = tokens_in + tokens_out
    rate = MODEL_COST_PER_1K.get(model, 0.003)
    return round((total / 1000) * rate, 8)


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


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    prompt: str


class CacheStoreRequest(BaseModel):
    prompt: str
    response: str


class CacheRecord(BaseModel):
    prompt: str
    response: str


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

@dataclass
class HistoryEntry:
    model: str
    co2_g: float
    cached: bool
    timestamp: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    kwh: float
    prompt_preview: str


@dataclass
class SessionState:
    requests: int = 0
    tokens_saved: int = 0
    co2_saved_g: float = 0.0
    cache_hits: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_kwh: float = 0.0
    history: List[HistoryEntry] = field(default_factory=list)
    cache: List[CacheRecord] = field(default_factory=list)


state = SessionState()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="CarbonProxy API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Existing endpoints (used by VS Code extension — kept stable)
# ---------------------------------------------------------------------------

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
        tokens_in = estimate_tokens(prompt)
        state.requests += 1
        state.cache_hits += 1
        state.total_tokens_in += tokens_in
        entry = HistoryEntry(
            model="cache",
            co2_g=0.0,
            cached=True,
            timestamp=time.time(),
            tokens_in=tokens_in,
            tokens_out=0,
            cost_usd=0.0,
            kwh=0.0,
            prompt_preview=prompt[:60],
        )
        state.history.append(entry)
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
    kwh = estimate_kwh(tokens_after, tokens_out, model)
    cost = estimate_cost_usd(tokens_after, tokens_out, model)

    state.requests += 1
    state.tokens_saved += max(0, tokens_before - tokens_after)
    state.co2_saved_g = round(state.co2_saved_g + co2_g, 6)
    state.total_tokens_in += tokens_after
    state.total_tokens_out += tokens_out
    state.total_cost_usd = round(state.total_cost_usd + cost, 8)
    state.total_kwh = round(state.total_kwh + kwh, 10)

    entry = HistoryEntry(
        model=model,
        co2_g=co2_g,
        cached=False,
        timestamp=time.time(),
        tokens_in=tokens_after,
        tokens_out=tokens_out,
        cost_usd=cost,
        kwh=kwh,
        prompt_preview=prompt[:60],
    )
    state.history.append(entry)

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
    """Legacy metrics endpoint — kept for VS Code extension compatibility."""
    return {
        "requests": state.requests,
        "tokens_saved": state.tokens_saved,
        "co2_saved_g": round(state.co2_saved_g, 6),
        "cache_hits": state.cache_hits,
        "co2_equivalent": co2_to_equivalent(state.co2_saved_g),
        "history": [
            {"model": h.model, "co2_g": h.co2_g, "cached": h.cached}
            for h in state.history
        ],
    }


@app.post("/api/demo/reset")
def demo_reset() -> Dict[str, bool]:
    state.requests = 0
    state.tokens_saved = 0
    state.co2_saved_g = 0.0
    state.cache_hits = 0
    state.total_tokens_in = 0
    state.total_tokens_out = 0
    state.total_cost_usd = 0.0
    state.total_kwh = 0.0
    state.history = []
    state.cache = []
    return {"ok": True}


# ---------------------------------------------------------------------------
# New dashboard endpoint — rich aggregated data for the web frontend
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def dashboard() -> Dict[str, object]:
    hit_rate = round((state.cache_hits / state.requests) * 100, 1) if state.requests > 0 else 0.0

    # Model distribution
    model_counts: Counter = Counter()
    for h in state.history:
        model_counts[h.model] += 1
    model_distribution = [
        {"model": m, "count": c} for m, c in model_counts.most_common()
    ]

    # Timeline (cumulative CO₂)
    cumulative = 0.0
    timeline = []
    for h in state.history:
        cumulative = round(cumulative + h.co2_g, 6)
        timeline.append({
            "timestamp": h.timestamp,
            "co2_g": h.co2_g,
            "cumulative_co2": cumulative,
            "tokens_in": h.tokens_in,
            "model": h.model,
            "cached": h.cached,
        })

    # Recent activity (last 20, newest first)
    recent = []
    for h in reversed(state.history[-20:]):
        recent.append({
            "model": h.model,
            "co2_g": h.co2_g,
            "cached": h.cached,
            "timestamp": h.timestamp,
            "tokens_in": h.tokens_in,
            "tokens_out": h.tokens_out,
            "cost_usd": h.cost_usd,
            "prompt_preview": h.prompt_preview,
        })

    # Per-request avg for team projection
    avg_co2 = (state.co2_saved_g / state.requests) if state.requests > 0 else 0
    annual_team_g = round(avg_co2 * 10 * 50 * 250, 2)  # 10 devs, 50 queries/day, 250 days

    return {
        "summary": {
            "requests": state.requests,
            "tokens_saved": state.tokens_saved,
            "total_tokens_in": state.total_tokens_in,
            "total_tokens_out": state.total_tokens_out,
            "co2_saved_g": round(state.co2_saved_g, 6),
            "cache_hits": state.cache_hits,
            "cache_hit_rate": hit_rate,
            "co2_equivalent": co2_to_equivalent(state.co2_saved_g),
        },
        "energy": {
            "total_kwh": round(state.total_kwh, 8),
            "total_cost_usd": round(state.total_cost_usd, 6),
            "annual_team_co2_g": annual_team_g,
        },
        "model_distribution": model_distribution,
        "timeline": timeline,
        "recent_activity": recent,
    }

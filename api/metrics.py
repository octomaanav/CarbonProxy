from config import KWH_PER_TOKEN, GRID_INTENSITY, MODEL_MULTIPLIERS, MODEL_COST_PER_1M_TOKENS_USD
from dataclasses import dataclass, field
from typing import List
import time


@dataclass
class RequestRecord:
    model: str
    tokens_before: int
    tokens_after: int
    tokens_used: int
    co2_g: float
    cached: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionMetrics:
    requests: int = 0
    tokens_saved: int = 0
    co2_saved_g: float = 0.0
    cache_hits: int = 0
    history: List[RequestRecord] = field(default_factory=list)

    def record(self, rec: RequestRecord) -> None:
        self.requests += 1
        self.tokens_saved += max(0, rec.tokens_before - rec.tokens_after)
        self.co2_saved_g = round(self.co2_saved_g + rec.co2_g, 6)
        if rec.cached:
            self.cache_hits += 1
        self.history.append(rec)

    def to_dict(self) -> dict:
        hit_rate = round(self.cache_hits / self.requests * 100) if self.requests else 0
        return {
            "requests": self.requests,
            "tokens_saved": self.tokens_saved,
            "co2_saved_g": self.co2_saved_g,
            "cache_hits": self.cache_hits,
            "cache_hit_rate_pct": hit_rate,
            "co2_equivalent": co2_to_equivalent(self.co2_saved_g),
        }

    def reset(self) -> None:
        self.requests = 0
        self.tokens_saved = 0
        self.co2_saved_g = 0.0
        self.cache_hits = 0
        self.history.clear()


def estimate_co2(tokens: int, model: str) -> float:
    multiplier = MODEL_MULTIPLIERS.get(model, 0.1)
    kwh = tokens * KWH_PER_TOKEN * multiplier
    return round(kwh * GRID_INTENSITY, 6)


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def estimate_cost_usd(tokens: int, model: str) -> float:
    rate_per_1m = MODEL_COST_PER_1M_TOKENS_USD.get(model, 1.0)
    return round((tokens / 1_000_000) * rate_per_1m, 8)


def format_usd(value: float) -> str:
    return f"${value:.8f}"


def co2_to_equivalent(grams: float) -> str:
    if grams == 0:
        return "nothing — cache hit"
    if grams < 0.001:
        return "less than a breath of air"
    if grams < 0.01:
        return f"{grams * 1000:.1f}mg — a few keystrokes of energy"
    if grams < 0.1:
        return f"{grams * 30:.1f}m of phone scrolling"
    if grams < 1.0:
        return f"{grams * 0.5:.2f}s of laptop use"
    if grams < 10:
        return f"{grams / 10:.2f}g of coal equivalent"
    return f"{grams / 1000:.3f}kg CO2"

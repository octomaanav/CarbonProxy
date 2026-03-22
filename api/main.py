from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse

from engine import CarbonProxyEngine
from demo_seed import SEED_DATA


app = FastAPI(title="CarbonProxy API", version="0.2.0")
engine = CarbonProxyEngine()


class OptimizeRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = None
    output_format: Optional[str] = None
    max_words: Optional[int] = None
    bullet_count: Optional[int] = None
    baseline_model: Optional[str] = None
    history: Optional[list] = None
    static_context: Optional[str] = None
    use_cache: bool = True
    use_classifier: bool = True


class PromptRequest(BaseModel):
    prompt: str


class CacheStoreRequest(BaseModel):
    prompt: str
    response: str


@app.on_event("startup")
def startup_seed_cache() -> None:
    if SEED_DATA:
        engine.warm_cache(SEED_DATA)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "cache": engine.cache_stats(),
    }


@app.post("/api/optimize")
def optimize(body: OptimizeRequest) -> dict:
    try:
        result = engine.complete(
            prompt=body.prompt,
            task_type=body.task_type,
            output_format=body.output_format,
            max_words=body.max_words,
            bullet_count=body.bullet_count,
            baseline_model=body.baseline_model,
            history=body.history,
            static_context=body.static_context,
            use_cache=body.use_cache,
            use_classifier=body.use_classifier,
        )
    except Exception as err:
        return JSONResponse(
            status_code=500,
            content={
                "error": "engine_failed",
                "message": str(err),
                "original_prompt": body.prompt,
            },
        )

    return {
        "original_prompt": body.prompt,
        "optimized_prompt": result.get("compressed_prompt", body.prompt),
        "tokens_before": result.get("tokens_before", 0),
        "tokens_after": result.get("tokens_after", 0),
        "savings_pct": result.get("savings_pct", 0),
        "cache_hit": result.get("cache_hit", False),
        "cached_response": result.get("cached_response"),
        "response": result.get("response", ""),
        "co2_g": result.get("co2_g", 0.0),
        "carbon_saved_g": result.get("carbon_saved_g", 0.0),
        "money_saved_usd": result.get("money_saved_usd", 0.0),
        "money_saved_display": result.get("money_saved_display", "$0.00000000"),
        "baseline_model": result.get("baseline_model", "gpt-4o-mini"),
        "actual_cost_usd": result.get("actual_cost_usd", 0.0),
        "baseline_cost_usd": result.get("baseline_cost_usd", 0.0),
        "money_saved_vs_baseline_usd": result.get("money_saved_vs_baseline_usd", 0.0),
        "model": result.get("model", "unknown"),
        "provider": result.get("provider", "unknown"),
        "intent": result.get("intent", "default"),
        "route_reason": result.get("route_reason", ""),
        "similarity": result.get("similarity", 0.0),
    }


@app.post("/api/cache/store")
def cache_store(body: CacheStoreRequest) -> dict:
    engine.cache_store(body.prompt, body.response)
    return {"stored": True}


@app.post("/api/cache/check")
def cache_check(body: PromptRequest) -> dict:
    result = engine.cache_check(body.prompt)
    return {
        "hit": result.get("hit", False),
        "cached_response": result.get("response"),
        "similarity": result.get("similarity", 0.0),
        "matched_prompt": result.get("matched_prompt"),
    }


@app.get("/api/metrics")
def metrics() -> dict:
    return engine.metrics()


@app.post("/api/demo/reset")
def demo_reset() -> dict:
    engine.reset_all()
    return {"ok": True}

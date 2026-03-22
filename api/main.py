import sys
import os
import json
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse

from engine import CarbonProxyEngine
from demo_seed import SEED_DATA

from ecostack.memory_store import (
    init_db, get_conn, get_chunks, append_chunk,
    chunk_exists, delete_session, log_carbon, get_total_chunks,
)
from ecostack.embeddings import embed_query, embed_document
from ecostack.similarity import find_relevant_chunks
from ecostack.summarizer import summarize_exchange
from ecostack.carbon import estimate_carbon
from ecostack.models import (
    InjectRequest, InjectResponse,
    SaveRequest, SaveResponse,
    SessionStats, DashboardResponse, DashboardSummary,
    SessionRow, RecentChunk, CarbonSummary,
    DeleteResponse, HealthResponse,
)

# ── App ───────────────────────────────────────────────────────

app = FastAPI(title="CarbonProxy API", version="0.2.0")
engine = CarbonProxyEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Existing request models ──────────────────────────────────

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


# ── Startup ───────────────────────────────────────────────────

@app.on_event("startup")
def startup() -> None:
    init_db()
    if SEED_DATA:
        engine.warm_cache(SEED_DATA)


# ══════════════════════════════════════════════════════════════
# EXISTING ROUTES (engine / cache)
# ══════════════════════════════════════════════════════════════

@app.get("/api/health")
def api_health() -> dict:
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


# ══════════════════════════════════════════════════════════════
# UNIFIED CHAT — full pipeline with auto memory + model routing
# ══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str = "default"
    prompt: str


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    """Full EcoStack pipeline: inject memory → compress → route → call Gemini → save memory.

    Just send { "session_id": "...", "prompt": "..." } and everything is automatic.
    """
    original_prompt = body.prompt

    # ── Step 1: Inject relevant memory context ────────────────
    memory_info = {"chunks_used": 0, "chunks_available": 0,
                   "tokens_injected": 0, "tokens_saved": 0,
                   "relevant_summaries": [], "injected_context": ""}

    chunks = get_chunks(body.session_id)
    if chunks:
        query_emb = embed_query(body.prompt)
        if query_emb is not None:
            relevant = find_relevant_chunks(query_emb, chunks)
            injected_context = "\n".join(f"[Memory] {c['summary']}" for c in relevant)
            tokens_injected = sum(c["tokens"] for c in relevant)
            total_session_tokens = sum(c["tokens"] for c in chunks)

            memory_info = {
                "chunks_used": len(relevant),
                "chunks_available": len(chunks),
                "tokens_injected": tokens_injected,
                "tokens_saved": max(0, total_session_tokens - tokens_injected),
                "relevant_summaries": [c["summary"] for c in relevant],
                "injected_context": injected_context,
            }

    # Prepend memory context to the prompt if we have any
    enriched_prompt = body.prompt
    if memory_info["injected_context"]:
        enriched_prompt = memory_info["injected_context"] + "\n\n" + body.prompt

    # ── Step 2: Run through engine (compress → route → call) ──
    try:
        result = engine.complete(prompt=enriched_prompt)
    except Exception as err:
        return JSONResponse(
            status_code=500,
            content={
                "error": "engine_failed",
                "message": str(err),
                "original_prompt": original_prompt,
            },
        )

    response_text = result.get("response", "")
    model_used = result.get("model", "unknown")
    tokens_before = result.get("tokens_before", 0)
    tokens_after = result.get("tokens_after", 0)
    tokens_saved_by_compression = max(0, tokens_before - tokens_after)

    # ── Step 3: Save exchange to memory (non-blocking) ────────
    save_result = {"status": "skipped", "summary": "", "id": "", "tokens": 0}
    if response_text.strip():
        try:
            save_result = _save_background(
                session_id=body.session_id,
                prompt=original_prompt,
                response=response_text,
                model=model_used,
                tokens_sent=tokens_after,
                tokens_saved=tokens_saved_by_compression + memory_info["tokens_saved"],
            )
        except Exception as e:
            print(f"[chat] Memory save failed: {e}")

    return {
        # ── Response ──
        "response": response_text,
        "original_prompt": original_prompt,

        # ── Model routing ──
        "model": model_used,
        "provider": result.get("provider", "unknown"),
        "intent": result.get("intent", "default"),
        "route_reason": result.get("route_reason", ""),

        # ── Compression stats ──
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "savings_pct": result.get("savings_pct", 0),
        "compressed_prompt": result.get("compressed_prompt", enriched_prompt),

        # ── Memory layer stats ──
        "memory": {
            "chunks_used": memory_info["chunks_used"],
            "chunks_available": memory_info["chunks_available"],
            "tokens_injected": memory_info["tokens_injected"],
            "tokens_saved_by_memory": memory_info["tokens_saved"],
            "relevant_summaries": memory_info["relevant_summaries"],
            "saved_chunk": save_result,
        },

        # ── Carbon + cost ──
        "co2_g": result.get("co2_g", 0.0),
        "carbon_saved_g": result.get("carbon_saved_g", 0.0),
        "money_saved_usd": result.get("money_saved_usd", 0.0),
        "cache_hit": result.get("cache_hit", False),
    }



# MEMORY LAYER ROUTES
# ══════════════════════════════════════════════════════════════

@app.post("/memory/inject", response_model=InjectResponse)
def memory_inject(body: InjectRequest) -> InjectResponse:
    """Embed prompt, find relevant stored chunks, return injection context."""
    chunks = get_chunks(body.session_id)

    # No chunks yet — skip embedding (saves money)
    if not chunks:
        return InjectResponse(
            injected_context="",
            chunks_used=0,
            chunks_available=0,
            tokens_injected=0,
            tokens_saved=0,
            relevant_summaries=[],
        )

    query_emb = embed_query(body.prompt)
    if query_emb is None:
        # Embedding failed — return empty injection, don't crash
        return InjectResponse(
            injected_context="",
            chunks_used=0,
            chunks_available=len(chunks),
            tokens_injected=0,
            tokens_saved=0,
            relevant_summaries=[],
        )

    relevant = find_relevant_chunks(query_emb, chunks)

    injected_context = "\n".join(f"[Memory] {c['summary']}" for c in relevant)
    tokens_injected = sum(c["tokens"] for c in relevant)
    total_session_tokens = sum(c["tokens"] for c in chunks)
    tokens_saved = max(0, total_session_tokens - tokens_injected)

    return InjectResponse(
        injected_context=injected_context,
        chunks_used=len(relevant),
        chunks_available=len(chunks),
        tokens_injected=tokens_injected,
        tokens_saved=tokens_saved,
        relevant_summaries=[c["summary"] for c in relevant],
    )


def _save_background(
    session_id: str,
    prompt: str,
    response: str,
    model: str,
    tokens_sent: int,
    tokens_saved: int,
) -> dict:
    """Background task: summarize, embed, store chunk, log carbon."""
    summary = summarize_exchange(prompt, response)

    if chunk_exists(session_id, summary):
        return {
            "status": "duplicate_skipped",
            "summary": summary,
            "id": hashlib.md5(summary.encode()).hexdigest()[:8],
            "tokens": len(summary.split()),
        }

    embedding = embed_document(summary)
    if embedding is None:
        # Can't store without embedding — log and skip
        print(f"[memory/save] Embedding failed for session {session_id}, skipping")
        return {
            "status": "embedding_failed",
            "summary": summary,
            "id": "",
            "tokens": 0,
        }

    chunk_id = hashlib.md5(summary.encode()).hexdigest()[:8]
    token_count = len(summary.split())

    chunk = {
        "id": chunk_id,
        "summary": summary,
        "prompt": prompt,
        "response": response,
        "embedding": embedding,
        "tokens": token_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        append_chunk(session_id, chunk)
    except Exception as e:
        print(f"[memory/save] SQLite write failed: {e}")

    # Carbon logging
    try:
        co2_consumed, co2_avoided = estimate_carbon(model, tokens_sent, tokens_saved)
        log_carbon(
            session_id=session_id,
            model=model,
            tokens_sent=tokens_sent,
            tokens_saved=tokens_saved,
            co2_consumed=co2_consumed,
            co2_avoided=co2_avoided,
        )
    except Exception as e:
        print(f"[memory/save] Carbon log failed: {e}")

    return {
        "status": "saved",
        "summary": summary,
        "id": chunk_id,
        "tokens": token_count,
    }


@app.post("/memory/save", response_model=SaveResponse)
def memory_save(body: SaveRequest, background_tasks: BackgroundTasks) -> SaveResponse:
    """Summarize exchange, embed, store chunk + carbon log (non-blocking)."""
    # Run synchronously for now so we can return the result.
    # The Gemini calls are I/O-bound but short (~200ms).
    # For true fire-and-forget, swap to background_tasks.add_task().
    result = _save_background(
        session_id=body.session_id,
        prompt=body.prompt,
        response=body.response,
        model=body.model,
        tokens_sent=body.tokens_sent,
        tokens_saved=body.tokens_saved,
    )
    return SaveResponse(**result)


@app.get("/memory/stats/{session_id}", response_model=SessionStats)
def memory_stats(session_id: str) -> SessionStats:
    """Per-session stats for dashboard."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_chunks WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        ).fetchall()

    chunks = [dict(r) for r in rows]
    return SessionStats(
        session_id=session_id,
        total_chunks=len(chunks),
        total_tokens_stored=sum(c["tokens"] for c in chunks),
        recent_summaries=[c["summary"] for c in chunks[-5:]],
        oldest_chunk=chunks[0]["timestamp"] if chunks else None,
        newest_chunk=chunks[-1]["timestamp"] if chunks else None,
    )


@app.get("/memory/dashboard", response_model=DashboardResponse)
def memory_dashboard() -> DashboardResponse:
    """Aggregate stats across ALL sessions — polled every 5s by dashboard."""
    with get_conn() as conn:
        # Recent chunks
        all_chunks = conn.execute("""
            SELECT session_id, summary, tokens, timestamp
            FROM memory_chunks
            ORDER BY timestamp DESC
        """).fetchall()

        # Per-session stats
        sessions = conn.execute("""
            SELECT
                session_id,
                COUNT(*)         AS chunk_count,
                SUM(tokens)      AS tokens_stored,
                MIN(timestamp)   AS first_seen,
                MAX(timestamp)   AS last_seen
            FROM memory_chunks
            GROUP BY session_id
            ORDER BY last_seen DESC
        """).fetchall()

        # Totals
        totals = conn.execute("""
            SELECT COUNT(*) as total_chunks, COALESCE(SUM(tokens), 0) as total_tokens
            FROM memory_chunks
        """).fetchone()

        # Carbon totals from carbon_log
        carbon = conn.execute("""
            SELECT
                COALESCE(SUM(co2_consumed), 0) AS total_consumed,
                COALESCE(SUM(co2_avoided), 0)  AS total_avoided,
                COALESCE(SUM(tokens_saved), 0) AS total_tokens_saved
            FROM carbon_log
        """).fetchone()

    total_consumed = carbon["total_consumed"]
    total_avoided = carbon["total_avoided"]
    total_either = total_consumed + total_avoided
    savings_pct = round((total_avoided / total_either * 100) if total_either > 0 else 0.0, 2)

    return DashboardResponse(
        summary=DashboardSummary(
            total_sessions=len(sessions),
            total_chunks=totals["total_chunks"],
            tokens_saved=carbon["total_tokens_saved"],
            co2_avoided_g=round(total_avoided, 4),
        ),
        sessions=[
            SessionRow(
                session_id=s["session_id"],
                chunk_count=s["chunk_count"],
                tokens_stored=s["tokens_stored"],
                first_seen=s["first_seen"],
                last_seen=s["last_seen"],
            )
            for s in sessions
        ],
        recent_chunks=[
            RecentChunk(
                session_id=c["session_id"],
                summary=c["summary"],
                tokens=c["tokens"],
                timestamp=c["timestamp"],
            )
            for c in all_chunks[:20]
        ],
        carbon_summary=CarbonSummary(
            total_co2_consumed_g=round(total_consumed, 4),
            total_co2_avoided_g=round(total_avoided, 4),
            savings_pct=savings_pct,
        ),
    )


@app.delete("/memory/session/{session_id}", response_model=DeleteResponse)
def memory_delete_session(session_id: str) -> DeleteResponse:
    """Demo reset — wipe one session's memory."""
    deleted = delete_session(session_id)
    return DeleteResponse(deleted_chunks=deleted, session_id=session_id)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check for dashboard status indicator."""
    try:
        total = get_total_chunks()
        db_status = "connected"
    except Exception:
        total = 0
        db_status = "error"
    return HealthResponse(status="ok", db=db_status, chunks_total=total)
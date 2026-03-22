"""Pydantic request/response models for the EcoStack memory layer."""

from typing import Optional
from pydantic import BaseModel


# ── Request Models ────────────────────────────────────────────

class InjectRequest(BaseModel):
    session_id: str
    prompt: str


class SaveRequest(BaseModel):
    session_id: str
    prompt: str
    optimized_prompt: Optional[str] = None
    response: str
    model: str
    tokens_sent: int
    tokens_saved: int


# ── Response Models ───────────────────────────────────────────

class InjectResponse(BaseModel):
    injected_context: str
    chunks_used: int
    chunks_available: int
    tokens_injected: int
    tokens_saved: int
    relevant_summaries: list[str]


class SaveResponse(BaseModel):
    status: str
    summary: str
    id: str
    tokens: int


class SessionStats(BaseModel):
    session_id: str
    total_chunks: int
    total_tokens_stored: int
    total_requests: int = 0
    total_tokens_before: int = 0
    total_tokens_after: int = 0
    total_tokens_saved: int = 0
    total_co2_avoided_g: float = 0.0
    recent_summaries: list[str]
    recent_original_prompts: list[str] = []
    recent_optimized_prompts: list[str] = []
    oldest_chunk: Optional[str]
    newest_chunk: Optional[str]


class DashboardSummary(BaseModel):
    total_sessions: int
    total_chunks: int
    tokens_saved: int
    co2_avoided_g: float


class SessionRow(BaseModel):
    session_id: str
    chunk_count: int
    tokens_stored: int
    requests: int = 0
    tokens_saved: int = 0
    co2_avoided_g: float = 0.0
    first_seen: str
    last_seen: str
    last_original_prompt: str = ""
    last_optimized_prompt: str = ""


class RecentChunk(BaseModel):
    session_id: str
    summary: str
    original_prompt: str = ""
    optimized_prompt: str = ""
    response: str = ""
    tokens: int
    timestamp: str


class CarbonSummary(BaseModel):
    total_co2_consumed_g: float
    total_co2_avoided_g: float
    savings_pct: float


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    sessions: list[SessionRow]
    recent_chunks: list[RecentChunk]
    carbon_summary: CarbonSummary


class DeleteResponse(BaseModel):
    deleted_chunks: int
    session_id: str


class HealthResponse(BaseModel):
    status: str
    db: str
    chunks_total: int

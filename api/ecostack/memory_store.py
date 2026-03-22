"""SQLite CRUD for memory_chunks and carbon_log tables."""

import json
import hashlib
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "ecostack_memory.db")


def get_conn() -> sqlite3.Connection:
    """Return a new SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes (idempotent — safe on every restart)."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_chunks (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL,
                summary     TEXT NOT NULL,
                prompt      TEXT NOT NULL DEFAULT '',
                optimized_prompt TEXT NOT NULL DEFAULT '',
                response    TEXT NOT NULL DEFAULT '',
                embedding   TEXT NOT NULL,
                tokens      INTEGER NOT NULL,
                timestamp   TEXT NOT NULL
            )
        """)
        _ensure_column(conn, "memory_chunks", "optimized_prompt", "TEXT NOT NULL DEFAULT ''")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON memory_chunks (session_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS carbon_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL,
                model         TEXT NOT NULL,
                tokens_sent   INTEGER NOT NULL,
                tokens_saved  INTEGER NOT NULL,
                co2_consumed  REAL NOT NULL,
                co2_avoided   REAL NOT NULL,
                timestamp     TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS request_log (
                id                           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id                   TEXT NOT NULL,
                original_prompt              TEXT NOT NULL,
                optimized_prompt             TEXT NOT NULL,
                response                     TEXT NOT NULL DEFAULT '',
                model                        TEXT NOT NULL,
                provider                     TEXT NOT NULL DEFAULT 'unknown',
                intent                       TEXT NOT NULL DEFAULT 'default',
                route_reason                 TEXT NOT NULL DEFAULT '',
                tokens_before                INTEGER NOT NULL DEFAULT 0,
                tokens_after                 INTEGER NOT NULL DEFAULT 0,
                tokens_saved_compression     INTEGER NOT NULL DEFAULT 0,
                tokens_saved_memory          INTEGER NOT NULL DEFAULT 0,
                cache_hit                    INTEGER NOT NULL DEFAULT 0,
                co2_consumed                 REAL NOT NULL DEFAULT 0,
                co2_avoided                  REAL NOT NULL DEFAULT 0,
                timestamp                    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_log_session
            ON request_log (session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_log_time
            ON request_log (timestamp DESC)
        """)
        # Backfill old rows from earlier builds where cache requests were logged with non-zero CO2.
        conn.execute("""
            UPDATE request_log
            SET co2_consumed = 0,
                co2_avoided = 0
            WHERE model = 'cache'
        """)
        conn.execute("""
            UPDATE carbon_log
            SET co2_consumed = 0,
                co2_avoided = 0
            WHERE model = 'cache'
        """)
        conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Add a missing column to an existing table (migration-safe)."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row["name"] for row in rows}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def get_chunks(session_id: str) -> list[dict]:
    """Load all chunks for a session with embeddings parsed from JSON."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_chunks WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        ).fetchall()
    return [
        {
            "id":        row["id"],
            "summary":   row["summary"],
            "prompt":    row["prompt"],
            "optimized_prompt": row["optimized_prompt"],
            "response":  row["response"],
            "embedding": json.loads(row["embedding"]),
            "tokens":    row["tokens"],
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


def chunk_exists(session_id: str, summary: str) -> bool:
    """Check if a chunk with the same md5-based id already exists for this session."""
    chunk_id = hashlib.md5(summary.encode()).hexdigest()[:8]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM memory_chunks WHERE id = ? AND session_id = ?",
            (chunk_id, session_id)
        ).fetchone()
    return row is not None


def append_chunk(session_id: str, chunk: dict) -> None:
    """Insert a memory chunk. Uses INSERT OR IGNORE for deduplication."""
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO memory_chunks
               (id, session_id, summary, prompt, optimized_prompt, response, embedding, tokens, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chunk["id"],
                session_id,
                chunk["summary"],
                chunk.get("prompt", ""),
                chunk.get("optimized_prompt", ""),
                chunk.get("response", ""),
                json.dumps(chunk["embedding"]),
                chunk["tokens"],
                chunk["timestamp"],
            )
        )
        conn.commit()


def log_request(
    session_id: str,
    original_prompt: str,
    optimized_prompt: str,
    response: str,
    model: str,
    provider: str,
    intent: str,
    route_reason: str,
    tokens_before: int,
    tokens_after: int,
    tokens_saved_compression: int,
    tokens_saved_memory: int,
    cache_hit: bool,
    co2_consumed: float,
    co2_avoided: float,
) -> None:
    """Insert one request-level analytics row used by /api/metrics and dashboard."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO request_log
               (session_id, original_prompt, optimized_prompt, response, model,
                provider, intent, route_reason, tokens_before, tokens_after,
                tokens_saved_compression, tokens_saved_memory, cache_hit,
                co2_consumed, co2_avoided, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                original_prompt,
                optimized_prompt,
                response,
                model,
                provider,
                intent,
                route_reason,
                tokens_before,
                tokens_after,
                tokens_saved_compression,
                tokens_saved_memory,
                int(cache_hit),
                co2_consumed,
                co2_avoided,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()


def log_carbon(
    session_id: str,
    model: str,
    tokens_sent: int,
    tokens_saved: int,
    co2_consumed: float,
    co2_avoided: float,
) -> None:
    """Insert a carbon log entry."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO carbon_log
               (session_id, model, tokens_sent, tokens_saved,
                co2_consumed, co2_avoided, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                model,
                tokens_sent,
                tokens_saved,
                co2_consumed,
                co2_avoided,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()


def delete_session(session_id: str) -> int:
    """Delete all memory chunks for a session. Returns deleted row count."""
    with get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM memory_chunks WHERE session_id = ?",
            (session_id,)
        )
        conn.commit()
        return cursor.rowcount


def get_total_chunks() -> int:
    """Count of all memory chunks across all sessions."""
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM memory_chunks").fetchone()
    return row["cnt"] if row else 0
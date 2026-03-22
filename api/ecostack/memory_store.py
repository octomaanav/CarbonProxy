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
                embedding   TEXT NOT NULL,
                tokens      INTEGER NOT NULL,
                timestamp   TEXT NOT NULL
            )
        """)
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
        conn.commit()


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
               (id, session_id, summary, embedding, tokens, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                chunk["id"],
                session_id,
                chunk["summary"],
                json.dumps(chunk["embedding"]),
                chunk["tokens"],
                chunk["timestamp"],
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
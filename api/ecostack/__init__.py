"""EcoStack memory layer package."""

from .memory_store import init_db, get_conn, get_chunks, append_chunk
from .memory_store import chunk_exists, delete_session, log_carbon, get_total_chunks
from .embeddings import embed_query, embed_document
from .similarity import cosine_sim, find_relevant_chunks
from .summarizer import summarize_exchange
from .carbon import estimate_carbon, MODEL_CO2_RATES

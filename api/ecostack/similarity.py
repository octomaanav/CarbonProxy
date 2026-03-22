"""Cosine similarity and chunk ranking for the EcoStack memory layer."""

import numpy as np

SIMILARITY_THRESHOLD = 0.75
TOP_K = 3


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def find_relevant_chunks(
    query_embedding: list[float],
    chunks: list[dict],
) -> list[dict]:
    """Score chunks by cosine similarity, filter by threshold, return top-k.

    Each returned chunk dict gets an added 'score' key.
    """
    scored: list[tuple[float, dict]] = []
    for chunk in chunks:
        score = cosine_sim(query_embedding, chunk["embedding"])
        if score >= SIMILARITY_THRESHOLD:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:TOP_K]:
        chunk_copy = dict(chunk)
        chunk_copy["score"] = round(score, 4)
        results.append(chunk_copy)
    return results

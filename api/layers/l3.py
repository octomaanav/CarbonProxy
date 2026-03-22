import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CACHE_SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL,
    L3_CANONICAL_REPLACEMENTS,
    L3_CONCEPT_GROUPS,
    L3_LOW_OVERLAP_CUTOFF,
    L3_LOW_OVERLAP_SIMILARITY_CAP,
)

print(f"Loading embedding model {EMBEDDING_MODEL}...")
_emb_model = SentenceTransformer(EMBEDDING_MODEL)
print("Embedding model ready.")

_chroma = chromadb.Client()
_collection = _chroma.get_or_create_collection(
    name="prompt_cache",
    metadata={"hnsw:space": "cosine"},
)


def _canonical(text: str) -> str:
    t = text.lower()
    for src, dest in L3_CANONICAL_REPLACEMENTS.items():
        t = t.replace(src, dest)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _tokens(text: str) -> set[str]:
    return {tok for tok in _canonical(text).split() if len(tok) > 1}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _embed(text: str) -> list:
    return _emb_model.encode([text]).tolist()


def check(prompt: str, threshold: float = CACHE_SIMILARITY_THRESHOLD) -> dict:
    if _collection.count() == 0:
        return {"hit": False, "response": None, "similarity": 0.0, "matched_prompt": None}

    results = _collection.query(
        query_embeddings=_embed(prompt),
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    if not results.get("documents") or not results["documents"][0]:
        return {"hit": False, "response": None, "similarity": 0.0, "matched_prompt": None}

    matched_prompt = results["documents"][0][0]
    if _canonical(prompt) == _canonical(matched_prompt):
        similarity = 1.0
    else:
        distance = results["distances"][0][0]
        similarity = round(max(0.0, min(1.0, 1 - (distance / 2))), 4)

        prompt_tokens = _tokens(prompt)
        matched_tokens = _tokens(matched_prompt)
        overlap = _jaccard(prompt_tokens, matched_tokens)

        for concept_group in L3_CONCEPT_GROUPS:
            if concept_group.issubset(prompt_tokens) and concept_group.issubset(matched_tokens):
                similarity = max(similarity, 0.9)

        if overlap < L3_LOW_OVERLAP_CUTOFF and similarity < 0.8:
            similarity = min(similarity, L3_LOW_OVERLAP_SIMILARITY_CAP)

    similarity = round(similarity, 4)

    if similarity >= threshold:
        return {
            "hit": True,
            "response": results["metadatas"][0][0].get("response", ""),
            "similarity": similarity,
            "matched_prompt": matched_prompt,
        }

    return {"hit": False, "response": None, "similarity": similarity, "matched_prompt": None}


def store(prompt: str, response: str) -> None:
    next_id = str(_collection.count())
    _collection.add(
        embeddings=_embed(prompt),
        documents=[prompt],
        metadatas=[{"response": response}],
        ids=[next_id],
    )


def warm(prompts_and_responses: list) -> None:
    for prompt, response in prompts_and_responses:
        store(prompt, response)
    print(f"Cache warmed: {len(prompts_and_responses)} entries.")


def stats() -> dict:
    return {
        "total_entries": _collection.count(),
        "embedding_model": EMBEDDING_MODEL,
        "threshold": CACHE_SIMILARITY_THRESHOLD,
    }


def clear() -> None:
    global _collection
    try:
        _chroma.delete_collection("prompt_cache")
    except Exception:
        pass
    _collection = _chroma.get_or_create_collection(
        name="prompt_cache",
        metadata={"hnsw:space": "cosine"},
    )

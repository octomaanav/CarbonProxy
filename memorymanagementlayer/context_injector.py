# context_injector.py
import numpy as np
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')

# genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_embedding(text):
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]

def select_relevant_chunks(current_prompt, chunks, top_k=3, threshold=0.75):
    if not chunks:
        return []
    prompt_emb = get_embedding(current_prompt)
    scored = []
    for chunk in chunks:
        chunk_emb = get_embedding(chunk["content"])
        sim = np.dot(prompt_emb, chunk_emb) / (
            np.linalg.norm(prompt_emb) * np.linalg.norm(chunk_emb)
        )
        if sim > threshold:
            scored.append((sim, chunk))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [c for _, c in scored[:top_k]]

def build_injected_prompt(original_prompt, relevant_chunks):
    if not relevant_chunks:
        return original_prompt, 0
    context_block = "\n".join(
        f"[Memory] {c['content']}" for c in relevant_chunks
    )
    injected = f"{context_block}\n\n{original_prompt}"
    saved = sum(c["tokens"] for c in relevant_chunks)  # vs sending all
    return injected, saved


# memory/
# ├── main.py              # your FastAPI app with all 3 routes
# ├── memory_store.py      # load_store, write_store, get_chunks, append_chunk
# ├── embeddings.py        # embed_query, embed_document
# ├── similarity.py        # cosine_sim, find_relevant_chunks
# ├── summarizer.py        # summarize()
# └── memory_store.json    # created automatically on first save
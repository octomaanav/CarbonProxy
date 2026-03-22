import json, os, hashlib
from datetime import datetime

MEMORY_FILE = "memory_store.json"

def load_store():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {}

def save_chunk(session_id: str, content: str, metadata: dict = {}):
    store = load_store()
    store.setdefault(session_id, []).append({
        "id": hashlib.md5(content.encode()).hexdigest()[:8],
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "tokens": len(content.split()),  # rough estimate
        **metadata
    })
    with open(MEMORY_FILE, "w") as f:
        json.dump(store, f)

def get_chunks(session_id: str):
    return load_store().get(session_id, [])
"""Seed the in-memory state with ~15 realistic demo requests so the dashboard
has rich data on first load.  Imported and executed by start.sh via
`python demo_seed.py` before the server starts."""

from __future__ import annotations
import time, random
from main import (
    state, CacheRecord, HistoryEntry,
    estimate_tokens, estimate_co2, estimate_kwh, estimate_cost_usd,
    compress_prompt, choose_model,
)

# --- Cache seed entries ---------------------------------------------------
cache_seed = [
    (
        "explain the difference between REST and GraphQL APIs",
        "REST uses multiple endpoints and fixed resource shapes. "
        "GraphQL uses a single endpoint and client-defined queries, "
        "reducing over/under-fetching.",
    ),
    (
        "explain async await in javascript",
        "`async`/`await` lets you write asynchronous code in a synchronous "
        "style on top of Promises.",
    ),
    (
        "how does JWT authentication work",
        "JWT (JSON Web Token) encodes claims into a signed token. The server "
        "creates a token on login, the client stores it, and sends it with "
        "each request in the Authorization header.",
    ),
]

for prompt, response in cache_seed:
    state.cache.append(CacheRecord(prompt=prompt, response=response))

# --- Simulated request history --------------------------------------------
demo_prompts = [
    "explain how TCP three-way handshake works in detail",
    "what is the difference between SQL and NoSQL databases",
    "explain async await in javascript",              # cache hit
    "write a Python function to merge two sorted lists",
    "how does garbage collection work in Java",
    "explain the difference between REST and GraphQL APIs",  # cache hit
    "what are the SOLID principles in object oriented design",
    "how to implement rate limiting in a FastAPI application",
    "explain how container orchestration works with Kubernetes",
    "what is the CAP theorem and why does it matter",
    "how does JWT authentication work",                 # cache hit
    "explain event-driven architecture with message queues",
    "write a React hook for debounced search input",
    "how to set up CI/CD pipeline with GitHub Actions",
    "explain the difference between concurrency and parallelism",
]

now = time.time()
random.seed(42)

for i, prompt in enumerate(demo_prompts):
    ts = now - (len(demo_prompts) - i) * 45 + random.uniform(-5, 5)

    # Check if it's a cache hit
    is_cache_hit = False
    for cr in state.cache:
        from difflib import SequenceMatcher
        score = SequenceMatcher(None, prompt.lower(), cr.prompt.lower()).ratio()
        if score >= 0.92:
            is_cache_hit = True
            break

    tokens_in = estimate_tokens(prompt)

    if is_cache_hit:
        state.requests += 1
        state.cache_hits += 1
        state.total_tokens_in += tokens_in
        entry = HistoryEntry(
            model="cache",
            co2_g=0.0,
            cached=True,
            timestamp=ts,
            tokens_in=tokens_in,
            tokens_out=0,
            cost_usd=0.0,
            kwh=0.0,
            prompt_preview=prompt[:60],
        )
        state.history.append(entry)
    else:
        optimized = compress_prompt(prompt)
        tokens_after = estimate_tokens(optimized)
        model = choose_model(tokens_after)
        tokens_out = random.randint(18, 40)  # simulate model response tokens
        co2 = estimate_co2(tokens_after, tokens_out, model)
        kwh = estimate_kwh(tokens_after, tokens_out, model)
        cost = estimate_cost_usd(tokens_after, tokens_out, model)

        state.requests += 1
        state.tokens_saved += max(0, tokens_in - tokens_after)
        state.co2_saved_g = round(state.co2_saved_g + co2, 6)
        state.total_tokens_in += tokens_after
        state.total_tokens_out += tokens_out
        state.total_cost_usd = round(state.total_cost_usd + cost, 8)
        state.total_kwh = round(state.total_kwh + kwh, 10)

        entry = HistoryEntry(
            model=model,
            co2_g=co2,
            cached=False,
            timestamp=ts,
            tokens_in=tokens_after,
            tokens_out=tokens_out,
            cost_usd=cost,
            kwh=kwh,
            prompt_preview=prompt[:60],
        )
        state.history.append(entry)

print(f"Seeded {len(cache_seed)} cache items + {len(demo_prompts)} demo requests")
print(f"  → {state.requests} total requests, {state.cache_hits} cache hits")
print(f"  → {state.co2_saved_g}g CO₂, {state.tokens_saved} tokens saved")

"""Generates realistic demo requests so the dashboard has rich data on first load."""

from __future__ import annotations
import time, random
from dataclasses import dataclass
from typing import List

# These are imported dynamically inside the function to avoid circular imports
def seed_data(state) -> None:
    from main import (
        CacheRecord, HistoryEntry,
        estimate_tokens, estimate_co2, estimate_kwh, estimate_cost_usd,
        compress_prompt, choose_model,
    )

    if state.requests > 0:
        return  # Already seeded

    # --- Cache seed entries ---
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
        (
            "what is a decorator in python",
            "A decorator is a function that takes another function and extends "
            "its behavior without explicitly modifying it.",
        ),
        (
            "how to center a div in css",
            "Use flexbox: `display: flex; justify-content: center; align-items: center;` "
            "or grid: `display: grid; place-items: center;`.",
        ),
    ]

    for prompt, response in cache_seed:
        state.cache.append(CacheRecord(prompt=prompt, response=response))

    # --- Simulated request history ---
    base_prompts = [
        "explain how TCP three-way handshake works in detail",
        "what is the difference between SQL and NoSQL databases",
        "explain async await in javascript",
        "write a Python function to merge two sorted lists",
        "how does garbage collection work in Java",
        "explain the difference between REST and GraphQL APIs",
        "what are the SOLID principles in object oriented design",
        "how to implement rate limiting in a FastAPI application",
        "explain how container orchestration works with Kubernetes",
        "what is the CAP theorem and why does it matter",
        "how does JWT authentication work",
        "explain event-driven architecture with message queues",
        "write a React hook for debounced search input",
        "how to set up CI/CD pipeline with GitHub Actions",
        "explain the difference between concurrency and parallelism",
        "what is a decorator in python",
        "how to center a div in css",
        "write a sql query to find the second highest salary",
        "explain the virtual dom in react",
        "what is the difference between let, const, and var",
    ]

    # Generate ~60 requests to fill the charts nicely
    demo_prompts = []
    random.seed(42)
    for _ in range(60):
        # 30% chance to repeat a prompt for a cache hit
        if random.random() < 0.3:
            demo_prompts.append(random.choice([p for p, _ in cache_seed]))
        else:
            demo_prompts.append(random.choice(base_prompts) + " " + str(random.randint(1, 100)))

    now = time.time()
    
    for i, prompt in enumerate(demo_prompts):
        # Spread over the last 2 hours
        ts = now - (len(demo_prompts) - i) * 120 + random.uniform(-10, 10)

        # Check if it's a cache hit
        is_cache_hit = False
        from difflib import SequenceMatcher
        for cr in state.cache:
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
            
            # Add some randomness to tokens_after to make the "Tokens Saved" metric non-zero
            tokens_after = max(1, min(tokens_in, int(tokens_after * random.uniform(0.5, 0.9))))
            
            model = choose_model(tokens_after)
            # Add some randomness to model selection for a colorful pie chart
            if random.random() < 0.2:
                model = random.choice(["gpt-4", "claude-opus-3", "gpt-4o-mini"])

            tokens_out = random.randint(20, 150)  # simulate model response tokens
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
    print(f"  → {state.co2_saved_g:.4f}g CO₂, {state.tokens_saved} tokens saved")


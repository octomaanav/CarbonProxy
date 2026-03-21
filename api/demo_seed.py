from main import state, CacheRecord

seed = [
    (
        "explain the difference between REST and GraphQL APIs",
        "REST uses multiple endpoints and fixed resource shapes. GraphQL uses a single endpoint and client-defined queries, reducing over/under-fetching.",
    ),
    (
        "explain async await in javascript",
        "`async`/`await` lets you write asynchronous code in a synchronous style on top of Promises.",
    ),
]

for prompt, response in seed:
    state.cache.append(CacheRecord(prompt=prompt, response=response))

print(f"Seeded {len(seed)} cache items")

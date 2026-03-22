SEED_DATA = [
    (
        "explain the difference between REST and GraphQL APIs",
        "REST uses multiple endpoints and fixed resource shapes. GraphQL uses a single endpoint and client-defined queries, reducing over/under-fetching.",
    ),
    (
        "explain async await in javascript",
        "`async`/`await` lets you write asynchronous code in a synchronous style on top of Promises.",
    ),
]


def seed_engine(engine) -> None:
    if SEED_DATA:
        engine.warm_cache(SEED_DATA)


if __name__ == "__main__":
    from engine import CarbonProxyEngine

    seed_engine(CarbonProxyEngine())
    print(f"Seeded {len(SEED_DATA)} cache items")

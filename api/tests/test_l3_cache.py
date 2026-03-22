from layers.l3 import clear, store, check


def test_3a_store_then_exact_match():
    clear()
    store(
        "explain REST vs GraphQL",
        "REST uses fixed endpoints. GraphQL uses a single flexible endpoint.",
    )

    result = check("explain REST vs GraphQL")

    assert result["hit"] is True
    assert result["similarity"] >= 0.999
    assert "REST uses fixed endpoints" in (result["response"] or "")


def test_3b_paraphrase_match():
    clear()
    store(
        "explain REST vs GraphQL",
        "REST uses fixed endpoints. GraphQL uses a single flexible endpoint.",
    )
    store(
        "how does machine learning work",
        "ML trains models on data to make predictions without explicit rules.",
    )
    store(
        "explain async await JavaScript",
        "async/await is syntactic sugar over Promises. await pauses until resolved.",
    )

    tests = [
        ("what is the difference between REST and GraphQL APIs", 0.92),
        ("what is the difference between REST and GraphQL?", 0.92),
    ]

    for prompt, threshold in tests:
        result = check(prompt, threshold=threshold)
        assert result["hit"] is True
        assert result["similarity"] >= threshold


def test_3c_cold_cache_miss():
    clear()
    result = check("explain quantum computing")

    assert result["hit"] is False
    assert result["similarity"] == 0.0


def test_3d_unrelated_prompt_no_hit():
    clear()
    store(
        "explain REST vs GraphQL",
        "REST uses fixed endpoints. GraphQL uses a single endpoint.",
    )

    result = check("what is the boiling point of water")

    assert result["hit"] is False
    assert result["similarity"] < 0.5

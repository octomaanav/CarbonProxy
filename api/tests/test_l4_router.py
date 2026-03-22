from layers.l4 import route
from config import MODEL_FLASH, MODEL_PRO


def test_routing_matrix():
    tests = [
        ("What is 2+2?", MODEL_FLASH, "simple_qa"),
        ("Write a Python function to reverse a string", MODEL_FLASH, "code_gen"),
        ("Review this code for bugs: def add(a,b): return a+b", MODEL_FLASH, "code_review"),
        ("Analyze the tradeoffs between microservices and monolith", MODEL_FLASH, "analysis"),
        ("Explain how TCP/IP works to a beginner", MODEL_FLASH, "explain"),
        (
            "Design a globally distributed database architecture with CAP theorem tradeoffs",
            MODEL_PRO,
            "architecture",
        ),
    ]

    for prompt, expected_model, expected_intent in tests:
        result = route(prompt)
        assert result["model"] == expected_model
        assert result["intent"] == expected_intent
        assert result["provider"] in {"google", "openai", "anthropic", "meta"}


def test_explicit_task_type_override():
    result = route("Design a global distributed system", task_type="simple_qa")
    assert result["model"] == MODEL_FLASH
    assert "explicit override" in result["reason"]

    result2 = route("What is 2+2?", task_type="architecture")
    assert result2["model"] == MODEL_PRO
    assert "explicit override" in result2["reason"]


def test_classifier_disabled_token_fallback():
    short = "explain REST"
    long_prompt = " ".join(["analyze the architectural tradeoffs"] * 200)

    r1 = route(short, use_classifier=False)
    r2 = route(long_prompt, use_classifier=False)

    assert r1["model"] == MODEL_FLASH
    assert r2["model"] == MODEL_PRO
    assert r1["provider"] == "google"
    assert r2["provider"] == "google"
    assert r1["reason"].startswith("token count:")
    assert r2["reason"].startswith("token count:")


def test_provider_fallback_when_google_unavailable(monkeypatch):
    monkeypatch.setattr("layers.l4._provider_available", lambda provider: provider == "openai")

    result = route("What is 2+2?", task_type="simple_qa")

    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini"

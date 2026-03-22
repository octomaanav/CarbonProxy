from layers.l1 import compress, rule_based_compress


def test_rule_based_removes_filler_lines():
    prompt = """You are a helpful assistant.
Please help me understand Docker.
Make sure to cover installation and basic commands.
Thank you."""

    result = rule_based_compress(prompt)
    lowered = result.lower()

    assert "you are" not in lowered
    assert "please help" not in lowered
    assert "make sure" not in lowered
    assert "thank you" not in lowered
    assert "docker" in lowered
    assert "installation and basic commands" in lowered
    assert result.strip() == "understand Docker.\ncover installation and basic commands."


def test_rule_based_strips_multiple_prefixes_in_one_line():
    prompt = "You are an experienced assistant, kindly please help me implement retries in Python requests."
    result = rule_based_compress(prompt)

    lowered = result.lower()
    assert "you are" not in lowered
    assert "kindly" not in lowered
    assert "please help me" not in lowered
    assert "implement retries" in lowered


def test_short_prompt_skips_llm(monkeypatch):
    called = {"value": False}

    def fake_call(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("LLM should not be called for short prompts")

    monkeypatch.setattr("layers.l1.call", fake_call)

    prompt = "Sum even numbers in a list. Python. Error handling."
    result = compress(prompt)

    assert result["tokens_before"] < 60
    assert 0 <= result["savings_pct"] <= 10
    assert result["compressed"] == prompt
    assert called["value"] is False


def test_verbose_prompt_uses_llm_when_available(monkeypatch):
    def fake_call(**_kwargs):
        return "Explain REST vs GraphQL with history, differences, use cases, pros/cons, and recommendation."

    monkeypatch.setattr("layers.l1.call", fake_call)

    prompt = (
        "You are a senior software engineer with 10 years of experience in distributed systems. "
        "I need you to help me understand the difference between REST APIs and GraphQL. "
        "Please provide a comprehensive explanation covering the history, technical differences, "
        "use cases, advantages and disadvantages of each approach, and when you would recommend "
        "using one versus the other in a modern web application architecture."
    )

    result = compress(prompt)

    assert result["tokens_before"] > 60
    assert result["tokens_after"] < result["tokens_before"]
    assert result["savings_pct"] > 0

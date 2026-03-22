from layers.l5 import (
    estimate_history_tokens,
    rolling_window,
    summarize_history,
    enforce_token_budget,
)


def test_5a_rolling_window_keeps_last_n():
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"}
        for i in range(30)
    ]

    result = rolling_window(history, max_turns=10)

    assert len(result) == 10
    assert result[-1]["content"] == "message 29"


def test_rolling_window_preserves_system_message():
    history = [{"role": "system", "content": "policy"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
        for i in range(20)
    ]

    result = rolling_window(history, max_turns=10)

    assert result[0]["role"] == "system"
    assert result[0]["content"] == "policy"
    assert len(result) == 11


def test_5b_token_budget_enforcement():
    long_msg = "word " * 500
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": long_msg}
        for i in range(20)
    ]

    before = estimate_history_tokens(history)
    result = enforce_token_budget(history, max_tokens=4000)
    after = estimate_history_tokens(result)

    assert before > 4000
    assert after <= 4000
    assert len(result) < len(history)


def test_enforce_budget_keeps_system_messages():
    long_msg = "word " * 800
    history = [{"role": "system", "content": "global policy"}] + [
        {"role": "user", "content": long_msg},
        {"role": "assistant", "content": long_msg},
    ]

    result = enforce_token_budget(history, max_tokens=1000)

    assert any(m["role"] == "system" for m in result)


def test_summarize_history_skips_when_short(monkeypatch):
    called = {"value": False}

    def fake_call(**_kwargs):
        called["value"] = True
        return "summary"

    monkeypatch.setattr("layers.l5.call", fake_call)

    messages = [{"role": "user", "content": "small history"}]
    result = summarize_history(messages)

    assert result == messages
    assert called["value"] is False


def test_summarize_history_compresses_when_long(monkeypatch):
    def fake_call(**_kwargs):
        return "- kept decisions\n- kept facts"

    monkeypatch.setattr("layers.l5.call", fake_call)

    long_piece = "word " * 350
    messages = [
        {"role": "system", "content": "policy"}
    ] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn-{i} {long_piece}"}
        for i in range(12)
    ]

    result = summarize_history(messages, keep_last=6)

    assert result[0]["role"] == "system"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"].startswith("[Summary of prior conversation]")
    assert len(result) == 8

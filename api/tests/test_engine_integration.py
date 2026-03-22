from engine import CarbonProxyEngine
import engine as engine_module


def test_engine_applies_l5_pipeline_when_history_present(monkeypatch):
    monkeypatch.setattr(engine_module.l3, "check", lambda _prompt: {"hit": False})
    monkeypatch.setattr(
        engine_module.l4,
        "route",
        lambda **_kwargs: {
            "model": "gemini-2.5-flash",
            "provider": "google",
            "intent": "analysis",
            "reason": "test route",
        },
    )
    monkeypatch.setattr(
        engine_module.l1,
        "compress",
        lambda _prompt, use_llm=False: {
            "compressed": "COMPRESSED",
            "savings_pct": 42,
            "tokens_before": 10,
            "tokens_after": 6,
        },
    )
    monkeypatch.setattr(engine_module.l6, "build_structured_prompt", lambda *_args, **_kwargs: "FINAL_PROMPT")
    monkeypatch.setattr(engine_module.l2, "get_system_with_context", lambda *_args, **_kwargs: "SYS")
    monkeypatch.setattr(engine_module.l6, "get_max_tokens", lambda _intent: 333)

    calls = []

    def fake_rolling(messages):
        calls.append("rolling")
        assert messages == [{"role": "user", "content": "old user"}]
        return [{"role": "system", "content": "policy"}, {"role": "assistant", "content": "rolled"}]

    def fake_summarize(messages):
        calls.append("summarize")
        assert messages[-1]["content"] == "rolled"
        return messages + [{"role": "assistant", "content": "summary"}]

    def fake_enforce(messages):
        calls.append("enforce")
        assert messages[-1]["content"] == "summary"
        return [{"role": "system", "content": "budget-ok"}]

    monkeypatch.setattr(engine_module.l5, "rolling_window", fake_rolling)
    monkeypatch.setattr(engine_module.l5, "summarize_history", fake_summarize)
    monkeypatch.setattr(engine_module.l5, "enforce_token_budget", fake_enforce)

    history_capture = {}

    def fake_call_with_history(**kwargs):
        history_capture.update(kwargs)
        return "LLM_RESPONSE"

    monkeypatch.setattr(engine_module, "call_with_history", fake_call_with_history)
    monkeypatch.setattr(engine_module, "call", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("call() should not be used")))

    stored = {}
    monkeypatch.setattr(engine_module.l3, "store", lambda prompt, response: stored.update({"prompt": prompt, "response": response}))

    engine = CarbonProxyEngine()
    result = engine.complete(
        prompt="Original user prompt",
        history=[{"role": "user", "content": "old user"}],
        use_cache=True,
    )

    assert calls == ["rolling", "summarize", "enforce"]
    assert history_capture["messages"] == [
        {"role": "system", "content": "budget-ok"},
        {"role": "user", "content": "FINAL_PROMPT"},
    ]
    assert history_capture["model"] == "gemini-2.5-flash"
    assert history_capture["system"] == "SYS"
    assert history_capture["max_tokens"] == 333

    assert result["response"] == "LLM_RESPONSE"
    assert result["provider"] == "google"
    assert result["intent"] == "analysis"
    assert stored == {"prompt": "Original user prompt", "response": "LLM_RESPONSE"}


def test_engine_skips_l5_when_no_history(monkeypatch):
    monkeypatch.setattr(engine_module.l3, "check", lambda _prompt: {"hit": False})
    monkeypatch.setattr(
        engine_module.l4,
        "route",
        lambda **_kwargs: {
            "model": "gemini-2.5-flash",
            "provider": "google",
            "intent": "simple_qa",
            "reason": "test route",
        },
    )
    monkeypatch.setattr(
        engine_module.l1,
        "compress",
        lambda _prompt, use_llm=False: {
            "compressed": "COMPRESSED",
            "savings_pct": 10,
            "tokens_before": 10,
            "tokens_after": 9,
        },
    )
    monkeypatch.setattr(engine_module.l6, "build_structured_prompt", lambda *_args, **_kwargs: "FINAL_PROMPT")
    monkeypatch.setattr(engine_module.l2, "get_system_with_context", lambda *_args, **_kwargs: "SYS")
    monkeypatch.setattr(engine_module.l6, "get_max_tokens", lambda _intent: 200)

    monkeypatch.setattr(engine_module.l5, "rolling_window", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rolling_window should not run")))
    monkeypatch.setattr(engine_module.l5, "summarize_history", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("summarize_history should not run")))
    monkeypatch.setattr(engine_module.l5, "enforce_token_budget", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("enforce_token_budget should not run")))

    monkeypatch.setattr(engine_module, "call_with_history", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("call_with_history should not run")))
    monkeypatch.setattr(engine_module, "call", lambda **_kwargs: "DIRECT_RESPONSE")
    monkeypatch.setattr(engine_module.l3, "store", lambda *_args, **_kwargs: None)

    engine = CarbonProxyEngine()
    result = engine.complete(prompt="prompt without history", history=None)

    assert result["response"] == "DIRECT_RESPONSE"
    assert result["cache_hit"] is False

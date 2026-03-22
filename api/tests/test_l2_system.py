from layers.l2 import SYSTEM_PROMPTS, get_system_prompt, audit_system_prompt


def test_system_prompts_are_short_and_targeted():
    banned = ["you are helpful", "be polite", "as an ai"]

    for intent, prompt in SYSTEM_PROMPTS.items():
        token_est = len(prompt.split()) * 1.3
        assert token_est < 15, f"{intent} prompt too long: {token_est} tokens"
        lowered = prompt.lower()
        for phrase in banned:
            assert phrase not in lowered


def test_get_system_prompt_fallback_default():
    assert get_system_prompt("nonexistent") == SYSTEM_PROMPTS["default"]


def test_audit_bloated_prompt_recommends_compress():
    bloated = (
        "You are a helpful, harmless, and honest AI assistant. "
        "Your goal is to provide accurate, useful, and clear responses to all user queries. "
        "Always be polite and professional in your responses. "
        "Make sure to acknowledge when you do not know something."
    )

    result = audit_system_prompt(bloated)

    assert result["tokens"] > 0
    assert len(result["issues"]) >= 3
    assert result["recommendation"] == "compress"

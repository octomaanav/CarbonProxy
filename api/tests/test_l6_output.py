from layers.l6 import build_structured_prompt, get_max_tokens, build_json_prompt


def test_build_structured_prompt_variants():
    r_json = build_structured_prompt("explain docker", output_format="json")
    assert r_json.endswith("Output valid JSON only. No prose.")

    r_code = build_structured_prompt("explain docker", output_format="code")
    assert r_code.endswith("Output code only. No explanation.")

    r_bullets = build_structured_prompt("explain docker", output_format="bullets", bullet_count=3)
    assert r_bullets.endswith("Respond with exactly 3 bullet points.")

    r_words = build_structured_prompt("explain docker", max_words=50)
    assert r_words.endswith("Answer in under 50 words.")


def test_build_structured_prompt_no_constraints_returns_original():
    prompt = "plain prompt"
    assert build_structured_prompt(prompt) == prompt


def test_get_max_tokens_by_intent():
    assert get_max_tokens("simple_qa") == 200
    assert get_max_tokens("code_gen") == 1000
    assert get_max_tokens("analysis") == 800
    assert get_max_tokens("default") == 500
    assert get_max_tokens("unknown_intent") == 500


def test_build_json_prompt_schema_format():
    prompt = "Extract fields"
    schema = {"name": "string", "age": "number"}
    result = build_json_prompt(prompt, schema)

    assert "Respond with ONLY valid JSON" in result
    assert '"name": string' in result
    assert '"age": number' in result

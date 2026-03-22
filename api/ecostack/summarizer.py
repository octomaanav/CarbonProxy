"""Summarize exchanges via Gemini Flash for the EcoStack memory layer."""

import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_MODEL = "gemini-2.0-flash"

_PROMPT_TEMPLATE = (
    "In one sentence of maximum 30 words, summarize the single most important "
    "fact or user preference revealed in this exchange. Focus on information "
    "that would help answer future questions from this user. Return only the "
    "summary sentence, no preamble.\n"
    "User: {prompt}\n"
    "Assistant: {response}"
)


def summarize_exchange(prompt: str, response: str) -> str:
    """Summarize a prompt/response pair into ≤30 words via Gemini Flash."""
    try:
        result = _client.models.generate_content(
            model=_MODEL,
            contents=_PROMPT_TEMPLATE.format(prompt=prompt, response=response),
            config=types.GenerateContentConfig(
                max_output_tokens=60,
                temperature=0.2,
            ),
        )
        summary = (result.text or "").strip()
        return summary if summary else prompt[:100]
    except Exception as e:
        print(f"[summarizer] Gemini Flash failed: {e}")
        return prompt[:100]
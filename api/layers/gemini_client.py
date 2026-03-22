# api/layers/gemini_client.py
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google import genai
from google.genai import types
from config import GEMINI_API_KEY, MODEL_FLASH, MODEL_PRO

_client = genai.Client(api_key=GEMINI_API_KEY)


def call(
    prompt: str,
    model: str = MODEL_FLASH,
    system: str = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
    retries: int = 3,
) -> str:
    """
    Single Gemini API call with automatic retry on rate limits.

    Args:
        prompt:      user prompt text
        model:       model name — use MODEL_FLASH for almost everything
        system:      system instruction string
        max_tokens:  max output tokens
        temperature: 0.0 = deterministic, 1.0 = creative
        retries:     retry attempts on 429 rate limit errors

    Returns:
        response text as string
    """
    gen_config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        system_instruction=system if system else None,
    )

    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model=model,
                contents=prompt,
                config=gen_config,
            )
            return response.text or ""

        except Exception as e:
            err = str(e).lower()

            if "429" in err or "resource_exhausted" in err or "rate" in err:
                wait = 2 ** attempt
                print(f"Rate limit. Waiting {wait}s (attempt {attempt + 1}/{retries})...")
                time.sleep(wait)
                continue

            if "quota" in err:
                raise RuntimeError(
                    "Gemini daily quota exhausted. "
                    "Wait until midnight PT or use a different Google account."
                ) from e

            raise

    raise RuntimeError(f"Gemini call failed after {retries} retries.")


def call_with_history(
    messages: list,
    model: str = MODEL_FLASH,
    system: str = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> str:
    """
    Multi-turn conversation call using Gemini chat interface.

    Args:
        messages: list of {"role": "user"|"assistant", "content": str}
        model:    model name
        system:   system instruction
        max_tokens: max output tokens

    Returns:
        response text
    """
    if not messages:
        return ""

    conversation = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        conversation.append(f"{role.upper()}: {content}")

    prompt = "\n".join(conversation)
    return call(
        prompt=prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )

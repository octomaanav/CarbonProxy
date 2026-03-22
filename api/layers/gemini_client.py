# api/layers/gemini_client.py
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, MODEL_FLASH, MODEL_PRO
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')

_client = genai.Client(api_key=API_KEY)


def count_tokens(
    prompt: str,
    model: str = MODEL_FLASH,
    retries: int = 2,
) -> int:
    """Count prompt tokens using Gemini's tokenizer endpoint."""
    text = (prompt or "").strip()
    if not text:
        return 0

    for attempt in range(retries):
        try:
            response = _client.models.count_tokens(
                model=model,
                contents=text,
            )

            # Handle SDK response variations across versions.
            for attr in ("total_tokens", "total_token_count", "token_count"):
                value = getattr(response, attr, None)
                if isinstance(value, int):
                    return max(0, value)

            if hasattr(response, "to_dict"):
                data = response.to_dict()
                for key in ("total_tokens", "total_token_count", "token_count"):
                    value = data.get(key)
                    if isinstance(value, int):
                        return max(0, value)

            raise RuntimeError("Unexpected Gemini count_tokens response schema")

        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

    return 0


def call(
    prompt: str,
    model: str = MODEL_FLASH,
    system: str = None,
    max_tokens: int | None = None,
    temperature: float = 0.7,
    retries: int = 3,
) -> str:
    """
    Single Gemini API call with automatic retry on rate limits.

    Args:
        prompt:      user prompt text
        model:       model name — use MODEL_FLASH for almost everything
        system:      system instruction string
        max_tokens:  max output tokens (None = let the model decide)
        temperature: 0.0 = deterministic, 1.0 = creative
        retries:     retry attempts on 429 rate limit errors

    Returns:
        response text as string
    """
    config_kwargs = {"temperature": temperature}
    if system:
        config_kwargs["system_instruction"] = system
    if max_tokens is not None:
        config_kwargs["max_output_tokens"] = max_tokens

    gen_config = types.GenerateContentConfig(**config_kwargs)

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
    max_tokens: int | None = None,
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

"""Groq API access. Every call returns (ok, payload) so the UI never crashes."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

# Groq retired the Llama chat models on 2026-08-16. gpt-oss-120b is the
# recommended replacement for llama-3.3-70b-versatile.
MODEL = "openai/gpt-oss-120b"

MODEL_CHOICES: Dict[str, str] = {
    "GPT-OSS 120B — best plans (default)": "openai/gpt-oss-120b",
    "GPT-OSS 20B — faster, lighter": "openai/gpt-oss-20b",
    "Qwen 3.6 27B — alternative": "qwen/qwen3.6-27b",
}

FRIENDLY_ERRORS: Dict[str, str] = {
    "auth": "Your Groq API key isn't working. Check GROQ_API_KEY in your .env file.",
    "rate": "Groq is rate limiting the free tier right now. Wait about a minute and try again.",
    "network": "Couldn't reach Groq. Check your internet connection and try again.",
    "empty": "The model came back empty. Try generating again — it usually works second time.",
    "parse": "The model returned something malformed. Hit generate again to retry.",
    "model": (
        "That model isn't available on Groq any more. Pick a different one in the "
        "sidebar — GPT-OSS 120B is the current default."
    ),
    "unknown": "Something went wrong talking to the model. Try again in a moment.",
}


def get_client(api_key: Optional[str] = None) -> Optional[Groq]:
    """Build a Groq client, or None if no key is configured."""
    key = api_key or os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        return None


def _classify(err: Exception) -> str:
    text = f"{type(err).__name__} {err}".lower()
    if "authentication" in text or "api key" in text or "401" in text or "invalid_api_key" in text:
        return "auth"
    if "rate" in text or "429" in text or "quota" in text:
        return "rate"
    if "connection" in text or "timeout" in text or "network" in text or "dns" in text:
        return "network"
    if any(w in text for w in ("decommission", "deprecat", "model_not_found", "does not exist",
                               "no longer supported", "404")):
        return "model"
    return "unknown"


LAST_ERROR: Dict[str, str] = {"detail": ""}


def ask(
    system_prompt: str,
    user_prompt: str,
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 3000,
    model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Send one prompt to Groq. Returns (ok, text) or (False, friendly message).

    The raw exception text is kept in LAST_ERROR so the UI can show it on
    request — a friendly message shouldn't mean an undiagnosable one.
    """
    client = get_client(api_key)
    if client is None:
        return False, "No Groq API key found. Add one in the sidebar to start generating."

    try:
        response = client.chat.completions.create(
            model=model or MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as err:  # noqa: BLE001 - surfaced to the user, never raised
        LAST_ERROR["detail"] = f"{type(err).__name__}: {err}"[:600]
        return False, FRIENDLY_ERRORS[_classify(err)]

    LAST_ERROR["detail"] = ""

    try:
        text = (response.choices[0].message.content or "").strip()
    except (AttributeError, IndexError, TypeError):
        return False, FRIENDLY_ERRORS["parse"]

    if len(text) < 40:
        return False, FRIENDLY_ERRORS["empty"]
    return True, text


def ask_json(
    system_prompt: str,
    user_prompt: str,
    api_key: Optional[str] = None,
    temperature: float = 0.6,
    model: Optional[str] = None,
) -> Tuple[bool, Any]:
    """Same as ask(), but expects and parses a JSON object or array."""
    ok, text = ask(
        system_prompt + "\n\nReturn ONLY valid JSON. No markdown fences, no commentary.",
        user_prompt,
        api_key=api_key,
        temperature=temperature,
        model=model,
    )
    if not ok:
        return False, text

    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"[\{\[].*[\}\]]", cleaned, flags=re.DOTALL)
    if not match:
        return False, FRIENDLY_ERRORS["parse"]
    try:
        return True, json.loads(match.group(0))
    except json.JSONDecodeError:
        return False, FRIENDLY_ERRORS["parse"]


def available_models() -> List[str]:
    return list(MODEL_CHOICES.values())


def probe(api_key: Optional[str] = None, model: Optional[str] = None) -> Tuple[bool, str]:
    """One tiny round-trip to confirm the key and model actually work."""
    client = get_client(api_key)
    if client is None:
        return False, "No API key set."
    try:
        client.chat.completions.create(
            model=model or MODEL,
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, f"Connected — {model or MODEL} is responding."
    except Exception as err:  # noqa: BLE001
        detail = f"{type(err).__name__}: {err}"[:400]
        return False, f"{FRIENDLY_ERRORS[_classify(err)]}\n\n`{detail}`"

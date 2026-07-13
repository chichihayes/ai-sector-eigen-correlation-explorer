"""
Single place that talks to OpenRouter. Both the AI writeup (ai_analyst.py)
and the AI sector/stock discovery (ai_discovery.py) call through here so
there's exactly one copy of the auth/request/error-surface logic.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-5"  # swap freely; any OpenRouter model works


def _get_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Create a .env file (see .env.example) "
            "with OPENROUTER_API_KEY=your_key_here — get a key at openrouter.ai."
        )
    return key


def call_openrouter(prompt: str, max_tokens: int = 400, json_mode: bool = False) -> str:
    """
    Sends a single-turn prompt to OpenRouter and returns the raw text
    content of the reply. Raises on any failure (missing key, HTTP error,
    timeout) — callers decide how to degrade.
    """
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

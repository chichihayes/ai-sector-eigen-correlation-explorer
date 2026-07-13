"""
AI-driven replacement for hand-maintaining data/sector_map.py: asks the LLM
which sectors/themes a ticker belongs to, and which stocks belong to a
given sector/theme. Open-ended — not limited to a fixed sector list.

Both functions return an empty list on ANY failure (missing key, network
error, bad/unparseable response) rather than raising, so the caller
(app.py) can fall back to the curated data/sector_map.py flow without
special-casing exceptions — the same degrade-gracefully philosophy as
core/ai_analyst.py.
"""

import json
import re

from core.openrouter_client import call_openrouter


def _parse_json_object(text: str) -> dict | None:
    """Best-effort JSON object extraction: try a direct parse first, then
    fall back to pulling the first {...} substring out of surrounding
    prose/code fences a model might add despite instructions."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def identify_sectors(ticker: str) -> list[str]:
    """Returns every real sector or thematic group `ticker` plausibly
    belongs to (e.g. NVDA -> ["Semiconductors", "AI Infrastructure"]),
    ordered most to least specific. Not restricted to a fixed taxonomy."""
    prompt = f"""Return ONLY a JSON object of the form {{"sectors": ["...", "..."]}}
listing every real sector or thematic group the public company with stock
ticker {ticker} belongs to. Include 1 to 4 items, most specific first.
Use concise, standard sector/theme names (e.g. "Semiconductors",
"AI Infrastructure", "Cloud Software"). No commentary, no markdown, only
the JSON object."""

    try:
        raw = call_openrouter(prompt, max_tokens=150, json_mode=True)
        data = _parse_json_object(raw)
        if not data or not isinstance(data.get("sectors"), list):
            return []

        sectors = []
        for s in data["sectors"]:
            if isinstance(s, str) and s.strip():
                cleaned = s.strip()
                if cleaned not in sectors:
                    sectors.append(cleaned)
        return sectors[:6]
    except Exception:
        return []


def propose_sector_stocks(sector: str, exclude_ticker: str, limit: int = 20) -> list[str]:
    """Returns up to `limit` real, currently-listed stock tickers in
    `sector`, excluding `exclude_ticker`. Caller is expected to validate
    each ticker independently (e.g. via yfinance) before trusting it."""
    prompt = f"""Return ONLY a JSON object of the form {{"tickers": ["...", "..."]}}
listing up to {limit} real, currently publicly-listed, liquid stock
tickers in the "{sector}" sector/theme. Use official exchange ticker
symbols only (e.g. "AVGO", not company names). Do not include
"{exclude_ticker}". No commentary, no markdown, only the JSON object."""

    try:
        raw = call_openrouter(prompt, max_tokens=400, json_mode=True)
        data = _parse_json_object(raw)
        if not data or not isinstance(data.get("tickers"), list):
            return []

        exclude = exclude_ticker.upper().strip()
        tickers = []
        for t in data["tickers"]:
            if isinstance(t, str) and t.strip():
                cleaned = t.strip().upper()
                if cleaned != exclude and cleaned not in tickers:
                    tickers.append(cleaned)
        return tickers[:limit]
    except Exception:
        return []

"""
Pulls price history and live company info via yfinance.

yfinance needs no API key and has no hard rate limit like Alpha Vantage's
5-calls/minute free tier (which is why the original notebook needed
time.sleep(12) between every request). This is the main reason to switch:
it's faster, keyless, and doesn't fail silently when a rate limit is hit.
"""

import sys
import time
import pandas as pd
import yfinance as yf

sys.path.append("..")
from data.sector_map import peers_for_sector


def yahoo_sector_hint(ticker: str) -> str | None:
    """
    Fall back to yfinance's own 'sector' field to *report* an unmatched
    ticker's sector to the user — informational only, since we don't build
    a peer group from it (no curated universe for arbitrary Yahoo sector
    strings).
    """
    try:
        info = yf.Ticker(ticker).info
        return info.get("sector")
    except Exception:
        return None


def fetch_price_history(tickers: list[str], period: str = "6mo") -> pd.DataFrame:
    """
    Returns a DataFrame of adjusted close prices, one column per ticker,
    for the given yfinance period string (e.g. '1mo', '3mo', '6mo', '1y').
    Tickers that fail to fetch are dropped with a warning, not silently —
    the caller should check which columns actually came back.
    """
    data = yf.download(
        tickers, period=period, auto_adjust=True, progress=False, threads=True
    )

    if data.empty:
        raise ValueError(f"No price data returned for {tickers} (period={period}).")

    # yfinance returns a MultiIndex column frame when >1 ticker, a plain
    # frame when there's exactly 1 — normalize both to ticker-per-column.
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data[["Close"]]
        close.columns = tickers

    missing = [t for t in tickers if t not in close.columns or close[t].isna().all()]
    if missing:
        print(f"⚠️  Could not fetch data for: {missing} (dropped from analysis)")
        close = close.drop(columns=[c for c in missing if c in close.columns])

    return close.dropna(how="all")


def fetch_market_caps(tickers: list[str]) -> dict[str, float]:
    """
    Live market cap per ticker in USD, used for the actual big-vs-small
    classification shown in the app (the static LARGE/MID/SMALL labels in
    sector_map.py are only a curation-time hint, not live truth).
    """
    caps = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            caps[t] = info.get("marketCap")
        except Exception:
            caps[t] = None
        time.sleep(0.15)  # be polite to the endpoint, not rate-limit driven
    return caps


def validate_and_rank_candidates(
    tickers: list[str], exclude: str, limit: int
) -> list[tuple[str, float]]:
    """
    Validates AI-proposed candidate tickers against yfinance and ranks the
    real ones by live market cap. A candidate with no market cap is treated
    as unresolvable (delisted/hallucinated/typo'd ticker) and dropped.
    Returns the top `limit` as (ticker, market_cap) pairs, highest cap first.
    """
    exclude = exclude.upper().strip()
    candidates = [t for t in tickers if t.upper().strip() != exclude]
    caps = fetch_market_caps(candidates)
    ranked = sorted(
        ((t, c) for t, c in caps.items() if c is not None),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return ranked[:limit]


def cap_tier(market_cap: float | None) -> str:
    if market_cap is None:
        return "UNKNOWN"
    if market_cap >= 200_000_000_000:
        return "LARGE"
    if market_cap >= 10_000_000_000:
        return "MID"
    return "SMALL"

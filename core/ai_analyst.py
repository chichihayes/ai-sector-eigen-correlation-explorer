"""
Sends the deterministic relationship_table() result (core/pca_engine.py)
to an LLM (via OpenRouter, see core/openrouter_client.py) and asks for a
short, direct explanation — not a full analyst writeup. The yes/no/
direction call for each peer is already decided by the correlation math
before this ever runs; the AI's only job here is to explain that result
in plain language, not to reinterpret or hedge it.
"""

from core.openrouter_client import call_openrouter


def generate_analysis(
    target_ticker: str,
    sector: str,
    moves_with: list[str],
    moves_against: list[str],
    no_relationship: list[str],
    dominant_ticker: str,
    explained_pct_top: float,
    trend_stats: dict[str, float] | None = None,
) -> str:
    """Returns a short plain-English explanation, or a clear error string on
    failure — never raises out to the UI layer so a missing/invalid key
    doesn't crash the app, just degrades to showing the raw table instead."""

    trend_line = ""
    if trend_stats:
        trend_desc = ", ".join(
            f"{t}: {pct:+.1f}%" for t, pct in sorted(
                trend_stats.items(), key=lambda kv: kv[1], reverse=True
            )
        )
        trend_line = f"\nPrice trend over the analysis window (% change): {trend_desc}"

    prompt = f"""A trader wants one direct question answered about {target_ticker} ({sector}):
if {target_ticker} moves, is there a real relationship with the rest of this
group, and what's the likely pattern? Yes/no, then explain briefly.

Moves with {target_ticker} (positively correlated): {', '.join(moves_with) or 'none'}
Moves against {target_ticker} (negatively correlated): {', '.join(moves_against) or 'none'}
No reliable relationship: {', '.join(no_relationship) or 'none'}
Dominant driver of the group's shared movement: {dominant_ticker}
Top factor explains {explained_pct_top:.1f}% of the group's shared variance.{trend_line}

Write at most 80 words. Start with a direct yes/no answer. State plainly
whether {target_ticker} can be used as a signal for the rest of the group
(or vice versa), or whether it's decoupled and should be traded on its own.
No analyst jargon, no dispersion/bellwether language, no disclaimers,
no compliance boilerplate — just the direct answer."""

    try:
        return call_openrouter(prompt, max_tokens=180)
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({e}). The relationship table above is unaffected."

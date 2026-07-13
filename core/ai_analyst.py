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

    prompt = f"""A trader wants two direct questions answered about {target_ticker} ({sector}):

1. If {target_ticker} moves, is there a real relationship with the rest of
   this group — yes/no, and what's the likely pattern?
2. {dominant_ticker} is the "dominant driver" — what does that actually
   mean here, and what's the practical implication for a trader?

Moves with {target_ticker} (positively correlated): {', '.join(moves_with) or 'none'}
Moves against {target_ticker} (negatively correlated): {', '.join(moves_against) or 'none'}
No reliable relationship: {', '.join(no_relationship) or 'none'}
Dominant driver of the group's shared movement: {dominant_ticker}
Top factor explains {explained_pct_top:.1f}% of the group's shared variance.{trend_line}

Write at most 110 words. Start with a direct yes/no answer on {target_ticker}'s
relationship to the group. Then explain plainly what it means that
{dominant_ticker} is the dominant driver — it's the stock whose returns best
represent the single biggest shared factor moving this group, i.e. the one
whose moves other members are most likely tied to. State the implication:
is {dominant_ticker} the one to watch for the earliest/clearest read on this
group's shared move, and does {target_ticker} lead or lag it? No analyst
jargon, no dispersion/bellwether language, no disclaimers, no compliance
boilerplate — just the direct answer."""

    try:
        return call_openrouter(prompt, max_tokens=320)
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({e}). The relationship table above is unaffected."

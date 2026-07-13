"""
Sends the computed PCA/correlation results to an LLM (via OpenRouter, see
core/openrouter_client.py) and asks for a plain-English analyst-style
writeup.
"""

from core.openrouter_client import call_openrouter


def generate_analysis(
    target_ticker: str,
    sector: str,
    peers: list[str],
    dominant_ticker: str,
    explained_pct_top: float,
    correlation_label: str,
    signal_label: str,
    cap_breakdown: dict[str, str],
    trend_stats: dict[str, float] | None = None,
) -> str:
    """Returns a plain-English writeup, or a clear error string on failure —
    never raises out to the UI layer so a missing/invalid key doesn't crash
    the app, just degrades to showing the raw numbers instead."""

    trend_line = ""
    if trend_stats:
        trend_desc = ", ".join(
            f"{t}: {pct:+.1f}%" for t, pct in sorted(
                trend_stats.items(), key=lambda kv: kv[1], reverse=True
            )
        )
        trend_line = f"\nPrice trend over the analysis window (% change, high to low): {trend_desc}"

    prompt = f"""You are a buy-side equity analyst. Write a concise (150-200 word) analysis for a client who holds/watches {target_ticker}, in the {sector} sector.

Correlation group analyzed: {', '.join(peers)}
Dominant driver stock (largest eigenvector loading): {dominant_ticker}
Top principal component explains {explained_pct_top:.1f}% of group variance.
Correlation structure: {correlation_label}
Signal strength: {signal_label}
Market cap tiers in this group: {cap_breakdown}{trend_line}

Explain what this means in practical terms: is this sector moving as a
unified block or independently, which company is the bellwether to watch,
and whether the smaller-cap names in the group tend to follow the
larger-cap names or move independently. Reference the price trend data
above where it's relevant to your read. Avoid generic disclaimers — give
a direct, specific read of what the numbers show. This is for portfolio
research, not investment advice, so do not include compliance boilerplate."""

    try:
        return call_openrouter(prompt, max_tokens=400)
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({e}). Numeric results above are unaffected."

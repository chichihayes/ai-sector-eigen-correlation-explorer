import sys
import os

sys.path.append(os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.express as px

from data.sector_map import find_sectors_for_ticker, peers_for_sector, all_known_tickers
from core.data_fetcher import (
    yahoo_sector_hint,
    fetch_price_history,
    fetch_market_caps,
    cap_tier,
    validate_and_rank_candidates,
)
from core.ai_discovery import identify_sectors, propose_sector_stocks
from core.pca_engine import run_pca, signal_strength_label, correlation_structure_label
from core.ai_analyst import generate_analysis

st.set_page_config(page_title="Sector Eigen-Correlation Explorer", layout="wide", page_icon="📊")

# Caching lives here (not inside core/) so core/ stays Streamlit-agnostic.
# AI discovery is expensive and rarely changes -> long TTL. Market data is
# cheap and changes fast -> short TTL.
cached_identify_sectors = st.cache_data(ttl=86400, show_spinner=False)(identify_sectors)
cached_propose_sector_stocks = st.cache_data(ttl=86400, show_spinner=False)(propose_sector_stocks)
cached_fetch_price_history = st.cache_data(ttl=1800, show_spinner=False)(fetch_price_history)
cached_fetch_market_caps = st.cache_data(ttl=1800, show_spinner=False)(fetch_market_caps)
cached_validate_and_rank_candidates = st.cache_data(ttl=1800, show_spinner=False)(validate_and_rank_candidates)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0E1117 0%, #161022 55%, #0E1117 100%);
    }
    [data-testid="stSidebar"] {
        background: #12141D;
        border-right: 1px solid rgba(124, 92, 252, 0.15);
    }
    [data-testid="stMetric"] {
        background: rgba(124, 92, 252, 0.08);
        border: 1px solid rgba(124, 92, 252, 0.25);
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] {
        color: #A9A9C2 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Sector Eigen-Correlation Explorer")
st.caption(
    "Pick a stock → AI identifies the sectors/themes it belongs to → AI proposes "
    "peer stocks, ranked by live market cap → run PCA/eigen-decomposition on returns → "
    "an AI analyst summarizes it."
)

with st.sidebar:
    st.header("Configuration")
    ticker_input = st.text_input("Stock ticker", value="NVDA").upper().strip()

    ai_sectors = cached_identify_sectors(ticker_input) if ticker_input else []
    if ai_sectors:
        sector_source = "ai"
        sector_options = ai_sectors
    else:
        sector_source = "curated"
        sector_options = find_sectors_for_ticker(ticker_input) if ticker_input else []

    sector = None
    if sector_options:
        sector = st.selectbox(
            "Sector group to analyze against",
            sector_options,
            help="This ticker sits in more than one group — pick which "
                 "peer set to run the correlation analysis against."
            if len(sector_options) > 1 else None,
        )
    elif ticker_input:
        st.caption(f"Couldn't classify {ticker_input} into a sector yet.")

    peer_count = 10
    if sector_source == "ai" and sector:
        peer_count = st.slider("Peers to compare", min_value=2, max_value=20, value=10)

    period = st.selectbox("History window", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    st.caption(
        f"Offline fallback sectors (used if AI discovery is unavailable): "
        f"{', '.join(all_known_tickers()[:12])} ..."
    )
    run_button = st.button("Run Analysis", type="primary")

if run_button and ticker_input:
    if sector is None:
        with st.spinner(f"Resolving sector for {ticker_input}..."):
            hint = yahoo_sector_hint(ticker_input)
        if hint:
            st.warning(
                f"{ticker_input} maps to Yahoo sector '{hint}', but neither the AI layer "
                f"nor the offline curated universe could build a peer group for it yet."
            )
        else:
            st.error(f"Couldn't resolve a sector for {ticker_input}. Try a different ticker.")
        st.stop()

    candidate_caps = None

    if sector_source == "ai":
        with st.spinner(f"AI is proposing peer stocks for '{sector}'..."):
            candidates = cached_propose_sector_stocks(sector, exclude_ticker=ticker_input, limit=20)

        if not candidates:
            st.error(
                f"AI couldn't build a peer list for '{sector}' — try a different sector "
                f"from the dropdown, or a different ticker."
            )
            st.stop()

        with st.spinner("Validating candidates and ranking by market cap..."):
            ranked = cached_validate_and_rank_candidates(candidates, exclude=ticker_input, limit=20)

        if not ranked:
            st.error(
                f"None of the AI-proposed tickers for '{sector}' could be validated — "
                f"try a different sector from the dropdown, or a different ticker."
            )
            st.stop()

        ranked = ranked[:peer_count]
        peers = {t: c for t, c in ranked}
        candidate_caps = dict(ranked)
    else:
        peers = peers_for_sector(sector, exclude=ticker_input)

    group_tickers = [ticker_input] + list(peers.keys())

    st.subheader(f"Sector: {sector} ({'AI-discovered' if sector_source == 'ai' else 'curated'})")
    st.write(f"Analyzing **{ticker_input}** against {len(peers)} sector peers: "
             f"{', '.join(peers.keys())}")

    with st.spinner(f"Fetching {period} price history for {len(group_tickers)} tickers..."):
        try:
            prices = cached_fetch_price_history(group_tickers, period=period)
        except ValueError as e:
            st.error(str(e))
            st.stop()

    if prices.shape[1] < 2:
        st.error("Not enough tickers returned valid price data to run correlation analysis.")
        st.stop()

    with st.spinner("Fetching live market cap data..."):
        if candidate_caps is not None:
            caps = dict(candidate_caps)
            missing = [t for t in prices.columns if t not in caps]
            if missing:
                caps.update(cached_fetch_market_caps(missing))
        else:
            caps = cached_fetch_market_caps(list(prices.columns))
    cap_tiers = {t: cap_tier(caps.get(t)) for t in prices.columns}

    with st.spinner("Running PCA / eigen-decomposition..."):
        result = run_pca(prices)

    trend_stats = ((prices.iloc[-1] / prices.iloc[0] - 1) * 100).to_dict()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Correlation Matrix")
        fig = px.imshow(
            result.correlation_matrix,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            aspect="auto",
            template="plotly_dark",
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Price History (normalized to 100 at start)")
        normalized = prices / prices.iloc[0] * 100
        st.line_chart(normalized)

    with col2:
        st.subheader("Key Findings")
        st.metric("Dominant driver", result.dominant_ticker)
        st.metric("Top component variance explained",
                   f"{result.explained_variance_pct[0]:.1f}%")
        st.write(f"**Structure:** {correlation_structure_label(result.eigenvalues)}")
        st.write(f"**Signal:** {signal_strength_label(result.explained_variance_pct[0])}")

        st.subheader("Market Cap Tiers")
        cap_df = pd.DataFrame({
            "Ticker": list(cap_tiers.keys()),
            "Tier": list(cap_tiers.values()),
            "Market Cap ($B)": [
                f"{caps[t]/1e9:.1f}" if caps.get(t) else "—" for t in cap_tiers
            ],
        })
        st.dataframe(cap_df, hide_index=True, use_container_width=True)

        st.subheader("Top Component Loadings")
        loadings_df = pd.DataFrame({
            "Ticker": list(result.top_component_loadings.keys()),
            "Loading": [f"{v:+.3f}" for v in result.top_component_loadings.values()],
        }).sort_values("Loading", ascending=False)
        st.dataframe(loadings_df, hide_index=True, use_container_width=True)

    st.subheader("🧠 AI Analyst Summary")
    with st.spinner("Generating AI analysis..."):
        cap_breakdown = {tier: [t for t, c in cap_tiers.items() if c == tier]
                          for tier in set(cap_tiers.values())}
        writeup = generate_analysis(
            target_ticker=ticker_input,
            sector=sector,
            peers=list(prices.columns),
            dominant_ticker=result.dominant_ticker,
            explained_pct_top=result.explained_variance_pct[0],
            correlation_label=correlation_structure_label(result.eigenvalues),
            signal_label=signal_strength_label(result.explained_variance_pct[0]),
            cap_breakdown=cap_breakdown,
            trend_stats=trend_stats,
        )
    st.write(writeup)

else:
    st.info("Enter a ticker in the sidebar and click **Run Analysis** to begin.")

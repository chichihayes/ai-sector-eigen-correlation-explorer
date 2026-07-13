# Sector Eigen-Correlation Explorer

Pick a stock → an AI layer figures out which sectors/themes it belongs to
→ AI proposes peer stocks in that sector, validated and ranked by live
market cap → recent price history is pulled for the group → PCA /
eigen-decomposition runs on daily returns → an AI analyst summarizes what
the correlation structure means: is the group moving as one block or
independently, who's the bellwether, and whether smaller-cap names follow
the large-cap leader or move on their own.

## How it works

1. **Sector discovery** (`core/ai_discovery.py`) — given a ticker, an LLM
   (via OpenRouter) returns every sector/theme it plausibly belongs to,
   open-ended rather than picked from a fixed list (e.g. NVDA comes back
   as `["Semiconductors", "AI Infrastructure", "Data Center Hardware",
   "Graphics Processing Units"]`). The sidebar shows these as a dropdown —
   pick which one to analyze against.
2. **Peer discovery** (`core/ai_discovery.py` + `core/data_fetcher.py`) —
   for the chosen sector, the LLM proposes up to 20 candidate tickers.
   Every candidate is checked against yfinance: no market cap means the
   ticker doesn't actually resolve, so it's dropped. Survivors are ranked
   by live market cap; a sidebar slider picks how many of the top-ranked
   ones to actually compare against (default 10).
3. **Price + market cap fetch** (`core/data_fetcher.py`) — yfinance, no
   key required, results cached (`st.cache_data`) to cut repeat calls.
4. **PCA / eigen-decomposition** (`core/pca_engine.py`) — daily returns
   are centered and their covariance matrix eigen-decomposed via `eigh`
   (numerically correct for symmetric matrices — the original notebook
   used plain `eig`, which is the wrong tool here and can return spurious
   tiny imaginary components).
5. **AI narrative** (`core/ai_analyst.py`) — the numeric PCA results,
   plus each ticker's real % price change over the fetch window, are sent
   to an LLM for a plain-English writeup grounded in that actual trend
   data rather than a hallucinated "current market conditions." If the
   key is missing or the call fails, the app still shows every
   numeric/chart result — this layer degrades gracefully rather than
   crashing the app, same as sector/peer discovery.

Both AI call sites go through one shared client, `core/openrouter_client.py`,
so there's exactly one place that talks to OpenRouter.

## Architecture

```mermaid
graph LR
    subgraph UI["app.py — Streamlit UI + caching"]
    end

    UI --> Discovery["core/ai_discovery.py<br/>identify_sectors / propose_sector_stocks"]
    UI --> Fetcher["core/data_fetcher.py<br/>fetch_price_history / validate_and_rank_candidates"]
    UI --> PCA["core/pca_engine.py<br/>run_pca (eigh)"]
    UI --> Analyst["core/ai_analyst.py<br/>generate_analysis"]

    Discovery --> Client["core/openrouter_client.py"]
    Analyst --> Client
    Client -->|HTTPS| OpenRouter[(OpenRouter API)]

    Fetcher -->|no key needed| YFinance[(yfinance / Yahoo)]
```

## Request flow (one "Run Analysis" click)

```mermaid
flowchart TD
    A["User enters ticker (e.g. NVDA)"] --> B["AI: identify_sectors(ticker)"]
    B -->|sectors returned| C["Sidebar: sector dropdown + peer-count slider"]
    B -->|AI unavailable, empty list| Z["Clear error shown, analysis stops"]
    C --> E["User picks a sector, clicks Run Analysis"]
    E --> G["AI: propose_sector_stocks(sector)"]
    G --> H["yfinance: validate_and_rank_candidates<br/>(drop unresolvable tickers, rank by market cap)"]
    H --> I["Top N peers (slider count)"]
    I --> K["yfinance: fetch_price_history for target + peers"]
    K --> L["pca_engine.run_pca<br/>covariance -> eigh -> eigenvalues/eigenvectors"]
    L --> M["Correlation matrix, dominant ticker,<br/>explained variance, component loadings"]
    M --> N["ai_analyst.generate_analysis<br/>(numeric results + real % price trend per ticker)"]
    N --> O["Streamlit renders: heatmap, price chart,<br/>cap-tier table, loadings table, AI writeup"]
```

## Setup (VS Code / local)

```bash
# 1. Clone / open this folder in VS Code
# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your API key
cp .env.example .env
# open .env and paste your real OpenRouter key (get one free at openrouter.ai)

# 5. Run it
streamlit run app.py
```

Streamlit opens automatically at **http://localhost:8501**. Without an
`OPENROUTER_API_KEY`, sector/peer discovery and the AI writeup can't run —
the app shows a clear error instead of crashing, but a key is required to
actually use it, since there's no offline data source behind it.

## Deploying (free)

[Streamlit Community Cloud](https://streamlit.io/cloud) is the best free
fit for this app specifically because it runs as a persistent process —
no serverless execution-time limit to fight, unlike e.g. Vercel's free
tier (10s Python function timeout), which this pipeline's AI + yfinance
calls would routinely exceed.

1. Push this repo to GitHub (`.env` is gitignored — never committed).
2. On [share.streamlit.io](https://share.streamlit.io), connect the repo
   and point it at `app.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   OPENROUTER_API_KEY = "your_real_key_here"
   ```
   Never put the real key in `.env.example` or anywhere in the repo —
   Streamlit Cloud secrets are the only place it should live in
   production.

## Extending it

- **Swap the AI model**: change `MODEL` in `core/openrouter_client.py` to
  any OpenRouter-supported model string.
- **Change how many candidate peers the AI proposes**: adjust the
  `limit` argument passed to `propose_sector_stocks` in `app.py`.
- **Change the default history window**: edit the `period` selectbox
  options in `app.py` (uses yfinance period strings: `1mo`, `3mo`, `6mo`,
  `1y`, `2y`, etc.).
- **Change cache lifetimes**: the `st.cache_data(ttl=...)` wrappers near
  the top of `app.py` — AI discovery is cached longer (rarely changes)
  than price/market-cap data (changes fast).

## Security note

The API key is loaded from a local `.env` file (gitignored) via
`python-dotenv` — never hardcoded in source. If you fork/push this to
GitHub, `.env` will not be included; only `.env.example` (with a blank
placeholder) is tracked. For a deployed instance, the key lives in
Streamlit Cloud's Secrets manager instead of any file in the repo.

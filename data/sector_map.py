"""
Static sector -> ticker universe, with a rough cap-tier label per ticker.

This exists because there is no reliable *free* API that returns "give me
every company in sector X" — Yahoo Finance's own sector/industry field only
tells you the sector of a ticker you already know, not the reverse. So we
maintain a curated universe per sector (mix of large caps and smaller/mid
caps) and use yfinance at runtime to confirm the target stock's actual
sector, then pull peers from this table.

Cap tiers are rough buckets (LARGE / MID / SMALL) based on typical market
cap as of curation time — not live data. Live market cap is fetched at
runtime in data_fetcher.py and used for the real "big vs small" split shown
in the app; these tier labels are only a fallback/hint.
"""

SECTOR_UNIVERSE = {
    "Semiconductors": {
        "NVDA": "LARGE", "AVGO": "LARGE", "TSM": "LARGE", "ASML": "LARGE",
        "AMD": "LARGE", "QCOM": "LARGE", "TXN": "LARGE", "INTC": "LARGE",
        "MU": "MID", "AMAT": "MID", "LRCX": "MID", "ON": "MID",
        "MPWR": "MID", "SWKS": "SMALL", "QRVO": "SMALL", "DIOD": "SMALL",
    },
    "Software / Cloud": {
        "MSFT": "LARGE", "ORCL": "LARGE", "CRM": "LARGE", "ADBE": "LARGE",
        "NOW": "LARGE", "INTU": "LARGE", "SNOW": "MID", "DDOG": "MID",
        "MDB": "MID", "HUBS": "MID", "ZS": "MID", "OKTA": "SMALL",
        "GTLB": "SMALL", "FROG": "SMALL",
    },
    "Banks / Financials": {
        "JPM": "LARGE", "BAC": "LARGE", "WFC": "LARGE", "C": "LARGE",
        "GS": "LARGE", "MS": "LARGE", "USB": "MID", "PNC": "MID",
        "TFC": "MID", "FITB": "MID", "ZION": "SMALL", "CMA": "SMALL",
    },
    "Oil & Gas": {
        "XOM": "LARGE", "CVX": "LARGE", "SHEL": "LARGE", "COP": "LARGE",
        "EOG": "MID", "SLB": "MID", "PXD": "MID", "MRO": "SMALL",
        "DVN": "SMALL", "APA": "SMALL",
    },
    "E-commerce / Retail": {
        "AMZN": "LARGE", "WMT": "LARGE", "COST": "LARGE", "HD": "LARGE",
        "TGT": "MID", "EBAY": "MID", "ETSY": "SMALL", "CHWY": "SMALL",
        "W": "SMALL",
    },
    "EV / Auto": {
        "TSLA": "LARGE", "TM": "LARGE", "GM": "MID", "F": "MID",
        "RIVN": "SMALL", "LCID": "SMALL", "NIO": "SMALL",
    },
    "Pharma / Biotech": {
        "JNJ": "LARGE", "PFE": "LARGE", "MRK": "LARGE", "LLY": "LARGE",
        "ABBV": "LARGE", "AMGN": "MID", "GILD": "MID", "VRTX": "MID",
        "REGN": "MID", "MRNA": "SMALL", "BMRN": "SMALL",
    },
    "Airlines": {
        "DAL": "MID", "UAL": "MID", "AAL": "MID", "LUV": "MID",
        "ALK": "SMALL", "JBLU": "SMALL", "SAVE": "SMALL",
    },
    "AI / Datacenter": {
        "NVDA": "LARGE", "AVGO": "LARGE", "MSFT": "LARGE", "GOOGL": "LARGE",
        "META": "LARGE", "AMD": "LARGE", "TSM": "LARGE", "ORCL": "LARGE",
        "SMCI": "MID", "ARM": "MID", "DELL": "MID", "VRT": "MID",
    },
}


def find_sectors_for_ticker(ticker: str) -> list[str]:
    """Look up every curated sector a ticker belongs to (a ticker can sit in
    more than one group, e.g. NVDA is both 'Semiconductors' and
    'AI / Datacenter') — the caller picks which peer group to analyze
    against."""
    ticker = ticker.upper().strip()
    return [sector for sector, members in SECTOR_UNIVERSE.items() if ticker in members]


def peers_for_sector(sector: str, exclude: str = None):
    members = dict(SECTOR_UNIVERSE.get(sector, {}))
    if exclude:
        members.pop(exclude.upper().strip(), None)
    return members


def all_known_tickers():
    seen = set()
    for members in SECTOR_UNIVERSE.values():
        seen.update(members.keys())
    return sorted(seen)

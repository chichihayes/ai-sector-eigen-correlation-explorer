"""
Core PCA/eigen-decomposition logic — generalized from the original
2-stock notebook version to N stocks, and switched to eigh (for symmetric
matrices) instead of eig, since a covariance matrix is always symmetric
and eigh is both faster and numerically safer (guarantees real eigenvalues
instead of relying on np.linalg.eig returning near-zero imaginary parts
that then need to be silently truncated).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PCAResult:
    tickers: list[str]
    eigenvalues: np.ndarray          # sorted descending
    eigenvectors: np.ndarray         # columns match eigenvalues, same order
    explained_variance_pct: np.ndarray
    correlation_matrix: pd.DataFrame
    dominant_ticker: str
    top_component_loadings: dict[str, float]


def run_pca(price_df: pd.DataFrame) -> PCAResult:
    if price_df.shape[1] < 2:
        raise ValueError("Need at least 2 tickers with valid price data to run PCA.")

    returns = price_df.pct_change().dropna()
    if returns.empty:
        raise ValueError("No overlapping trading days with valid returns across tickers.")

    centered = returns - returns.mean()
    cov_matrix = centered.cov()

    # eigh: covariance is always symmetric, so this is the correct and
    # numerically stable choice over the general-purpose eig.
    eigvals, eigvecs = np.linalg.eigh(cov_matrix.values)

    # eigh returns ascending order — flip to descending (largest first)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    total_variance = eigvals.sum()
    explained_pct = (eigvals / total_variance) * 100 if total_variance > 0 else eigvals * 0

    tickers = list(price_df.columns)
    v1 = eigvecs[:, 0]
    dominant_ticker = tickers[int(np.argmax(np.abs(v1)))]
    loadings = {tickers[i]: float(v1[i]) for i in range(len(tickers))}

    return PCAResult(
        tickers=tickers,
        eigenvalues=eigvals,
        eigenvectors=eigvecs,
        explained_variance_pct=explained_pct,
        correlation_matrix=returns.corr(),
        dominant_ticker=dominant_ticker,
        top_component_loadings=loadings,
    )


def signal_strength_label(explained_pct_top: float) -> str:
    if explained_pct_top > 80:
        return "Strong — one dominant factor drives the group; high directional confidence."
    if explained_pct_top > 60:
        return "Moderate — a lead factor exists but watch for confirmation (volume, macro triggers)."
    return "Weak — no dominant factor; the group is behaving noisily/independently."


def correlation_structure_label(eigvals: np.ndarray) -> str:
    if len(eigvals) < 2:
        return "Not enough components to assess structure."
    if np.isclose(eigvals[1], 0, atol=1e-8):
        return "Stocks are highly correlated — they move together as a group."
    if np.isclose(eigvals[0], eigvals[1], rtol=0.2):
        return "Stocks are relatively uncorrelated — each moves on its own drivers."
    return "One strong factor dominates, with secondary independent movement beneath it."

import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from core.pca_engine import run_pca, signal_strength_label, correlation_structure_label

np.random.seed(42)
n_days = 60
factor = np.random.normal(0, 1, n_days)
prices = pd.DataFrame({
    "AAA": 100 * np.cumprod(1 + 0.01 * factor + np.random.normal(0, 0.002, n_days)),
    "BBB": 100 * np.cumprod(1 + 0.012 * factor + np.random.normal(0, 0.002, n_days)),
    "CCC": 100 * np.cumprod(1 + 0.008 * factor + np.random.normal(0, 0.002, n_days)),
    "DDD": 100 * np.cumprod(1 + np.random.normal(0, 0.01, n_days)),
})

result = run_pca(prices)
print("Tickers:", result.tickers)
print("Eigenvalues:", result.eigenvalues)
print("Explained variance %:", result.explained_variance_pct)
print("Dominant ticker:", result.dominant_ticker)
print("Loadings:", result.top_component_loadings)
print()
print("Structure label:", correlation_structure_label(result.eigenvalues))
print("Signal label:", signal_strength_label(result.explained_variance_pct[0]))
print()
print("Correlation matrix:")
print(result.correlation_matrix.round(2))

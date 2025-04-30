---
layout: post
title: "Portfolio Simulator"
author: Ivan Bercovich
date: 2023-10-21 01:01:01 -0700
categories:
---

This document is intended to help those interested in venture capital reason about expected fund-level returns. All multiples are **net to LPs** (i.e. after fees and 20 % carry) unless noted. I wrote this originally in 2023, and updated it in April 2025 with about 60 min of vibe coding. After many attempts to generate the distribution using monte carlo methods, I reverted to picking a gamma distribution that fit the data.

I took data from [this 2020 report](https://www.cambridgeassociates.com/wp-content/uploads/2020/07/WEB-2020-Q1-USVC-Benchmark-Book.pdf) (page 14), and filtered it for the 10 year period between 2004 and 2013. I chose that period because the vintages surrounding the internet bubble show unusually high volatility, and discarded years closer to 2020 given that it takes about 7 years for the TVPI to stabilize. I also used [Angel List](https://www.angellist.com/funds-performance-calculator) to estimate some of the higher percentiles, although the time period for this data is unclear.

## Cambridge Associates 10-yr TVPI (2004-2013)

    | Vintage | Pooled | Mean | Median | Upper Q | Lower Q | Funds |
    | ------- | ------ | ---- | ------ | ------- | ------- | ----- |
    | 2004    | 1.69   | 1.72 | 1.2    | 1.82    | 0.82    | 63    |
    | 2005    | 1.68   | 1.66 | 1.41   | 2.07    | 0.91    | 61    |
    | 2006    | 1.69   | 1.56 | 1.59   | 1.95    | 0.75    | 78    |
    | 2007    | 2.29   | 2.38 | 1.76   | 2.93    | 1.31    | 68    |
    | 2008    | 1.77   | 1.71 | 1.4    | 2.21    | 1.09    | 64    |
    | 2009    | 2.1    | 2.12 | 1.75   | 2.46    | 1.3     | 23    |
    | 2010    | 3.21   | 2.8  | 2.12   | 3.41    | 1.41    | 48    |
    | 2011    | 2.48   | 2.26 | 1.9    | 2.71    | 1.39    | 44    |
    | 2012    | 2.21   | 2.48 | 1.73   | 2.37    | 1.35    | 55    |
    | 2013    | 2.02   | 2.01 | 1.81   | 2.26    | 1.34    | 59    |
    | Average | 2.11   | 2.07 | 1.67   | 2.42    | 1.17    | 56    |

## Angel List Fund Performance Calculator (April 2025)

    | Percentile | Net IRR |
    | ---------- | ------- |
    | 90th       | 35%     |
    | 95th       | 40%     |
    | 99th       | 55%     |

## Modelling assumptions

- **One cheque per company, no follow-on.**  
  Each of the 24 portfolio companies receives a single initial investment. This keeps the exercise focused on portfolio‐level dispersion rather than reserve strategy.

- **Net-to-LP multiples.**  
  All TVPIs are _after_ a 20 % carry and 15 % lifetime management fees (≈ 2 % per year for 7–8 years). Fees are treated as an upfront reduction of committed capital.

- **Capital-call cadence.**  
  LP capital is called evenly over the first four years (25 % in years 0-3). This mirrors typical early-stage fund pacing.

- **Liquidity timing.**  
  For simplicity we assume the fund’s net multiple is realised at the end of year 7. This is encoded directly in the IRR shortcut `(IRR ≈ TVPI^(1/7) − 1)`, so no explicit exit-year sampling is performed in the final Gamma model.

- **Return distribution.**  
  Rather than simulate deal-by-deal outcomes, we model the _fund’s_ total performance as a single draw from a **Gamma(α = 2.0, β = 1.1)** distribution.

- **IRR proxy.**  
  To give readers an intuitive sense of performance, an approximate IRR is
  derived by assuming the net multiple realises entirely in year 7 while capital
  is drawn over years 0-3. The closed-form shortcut is  
  `IRR ≈ TVPI^(1/7) − 1`.

- **Reproducibility.**  
  All random draws use a fixed NumPy RNG seed (`2025`), so running the notebook
  on any machine will reproduce the exact percentiles and histogram shown.

## Simulated Results

    | Percentile   | Net TVPI   | IRR (approx)   |
    |--------------|------------|----------------|
    | 25th         | 1.07×      | 1.0%           |
    | 50th         | 1.89×      | 9.5%           |
    | 75th         | 3.01×      | 17.1%          |
    | 90th         | 4.27×      | 23.0%          |
    | 95th         | 5.28×      | 26.8%          |
    | 99th         | 7.27×      | 32.8%          |
    | Mean         | 2.22×      | 8.5%           |

![](/assets/simulation_gamma_distribution.png)

## Code

```python
# =============================================================================
# Calibrated Gamma TVPI Simulator for Venture Funds
# -----------------------------------------------------------------------------
# This notebook cell is fully self‑contained.  It:
#
#   1) Defines *one* set of gamma parameters (shape α, scale β) that were chosen
#      to match target percentile bands for venture‑fund TVPI:
#
#          25 th: 1 ‑ 1.5 ×
#          50 th: 1.75 ‑ 2.25 ×
#          75 th: 2.5 ‑ 3 ×
#          90 th: 4 ‑ 6 ×
#          95 th: 5 ‑ 8 ×
#          99 th: 6 ‑ 10 ×
#
#   2) Draws N simulated fund TVPIs from that gamma distribution.
#
#   3) Converts those TVPIs into a *rough* IRR proxy by assuming:
#        • capital is called evenly in years 0‑3,
#        • everything is distributed in year 7.
#      (This matches the “TVPI → IRR” shortcut used earlier.)
#
#   4) Prints a Markdown table of key percentiles + the mean.
#
#   5) Plots a histogram with the inter‑quartile band and median marker.
#
# You can copy‑paste this cell unchanged into a blog post or notebook.  To
# tweak the shape of the distribution, modify the ALPHA / BETA constants.
# =============================================================================

import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import tabulate

# --------------------------- 1. Gamma parameters -----------------------------
# These values were selected by hand to satisfy the percentile targets above.
ALPHA = 2.0          # shape parameter  (k > 0)
BETA  = 1.1          # scale parameter  (θ > 0)

# Number of Monte‑Carlo funds to simulate. 8k is more than enough for smoothness
N_FUNDS = 8_000

# RNG seed for reproducibility in published material
rng = np.random.default_rng(seed=2025)

# --------------------------- 2. Simulate TVPI --------------------------------
# Draw TVPI multiples directly from the gamma distribution: Gamma(k=α, θ=β).
# Note: In numpy's parameterisation, scale = β (same as scipy.stats.gamma).
tvpi = rng.gamma(shape=ALPHA, scale=BETA, size=N_FUNDS)

# --------------------------- 3. Approximate IRR ------------------------------
# Very simple proxy: assume each fund’s net TVPI is realised in a single cash
# flow at year 7, while cash is called evenly over years 0‑3.
#
# If TVPI = M, then the multiple on *invested* capital is M.  IRR ≈ (M)^(1/7)-1
irr = (tvpi ** (1 / 7) - 1) * 100      # convert to percentage

# --------------------------- 4. Markdown table -------------------------------
percentiles = [25, 50, 75, 90, 95, 99]
rows = [
    [f"{p}th", f"{np.percentile(tvpi, p):.2f}×", f"{np.percentile(irr, p):.1f}%"]
    for p in percentiles
]
rows.append(["Mean", f"{tvpi.mean():.2f}×", f"{irr.mean():.1f}%"])

print("### Gamma distribution parameters")
print(f"shape (α) = {ALPHA:.2f}, scale (β) = {BETA:.2f}\n")

print("### Simulated Fund Results (Markdown)\n")
print(
    tabulate.tabulate(
        rows, headers=["Percentile", "Net TVPI", "IRR (approx)"], tablefmt="github"
    )
)

# --------------------------- 5. Histogram plot -------------------------------
q25, q50, q75 = np.percentile(tvpi, [25, 50, 75])

plt.figure(figsize=(10, 6))
plt.hist(tvpi, bins=60, density=True, histtype="step", lw=1.4, label="Simulated TVPI")
plt.axvspan(q25, q75, alpha=0.15, label="IQR (25‑75 %)")
plt.axvline(
    q50, ls="--", lw=1.2, label=f"Median {q50:.2f}×", color="tab:orange"
)
plt.xlabel("Net TVPI (LP multiple)")
plt.ylabel("Density")
plt.title(f"VC Fund TVPI Distribution – Gamma(α={ALPHA}, β={BETA})")
plt.legend()
plt.tight_layout()
plt.show()

```

---
layout: post
title: "Portfolio Simulator"
author: Ivan Bercovich
date: 2023-10-21 01:01:01 -0700
categories:
---

This document is intended to help those interested in venture capital reason about expected fund-level returns. All multiples are **net to LPs** (i.e. after fees and 20 % carry) unless noted. I wrote this originally in 2023, and updated it in April 2025 with about 60 min of vibe coding.

I took data from [this 2020 report](https://www.cambridgeassociates.com/wp-content/uploads/2020/07/WEB-2020-Q1-USVC-Benchmark-Book.pdf) (page 14), and filtered it for the 10 year period between 2004 and 2013. I chose that period because the vintages surrounding the internet bubble show unusually high volatility, and discarded years closer to 2020 given that it takes about 7 years for the TVPI to stabilize. I also used [Angel List](https://www.angellist.com/funds-performance-calculator) to estimate some of the higher percentiles, although the time period for this data is unclear.

### TL;DR

- Median net TVPI lands ≈ 1.6× (slightly conservative vs Cambridge).
- Upper tail preserves the “dragon” effect: 95 th percentile ≈ 6×, 99 th ≈ 8×.
- Converting those payouts into staggered cash flows puts the 90 th–95 th **IRR** band in the low-30s %, matching AngelList’s live data.

---

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

### Core assumptions

- **Fund size**: $50 M — typical seed/Series A vehicle
- **Fee load**: 15 % total (≈ 2 % per year for 7–8 yrs, paid up-front)
- **Carry**: 20 % — standard GP promote
- **Initial cheques**: 28 equal-sized investments, no follow-ons — simplifies dispersion math
- **Outcome buckets**: 40 % 0× · 30 % 1× · 25 % U(3–5×) · 4 % U(10–20×) · 1 % U(50–200×) — mirrors historical deal stats and keeps the 95th percentile near 6×
- **Capital calls**: 25 % of committed capital in each of years 0-3 — matches typical pacing
- **Exit timing**: each company exits once, _uniformly_ between years 4-10 — spreads cash flows for a realistic IRR
- **IRR calculation**: true cash-flow schedule solved with `numpy_financial.irr` — no midpoint shortcuts
- **Reproducibility**: fixed NumPy RNG seed `2025`; 3 500 simulated funds — copy-paste repeatability

## Simulated Results

    | Percentile | MC TVPI | Gamma TVPI | MC IRR % | Gamma IRR % |
    | ---------- | ------- | ---------- | -------- | ----------- |
    | 25th       | 1.26×   | 1.08×      | 3.5%     | 1.1%        |
    | 50th       | 1.61×   | 1.90×      | 7.8%     | 10.0%       |
    | 75th       | 2.56×   | 3.14×      | 17.0%    | 19.6%       |
    | 90th       | 5.15×   | 4.55×      | 29.8%    | 30.1%       |
    | 95th       | 6.02×   | 5.70×      | 41.5%    | 38.3%       |

![](/assets/portfolio_simulation_fig.png)

We fit a Gamma distribution—specifically Γ(k ≈ 1.76, θ ≈ 1.33)—to the Monte-Carlo TVPI sample after the simulation finishes. Overlaying this analytic curve serves two purposes: first, it provides a quick visual check that the simulated histogram has the expected shape, and second, it gives readers a neat closed-form PDF and CDF they can drop into their own spreadsheets without rerunning thousands of Monte-Carlo draws.

## Code

```python
# =============================================================================
#  Monte-Carlo Venture Fund Simulator – “Best-Fit” Parameter Set
#  ---------------------------------------------------------------------------
#  * Generates N_FUNDS simulated net-to-LP TVPI multiples (one per fund)
#  * Computes an IRR for each fund using an explicit cash-flow schedule:
#       –25 % capital calls in years 0-3
#        Single lump-sum distribution in a random exit year U(4, 10)
#  * Fits a Gamma distribution to the TVPI sample for analytical comparison
#  * Prints a tidy percentile table (TVPI + IRR) and overlays the Gamma PDF
#
#  Author : Ivan Bercovich (updated April 2025)
#  License: MIT
# =============================================================================

import numpy as np
import numpy_financial as npf          # only for IRR
import pandas as pd
import matplotlib.pyplot as plt
import math

# --------------------------- 1. Global settings ------------------------------
SEED        = 2025          # deterministic RNG seed for reproducibility
N_FUNDS     = 3_500         # number of Monte-Carlo funds to simulate
N_INVEST    = 28            # *equal-sized* first cheques (no follow-ons)

# Outcome-bucket probabilities
P_FAIL  = 0.40              # 0× return
P_ONE   = 0.30              # exactly 1×
P_TEN   = 0.04              # 10-20×
P_HUNDO = 0.01              # 50-200×
P_MID   = 1 - (P_FAIL + P_ONE + P_TEN + P_HUNDO)  # 1-5× bucket
MID_LOW = 3.0               # lower edge of 1-5× range  (draw U(3, 5))

# Economics
MGMT_FEE = 0.15             # lifetime management fees, taken up-front
CARRY    = 0.20             # carried-interest on profits after fees

# --------------------------- 2. Helper functions -----------------------------
def simulate_fund_tvpi(rng: np.random.Generator) -> float:
    """
    Simulate a *single* fund’s net-to-LP TVPI.

    Steps
    -----
    1.  Draw an outcome bucket for each initial cheque.
    2.  Convert bucket → exit multiple using simple uniforms.
    3.  Average across all cheques ⇒ gross multiple.
    4.  Apply fees + carry to obtain net TVPI.

    Returns
    -------
    float : Net multiple of distributed / committed capital.
    """
    # 2.1 Draw bucket index for each cheque
    buckets = rng.choice(
        5,
        size=N_INVEST,
        p=[P_FAIL, P_ONE, P_MID, P_TEN, P_HUNDO]
    )

    # 2.2 Map bucket → multiple
    m = np.zeros(N_INVEST)               # default 0× for failures
    m[buckets == 1] = 1.0
    m[buckets == 2] = rng.uniform(MID_LOW, 5.0, (buckets == 2).sum())
    m[buckets == 3] = rng.uniform(10.0,   20.0, (buckets == 3).sum())
    m[buckets == 4] = rng.uniform(50.0,  200.0, (buckets == 4).sum())

    gross = m.mean()                     # equal cheque sizes ⇒ simple mean

    # 2.3 Convert gross → net
    #     LPs pay management fees first, then GP takes carry on profits
    net = (1 - MGMT_FEE) * (1 + (1 - CARRY) * (gross - 1))
    return net


def fund_irr(tvpi: float, exit_year: int) -> float:
    """
    Compute fund-level IRR given:
      tvpi      – net multiple (distributed / committed)
      exit_year – single lump-sum distribution year (≥4)

    Capital calls are –25 % in each of years 0-3.
    """
    calls      = [-0.25] * 4                 # years 0-3
    dist_block = [0] * (exit_year - 3)       # zeros until exit
    dist_block.append(tvpi)                  # lump-sum distribution
    return npf.irr(calls + dist_block)


# --------------------------- 3. Simulation loop ------------------------------
rng = np.random.default_rng(SEED)

tvpi_mc  = np.empty(N_FUNDS)
irr_mc   = np.empty(N_FUNDS)

for i in range(N_FUNDS):
    tvpi_mc[i] = simulate_fund_tvpi(rng)
    exit_year  = rng.integers(4, 11)             # uniform 4-10 inclusive
    irr_mc[i]  = fund_irr(tvpi_mc[i], exit_year) * 100  # convert to %

# --------------------------- 4. Fit a Gamma distribution ---------------------
# Moment-matching: shape k = μ² / σ²,  scale θ = σ² / μ
mu, var = tvpi_mc.mean(), tvpi_mc.var()
shape_g, scale_g = mu**2 / var, var / mu

tvpi_gamma = rng.gamma(shape_g, scale_g, N_FUNDS)
irr_gamma  = np.array([
    fund_irr(m, yr) * 100
    for m, yr in zip(tvpi_gamma, rng.integers(4, 11, N_FUNDS))
])

# --------------------------- 5. Summarise results ----------------------------
percentiles = [25, 50, 75, 90, 95, 99]
table = pd.DataFrame({
    "Percentile":  [f"{p}th" for p in percentiles],
    "MC TVPI":     np.round(np.percentile(tvpi_mc,  percentiles), 2),
    "Gamma TVPI":  np.round(np.percentile(tvpi_gamma, percentiles), 2),
    "MC IRR %":    np.round(np.percentile(irr_mc,   percentiles), 1),
    "Gamma IRR %": np.round(np.percentile(irr_gamma,percentiles), 1),
})

print("\n=== Percentile comparison: Monte-Carlo vs fitted Gamma ===")
print(table.to_string(index=False))

# --------------------------- 6. Visualise ------------------------------------
x = np.linspace(0, tvpi_mc.max() * 1.1, 500)
pdf_gamma = (x**(shape_g - 1) * np.exp(-x / scale_g)) / (
    math.gamma(shape_g) * scale_g**shape_g
)

plt.figure(figsize=(9, 5))
plt.hist(tvpi_mc, bins=60, density=True, histtype="step", lw=1.25,
         label="Monte-Carlo TVPI")
plt.plot(x, pdf_gamma, lw=1.4,
         label=f"Gamma fit k={shape_g:.2f}, θ={scale_g:.2f}")
plt.xlabel("Net TVPI (LP multiple)")
plt.ylabel("Density")
plt.title("Monte-Carlo vs fitted Gamma distribution")
plt.legend()
plt.tight_layout()
plt.show()
```

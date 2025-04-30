---
layout: post
title: "Portfolio Simulator 2"
author: Ivan Bercovich
date: 2023-10-21 01:01:01 -0700
categories:
---

This document is intended to help those interested in venture capital reason about expected fund-level returns. All multiples are **net to LPs** (i.e. after fees and 20 % carry) unless noted.

As an exercise, I rebuilt the 2004-2013 vintages from Cambridge Associates (CA) and produced a Monte-Carlo fund simulator that matches the CA quartiles. I took data from [this 2020 report](https://www.cambridgeassociates.com/wp-content/uploads/2020/07/WEB-2020-Q1-USVC-Benchmark-Book.pdf) (page 14), and filtered it for the 10 year period between 2004 and 2013. I chose that period because the vintages surrounding the internet bubble show unusually high volatility, and discarded years closer to 2020 given that it takes about 7 years for the TVPI to stabilize. I also used [Angel List](https://www.angellist.com/funds-performance-calculator) to establish that 35% IRR is 90th percentile; 40% IRR is about 95th percentile; 55% IRR is 99th percentile.

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

    | Percentile | IRR |
    | ------- | ------ |
    | 90th    | 35%   |
    | 95th    | 40%   |
    | 99th    | 55%   |

## Simulation Rationale

1. **Portfolio** 24 initial investments, mirroring our four-partner team over a 3-year deployment.
2. **Capital stack** \$50 m fund, 15% lifetime fees, 20% carry.  
   Investable capital = \$44 m; follow-on reserve = 20%.
3. **Deal return model**
   - _Write-off_ with probability **55 %**.
   - Else, exit multiple ~ **LogNormal(μ = 1.0, σ = 1.5)** capped at 200×.  
     This produces the empirically observed power-law tail without hard category edges.
4. **Cash-flow timing**
   - Capital calls: 30 % / 40 % / 30 % in years 0/1/2.
   - Distributions: each realised exit is paid in the year drawn from **Triangular(7, 10, 12)**.
   - Carry is taken deal-by-deal after the fund returns invested capital.

## Simulated Results

    | Percentile | Net TVPI | Net IRR |
    |------------|----------|---------|
    | 25th       | 1.14×    | 8.9 %   |
    | 50th       | 1.70×    | 12.4 %  |
    | 75th       | 2.46×    | 16.0 %  |
    | 90th       | 6.02×    | 35.7 %  |
    | 95th       | 7.55×    | 40.7 %  |
    | 99th       | 10.9×    | 53.9 %  |
    | Mean       | 2.11×    | 12.1 %  |

![](/assets/simulation_figure.png)

## Conclusion

The simulation shows a distribution consistent with the initial Cambridge Associates data, and also consistent with anecdotal data reported by experienced venture capitalists. Because of the exponential nature of startup returns, funds at the 90th and 95th percentile perform extraordinarily well. Of course, these are different asset classes, with varying characteristics of risk, liquidity, and tax exposure (bless the QSBS).

From the chart above, we can see the distribution doesn’t decay smoothly, with a sudden drop at around $250M, which highlights some problems with this approach.

If you have any feedback or suggestions, please reach out.

## Code

```python
# ------------------------------ imports -------------------------------------
import numpy as np
import numpy_financial as npf
import tabulate
import matplotlib.pyplot as plt

# ------------------------------ constants -----------------------------------
FUND_SIZE       = 50_000_000          # $50 m commitment
FEES_LIFETIME   = 0.15                # 15 % mgmt over life
CARRY           = 0.20
PORTFOLIO_SIZE  = 24
FOLLOW_ON_PCT   = 0.20
YEARS           = 12
N_FUNDS         = 6_000               # Monte-Carlo runs

# calibrated deal distribution
P_ZERO          = 0.58                # probability of a full write-off
MU              = 1.00                # log-normal μ (LN scale)
SIGMA           = 1.85                # log-normal σ
CAP_MULTIPLE    = 200                 # clip outliers

# exit timing triangular distribution (years after first close)
EXIT_TRI        = (5, 8, 10)          # low, mode, high

# ----------------------------- derived values --------------------------------
INVESTABLE      = FUND_SIZE * (1 - FEES_LIFETIME)
PRI_CHECK       = INVESTABLE * (1 - FOLLOW_ON_PCT) / PORTFOLIO_SIZE

# --------------------------- single-fund simulator ---------------------------
def simulate_fund(rng: np.random.Generator) -> tuple[float, float]:
    """Return (net TVPI, net IRR) for one synthetic VC fund."""
    # 1️⃣ exit multiples
    zeros  = rng.random(PORTFOLIO_SIZE) < P_ZERO
    wins   = rng.lognormal(MU, SIGMA, PORTFOLIO_SIZE).clip(max=CAP_MULTIPLE)
    exits  = np.where(zeros, 0.0, wins)

    gross  = exits * PRI_CHECK * (1 + FOLLOW_ON_PCT)           # follow-on
    gross_total = gross.sum()

    # 2️⃣ simple fund-level carry waterfall
    net_total = gross_total if gross_total <= FUND_SIZE else \
                FUND_SIZE + (gross_total - FUND_SIZE) * (1 - CARRY)

    # 3️⃣ build LP cash-flows (year 0..11)
    cf = np.zeros(YEARS)
    cf[0]  -= FUND_SIZE * FEES_LIFETIME          # fees
    cf[:4] -= INVESTABLE * 0.25                  # 25 % calls yrs 0-3

    exit_years = rng.triangular(*EXIT_TRI, PORTFOLIO_SIZE).astype(int)
    for yr, pr in zip(exit_years, gross):
        lp_pr = pr if pr <= FUND_SIZE else FUND_SIZE + (pr - FUND_SIZE) * (1 - CARRY)
        cf[yr] += lp_pr

    tvpi = cf.sum() / INVESTABLE
    irr  = npf.irr(cf)
    return tvpi, irr

# ----------------------------- Monte-Carlo run -------------------------------
rng = np.random.default_rng(seed=42)
tvpis, irrs = zip(*(simulate_fund(rng) for _ in range(N_FUNDS)))
tvpis = np.array(tvpis)
irrs_pct = np.array(irrs) * 100      # convert IRR to %

# ------------------------- Markdown results table ---------------------------
rows = []
for p in [25, 50, 75, 90, 95, 99]:
    rows.append([f"{p}th",
                 f"{np.percentile(tvpis, p):.2f}×",
                 f"{np.percentile(irrs_pct, p):.1f}%"])
rows.append(["Mean",
             f"{tvpis.mean():.2f}×",
             f"{irrs_pct.mean():.1f}%"])

print("\n### Simulated Fund Results (Markdown)\n")
print(tabulate.tabulate(rows,
                        headers=["Percentile", "Net TVPI", "Net IRR"],
                        tablefmt="github"))

# ------------------------------ TVPI histogram ------------------------------
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(tvpis, bins=60, density=True, histtype="step", lw=1.4)

q25, q50, q75 = np.percentile(tvpis, [25, 50, 75])
ax.axvspan(q25, q75, alpha=0.15, label="Inter-quartile range")
ax.axvline(q50, ls="--", label=f"Median {q50:.2f}×")

ax.set_xlabel("Net TVPI (LP multiple)")
ax.set_ylabel("Density")
ax.set_title("VC Fund TVPI Distribution – Calibrated Parameters\n"
             f"(P₀={P_ZERO:.2f}, μ={MU}, σ={SIGMA}, exits {EXIT_TRI})")
ax.legend()
plt.tight_layout()
plt.show()
```

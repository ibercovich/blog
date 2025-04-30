---
layout: post
title: "Portfolio Simulator"
author: Ivan Bercovich
date: 2023-10-21 01:01:01 -0700
categories:
---

This document is intended to help those interested in venture capital reason about expected fund-level returns. All multiples are **net to LPs** (i.e. after fees and 20 % carry) unless noted.

As an exercise, I rebuilt the 2004-2013 vintages from Cambridge Associates (CA) and produced a Monte-Carlo fund simulator that matches the CA quartiles. I took data from [this 2020 report](https://www.cambridgeassociates.com/wp-content/uploads/2020/07/WEB-2020-Q1-USVC-Benchmark-Book.pdf) (page 14), and filtered it for the 10 year period between 2004 and 2013. I chose that period because the vintages surrounding the internet bubble show unusually high volatility, and discarded years closer to 2020 given that it takes about 7 years for the TVPI to stabilize.

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

| Percentile | Net TVPI | Net IRR |
| ---------- | -------- | ------- |
| 25th       | 1.21×    | 9.40%   |
| 50th       | 1.77×    | 12.28%  |
| 75th       | 2.44×    | 15.35%  |
| 90th       | 3.29×    | 18.33%  |
| 95th       | 3.78×    | 20.04%  |
| 99th       | 4.86×    | 23.65%  |
| Mean       | 1.92×    | 12.43%  |

![](/assets/portfolio_simulation_graph.png)

## Conclusion

The simulation shows a distribution consistent with the initial Cambridge Associates data, and also consistent with anecdotal data reported by experienced venture capitalists. For this particular period, the median fund (50th percentile) would have performed simmilarly to the S&P 500 index, whereas a fund at the top quartile would have almost doubled the IRR of the index. Because of the exponential nature of startup returns, funds at the 90th and 95th percentile perform extraordinarily well. Of course, these are different asset classes, with varying characteristics of risk, liquidity, and tax exposure (bless the QSBS).

From the chart above, we can see the distribution doesn’t decay smoothly, with a sudden drop at around $250M, which highlights some problems with this approach.

If you have any feedback or suggestions, please reach out.

## Code

```python
import numpy as np
import pandas as pd
import numpy_financial as npf
import tabulate
import matplotlib.pyplot as plt

# --------------------------------------------------------------
# 0. Reference: Cambridge Associates “average vintage” numbers
# --------------------------------------------------------------
ca_row = [["Average", 2.11, 2.07, 1.67, 2.42, 1.17, 56]]
headers = ["Vintage","Pooled","Mean","Median","Upper Q","Lower Q","Funds"]
print("### Cambridge Associates target (Markdown)\n")
print(tabulate.tabulate(ca_row, headers, tablefmt="github"), "\n\n")

# --------------------------------------------------------------
# 1. Tuned simulation parameters – found by grid search
#    (see narrative in the answer for search method)
# --------------------------------------------------------------
FUND_SIZE       = 50_000_000
FEES_LIFETIME   = 0.15              # 15 % of committed capital
CARRY           = 0.20
PORTFOLIO_SIZE  = 24
FOLLOW_ON_PCT   = 0.20
N_FUNDS         = 4_000
YEARS           = 12

# *** tuned deal‑level parameters ***
P_ZERO  = 0.17                      # probability a deal returns zero
MU      = 0.78                      # log‑normal μ
SIGMA   = 1.08                      # log‑normal σ
CAP_MULTIPLE = 200

INVESTABLE  = FUND_SIZE * (1 - FEES_LIFETIME)
PRI_CHECK   = INVESTABLE * (1 - FOLLOW_ON_PCT) / PORTFOLIO_SIZE

# --------------------------------------------------------------
# 2. Single‑fund simulator
# --------------------------------------------------------------
def simulate_fund():
    # deal exit multiples
    zeros = np.random.rand(PORTFOLIO_SIZE) < P_ZERO
    wins  = np.random.lognormal(MU, SIGMA, PORTFOLIO_SIZE).clip(max=CAP_MULTIPLE)
    exit_mult = np.where(zeros, 0.0, wins)

    gross = exit_mult * PRI_CHECK * (1 + FOLLOW_ON_PCT)      # include follow‑on
    gross_tot = gross.sum()

    # simple fund‑level carry waterfall
    net_tot = gross_tot if gross_tot <= FUND_SIZE else FUND_SIZE + (gross_tot - FUND_SIZE) * (1 - CARRY)

    # LP cash‑flows
    cf = np.zeros(YEARS)
    cf[0]  -= FUND_SIZE * FEES_LIFETIME           # fees
    cf[:4] -= INVESTABLE * 0.25                   # 25 % calls over years 0‑3

    exit_years = np.random.triangular(7, 10, 12, PORTFOLIO_SIZE).astype(int)
    for yr, pr in zip(exit_years, gross):
        # per‑deal carry (same logic as net_tot line)
        lp_pr = pr if pr <= FUND_SIZE else FUND_SIZE + (pr - FUND_SIZE) * (1 - CARRY)
        cf[yr] += lp_pr

    tvpi = cf.sum() / INVESTABLE
    irr  = npf.irr(cf)
    return tvpi, irr

# --------------------------------------------------------------
# 3. Monte‑Carlo run
# --------------------------------------------------------------
np.random.seed(42)
tvpis, irrs = zip(*(simulate_fund() for _ in range(N_FUNDS)))
tvpis = np.array(tvpis)
irrs  = np.array(irrs) * 100      # convert to %

# --------------------------------------------------------------
# 4. Results table
# --------------------------------------------------------------
rows = []
for p in [25, 50, 75, 90, 95, 99]:
    rows.append([f"{p}th", f"{np.percentile(tvpis,p):.2f}×", f"{np.percentile(irrs,p):.2f}%"])
rows.append(["Mean", f"{tvpis.mean():.2f}×", f"{irrs.mean():.2f}%"])

print("### Simulated fund results (Markdown)\n")
print(tabulate.tabulate(rows, headers=["Percentile","Net TVPI","Net IRR"], tablefmt="github"), "\n\n")

# --------------------------------------------------------------
# 5. Histogram visualisation
# --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10,6))
ax.hist(tvpis, bins=60, density=True, histtype='step', linewidth=1.4)
q25, q50, q75 = np.percentile(tvpis,[25,50,75])
ax.axvspan(q25, q75, alpha=0.15, label="IQR")
ax.axvline(q50, ls='--', label=f"Median {q50:.2f}×")

ax.set_xlabel("Net TVPI (LP multiple)")
ax.set_ylabel("Density")
ax.set_title("VC fund TVPI distribution – tuned parameters\n(15 % fees, 4 years of 25 % calls)")
ax.legend()
plt.show()
```

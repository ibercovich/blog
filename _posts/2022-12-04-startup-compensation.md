---
layout: post
title:  "Startup Compensation"
author: Ivan Bercovich
date:   2022-12-03 01:01:01 -0700
categories:
---

In the startup world, many conversations stall while discussing compensation. This is unsurprising, given that the upside is composed of cash, stock options, growth prospects, and possibly a bespoke role. As an investor, I find myself stepping in as the matchmaker to overcome this final hurdle and get to a mutually agreed offer. To make this process more repeatable, I have come up with a simple framework to facilitate compensation discussions.

## Framework ##

The following steps should be followed by both parties and then used to reach a middle ground. First, we define some input variables.

**Cash Equivalent**: how much should the person get paid if it was 100% cash (or cash + publicly traded shares with some margin of error for the latter). It’s important to be as realistic as possible here. For the candidate, the best proxy is current salary or total cash salary from other offers. For employers, use something like Levels.fyi to get a sense of what large public companies are paying for a role. Also keep in mind both the compensation for the role as defined (e.g. engineer with 3 years of experience) and the specific candidate you’re interviewing (e.g. sr. engineer with 7 years of experience), with the latter being more relevant.

**Enterprise Value**: since the offer will include options, it’s important to value the company. The simplest approach is to look at valuation as of the last fundraising event. An appropriate valuation for common shares would be the most recent strike price for options, determined by a third party 409A consultant (usually 25%-50% of preferred value), which takes into account issues like illiquidity. Companies should be prepared to share enough information for prospective candidates to make their assessment, or risk losing savvy individuals.

**Salary**: candidates interested in startups should be prepared to take a significantly lower paycheck. Some companies offer different packages depending on the candidate’s appetite for risk, but most startups tend to lean one way or another, with earlier stages leaning towards more equity. The idea is to shift some degree of compensation to options so that interests are aligned, while allowing for a reasonable lifestyle. It’s not uncommon for a valuable employee to have a higher salary than the founders who are very focused on capital gains.

**Example**: Let's assume someone is making $200k as an engineer at a publicly traded company, taking a combination of $150k cash and $50k public stock RSUs, during stable market conditions, so RSUs ~== cash. They are getting an offer from an early stage startup that includes options over a 4 year vesting period. The candidate is willing to decrease their paycheck to $100k. The company recently raised money at a $25M valuation and their most recent 409A fair market value was $12.5M (50%). All parties are optimisitic about the prospects of the company growing 2x YoY for the next 4 years.




```python
import numpy as np

def get_options(
    cash_equivalent = 200_000,
    vesting_years = 4,
    fmv = 12_500_000,
    exp_growth = 2, #grow 2x YoY for the vesting period
    desired_salary = 100_000,
    ):

    total_equivalent = cash_equivalent * vesting_years
    avg_enterprise_value = (exp_growth**np.arange(vesting_years)).mean()*fmv
    total_cash = desired_salary * vesting_years
    total_option_value = total_equivalent - total_cash
    grant_percentage = (total_option_value / avg_enterprise_value)*100

    return grant_percentage

print(f'{get_options():.2f}%')

```

    0.85%


We can extend our calculation to show a variety of outcomes as we change growth rate assumptions and the candidate's risk tolerance.


```python
import tabulate
data = []
for growth in np.arange(1.5, 3.25, 0.25):
    row = [f'{growth:.2f}x YoY']
    headers = []
    for cash in np.arange(50_000, 200_000, 25_000):
        headers.append(f'${cash/1000:.0f}k')
        col = f'{get_options(desired_salary=cash, exp_growth=growth):.2f}%'
        row.append(col)
    data.append(row)

table = tabulate.tabulate(data, headers=headers)
print(table)
```

               $50k    $75k    $100k    $125k    $150k    $175k
    ---------  ------  ------  -------  -------  -------  -------
    1.50x YoY  2.36%   1.97%   1.58%    1.18%    0.79%    0.39%
    1.75x YoY  1.72%   1.43%   1.15%    0.86%    0.57%    0.29%
    2.00x YoY  1.28%   1.07%   0.85%    0.64%    0.43%    0.21%
    2.25x YoY  0.97%   0.81%   0.65%    0.49%    0.32%    0.16%
    2.50x YoY  0.76%   0.63%   0.50%    0.38%    0.25%    0.13%
    2.75x YoY  0.60%   0.50%   0.40%    0.30%    0.20%    0.10%
    3.00x YoY  0.48%   0.40%   0.32%    0.24%    0.16%    0.08%


## Conclusion ##

That’s basically it. Of course this is an imprecise methodology and participants should make adjustments as warranted by the situation. The candidate might be willing to take the leap in exchange for a higher title or bigger scope– I argue positioning for career growth is far more important than starting compensation.  The company might have reason to believe they will grow faster. The last funding round might have unusual preferences or be led by unsophisticated investors. The founding team might have prior extraordinary success. However, I encourage both parties to keep the calculations as simple as possible, as going much further is likely false precision.

Keep in mind that while compensation is very important, it’s not the only factor at play. For me, most of the value of working at a startup came from being part of the journey and growing with the company, which won’t be captured in the offer. Many people who join a startup dream of doing their own one day, and there is nothing like the real thing to develop the right skills. Likewise for founders, the right early employee can add as much value as a co-founder and be pivotal in the eventual success of the company. So in situations where there is a strong fit and mutual interest, I strongly encourage both parties to overcome hurdles and get to business!

[Feel free to modify this Jupyter Notebook](https://github.com/ibercovich/ibercovich.github.io/blob/master/notebooks/compensation.ipynb)

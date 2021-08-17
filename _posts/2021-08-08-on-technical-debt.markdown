---
layout: post
title:  "On Technical Debt"
author: Ivan Bercovich
date:   2021-08-08 20:08:31 -0700
categories:
---
Code is like cars and buildings. It requires regular upkeep and recurrent care to perform well. But when it comes to software, there isn’t a one-size-fits-all approach. While car maintenance can be broken down into specific line items like tire pressure and oil change, “Technical Debt”  is a catch-all term for a latent risk which is hard to describe or quantify.

This vagueness leads shrewd business leaders to be skeptical of the cries to action from the development team. The devs usually give up on trying to translate their concerns to a more universal language and just wait for the inevitable to happen. And so, sooner or later, the product will suffer an awful bug, serious downtime, data loss, or simply become slow and glitchy. This situation creates an opening for the software team to bargain for time and resources to finally eliminate ALL technical debt.

This rarely leads to a great outcome. Big refactorings often end up becoming a creative endeavor or a quest to add cool new technology, as opposed to a set of well defined, independently valuable, and progressively executed milestones, with concrete and measurable results. Efforts will take far longer than originally planned; subsequent projects will attempt to fix new issues introduced due to major re-architectures. Product development speed will stall and morale will collapse. The CEO has to lead the team to shore navigating through the self-inflicted tech debt storm. In the end, the product will be behind the competition, the improvements to the system will be uncertain, and everyone will be exhausted. And the cycle will likely repeat.

The Path Forward
----------------

Accept Tech Debt as a natural part of doing business
-----------------------------------------------------

The push to deliver customer features as fast as possible and lack of coordination between developers lead to inconsistent architectures that become progressively harder to maintain. This is absolutely inevitable. Moving slower and planning longer would not lead to less technical debt- it would lead to building the wrong product and subsequently dying. And yet, the business skepticism that impedes its resolution is also fully warranted. Leaders should be attentive and listen to concerns from the engineering team, especially those with a reputation for being conservative. Developers should avoid being alarmist. Instead be methodical in identifying opportunities and gain trust from management by articulating debt in terms of business impact and delivering a sequence of moderately sized wins.

Couple debt reduction with customer value
-----------------------------------------

Don’t think of technical debt as something that has to be done as a standalone sprint. Instead, make every project include a certain percentage of work allocated to the betterment of the system. In my experience 20% reserved to codebase enhancements and 80% dedicated to customer value is the right balance. This breakdown won’t only encourage a constant flow of improvements, but it will also force piecemeal execution. For example, instead of having an epic titled “move front-end to react”, there should be an epic called “improved search capabilities”, which includes integrating elastic search as well as moving the search-specific UI to react components. The engineering team might claim that moving the entire front-end to react at once will be more efficient, and there are good arguments to support that line of thinking, but this is an area where theory breaks down when confronted with reality due to unknown unknowns.

Target concrete KPIs
--------------------

Translate technical debt objectives into measurable quantities, and build instrumentation to make those KPIs easily accessible in real time. If the app is slow, start measuring front and backend performance, identify the highest volume and slowest requests, and methodically tackle bottlenecks until speed improves. Too often, teams make the leap from “our backend is slow” to “we need a new trendy database”, only to forget the initial intent and end up with an equally sluggish app on a fancy and poorly documented DB. Even worse, the team will feel accomplished because a proposed solution became the core objective. A good way to avoid this hazard is to take bets on which solutions will bring the most ROI for a particular metric, build a leaderboard and celebrate those people who had the biggest impact. Be skeptical of technical debt that can’t be measured, often things that end in “-ility” like readability or maintainability. It’s always best to start with the most measurable improvements as a testing ground for more abstract objectives.

The codebase is not the enemy
-----------------------------

Promote a culture of appreciation for the current architecture, or as stated in Amazon’s engineering principles, “respect what came before”. It’s too easy to hate on the current codebase, especially by those who didn’t write it. But the devil truly is in the details. Channel the energy of those who show dissatisfaction into identifying measurable opportunities and proposing high-ROI solutions. Likewise, once an opportunity has been identified, consider assigning it to someone on the conservative side, who is afraid of change. Having a well-balanced culture is critical in building a successful and durable application. When dissatisfaction can’t be harnessed, it just becomes hyperbolic negativity, which destroys team morale. If someone can’t reconcile their personal standards with the state of the codebase, it’s best if they move onto greener pastures.

DO NOT DO A FULL REWRITE
------------------------

Just don’t. Count to 2^100. Seriously, STOP!

Absolutely no Rewrite + Relaunch
---------------------------------

If you do make the mistake of entertaining a full rewrite or major technical debt projects, for the love of Claude Shannon please don’t use that opportunity to redesign the product or add new features alongside a marketing campaign! It’s so tempting to squeeze those long awaited features into a full rewrite. Afterall, if the entire application is being written from scratch, why not make it perfect? Stop right there! The current set of features and the user experience that goes with them, might be outdated, but has evolved through battletesting. Products are the result of iteration, and thinking that a perfect version can be conceived from scratch is just startup heresy. Instead, try to survive the already painful experience of a major architectural change and keep the user experience identical. Other than gains in measurable KPIs like latency, users should be completely unaware that this effort happened at all.

Take full responsibility for migrations
---------------------------------------

One of the worst outcomes of refactoring is when the project is never fully completed and the product ends up needing to support two sets of APIs. It goes without saying that doubling the surface area will carry a proportional increase in bugs, a growing discrepancy in feature parity, and a decrease in product development speed. While this fragmentation can happen due to an incomplete refactor of the codebase, it is more frequently the outcome of eternal migrations. The team thinks switching customers to the new API will be a matter of flipping a switch, but inevitably discovers performance bottlenecks or customer-specific requirements, resulting in a more extended migration which starts with smaller customers and slowly moves up the scale. Another common scenario occurs in organizations with an overpopulation of microservices (that’s for another rant), where a team upgrades an API and assumes that every other team will follow suit. The risk of incomplete migrations is mitigated by making the project owner fully responsible for completion within a given timeframe, even if that means hand holding customers or smokejumping into another team’s codebase.

~~

That summarizes my wisdom in this topic. Easy to say, hard to execute. I wish you good luck in your journey to understand and embrace continuous technical debt reduction.


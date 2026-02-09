---
layout: post
title: The Software Business
author: Ivan Bercovich
date: 2026-02-05T00:00:00.000Z
---

I don't know the future, but I believe most people aren't thinking this AI thing through.

Let's talk about the business of software.

The free market argument for housing affordability is to remove red tape and make it easy to build. There's no need to force developers to include "affordable" units in new projects. The idea is simple: if we build new luxury homes, older luxury homes become cheaper, and middle-class homes cheaper still. As a thought experiment, if a solar flare broke all modern cars, would crappy old beaters become cheaper or more expensive?

It's all about supply and demand.

So, if simple software, like personal apps and internal tools, becomes free, what happens to slightly more sophisticated software? Presumably it becomes cheaper. But where do we draw the line? Five years ago you could build approximately nothing vibecoding. Today, virtually anyone can build an internal tool or personal app. A dedicated vibecoder with enough practice can build a simple SaaS application.

Have we reached the steady state? Where will we be in another five years? Will we have more software or less? Will software be easier to build or harder? Will we have more or fewer people that can build software? What does that mean for the business of selling software?

Furthermore, how many use cases that formerly relied on software can now be solved by an agent doing throwaway work? Do I need a personal financial planning tool, or do I just throw some data into Claude and ask for help?

<blockquote style="margin-left: 2em; padding-left: 1em; border-left: 3px solid #ccc;">
  <p>You tell the agent what you want. The agent does it until it gets stuck. You don't know or care how it's doing it, so long as you can trust the results. The agent keeps getting better every 6 months, for free. You don't need to write more software or better prompts. Just keep doing your job and the thing will improve.</p>
  <cite style="font-size: 0.9em;">— <a href="/2025/agents-are-a-generalized-technology">Agents are a Generalized Technology</a></cite>
</blockquote>

I'm not saying I understand the implications for today's large SaaS companies. Software is one component of building a successful business. But today we have organizations whose main value prop is building and selling software. The software is the end. Maybe that will shift to firms more strictly selling solutions to problems, done through software.

Think of a business that sells me a tool to do performance reviews. Are they directly solving a problem? The problem is that I want to promote the best and fire the worst. Do I need software to administer the managerial process of performing reviews? Or do I need an AI that tells me who to promote and who to let go? Do you see the difference? Does Salesforce bring me sales, or is it just software to administer the human process of sales?

In good business relationships, everyone wins. In order to know everyone is benefiting, both parties need to know the value they're getting. With SaaS, the value to the buyer is often unclear. Customers pay per-seat licenses without knowing exactly how much leverage those licenses bring to the business. Meanwhile, SaaS companies have a tremendous amount of visibility into their customers' utility. They know exactly how often every feature of their product is touched by each user at each company, and how users and companies compare. This relative advantage, especially when the buyer is a smaller business, makes it inevitable that SaaS companies will end up capturing more value than their customers.

It's more fair to have metered pricing. You pay for what you use, and both the customer and the provider understand this number. Gasoline and electricity costs are proportionate to usage, and these expenses can be reduced when needed by reducing consumption. In software, hyperscalers offer similar transactions. Many API products charge per unit of work. This is the future, because it's more fair for the customer and it allows consumption to ebb and flow based on business need.

Per-seat pricing is not evil. It's a reasonable way to arrive at a clearing price when the product is a bundle of thousands of actions a user can take in a given month. It's a simple alternative to the false precision of trying to measure the utility of something that is simply too hard to measure.

But AI is going to change the playing field. Businesses will want to pay for results instead of paying for SaaS software that manages the human process which promises to deliver results.

<blockquote style="margin-left: 2em; padding-left: 1em; border-left: 3px solid #ccc;">
  <p>Vertical software has been a way to roughly encode processes into digital machines, so that humans can introduce intelligence into those processes.</p>
  <cite style="font-size: 0.9em;">— <a href="/2025/agents-are-a-generalized-technology">Agents are a Generalized Technology</a></cite>
</blockquote>

With agents, you'll pay for outcomes.

People say, "SaaS has a moat because of total cost of ownership. You need to pay for enterprise-grade security, customer success, and sales, and that scales better across many customers."

Read *The Innovator's Dilemma*. Disruption starts at the bottom. Imagine small businesses developing internal tools. What is most SaaS software if not internal tools? If you have your own tool, does it need to be as secure as a massive company like Salesforce, which is a constant target for hackers? Maybe you use something like ZeroTrust Cloudflare for authentication, and only your team will ever be able to access the endpoint. You just have to gatekeep yourself from the outside world. If you built the tool, do you need customer support?

"But adding features and fixing bugs is going to be hard." Again, don't compare this to enterprise-grade SaaS that needs to support other enterprises, all of which have different requirements. Think of software meant for a single small team with its own needs for a very specific use case. The equivalent of a spreadsheet. Vibe coding can maintain that. And when it gets unwieldy a year later, tell a smarter AI to take all the data from the old product and build a new one.

One of the first things I tell a SaaS founder when they're struggling with bugs and maintenance is to start tracking analytics for every click on every feature and then analyze what is or isn't being used.

I always predict that they'll have a lot of features being used by a tiny fraction of their customers. Even within a feature, there will be a certain config or setting that almost nobody uses. And often, they'll find there are features that actually nobody uses.

Furthermore, on close inspection, they will realize the number of unique users and the level of activity at each customer is lower than they thought.

The point is, it's a reality that enterprise software is complex, has delicate security features, needs to scale, needs to support a lot of use cases, and has been battle-tested for bugs for many years.

But custom software for small teams doesn't need all the features SaaS companies bundle to justify higher prices.

Teams manage hundreds of documents and spreadsheets in their day-to-day business. There's no reason they can't have dozens of neatly defined internal vibe-coded tools to do their jobs.

I'm very long on the infrastructure to run all this, like [Daytona](https://www.daytona.io/). There's going to be infinitely more custom software.

This is just one more force SaaS companies need to contend with. On top of that, software is becoming cheaper to make and easier to migrate across.

<blockquote style="margin-left: 2em; padding-left: 1em; border-left: 3px solid #ccc;">
  <p>AI is eroding the last standing barriers of entry. Trivialization of app production will lead to diminishing returns, and upside will vanish.</p>
  <cite style="font-size: 0.9em;">— <a href="/2025/hard-is-back">Hard is Back</a></cite>
</blockquote>

What else is abundant and easy to substitute? Commodities. What are the gross margins of commodities? SaaS has 70%+ gross margins. Is this sustainable? Why?

The number of software startups going after every vertical will 10x, the price will 1/10th due to competition. It will start with the simpler stuff, but I struggle to see a world where it stops there given how fast code generation is advancing. This has happened before to other industries. Margins compress with competition. It's why free markets are good. And there will be more companies that decide to take technology in-house and vertically integrate. Most companies benefit from using the same software every other company in their industry uses. But some ultra innovative companies, like Tesla, like to own the entire stack to do things their own way. I'm thinking of companies like Waymo.

SaaS has been capturing too much value. We live in a world where everyone has to pay SaaS taxes in order to operate their business. It's a good time for software operators to carefully consider the nature of their transactions and make sure their customers are getting a good deal.

One set of businesses that will thrive will be the ones building the tools agents need to actually solve the problem:

<blockquote style="margin-left: 2em; padding-left: 1em; border-left: 3px solid #ccc;">
  <p>If someone creates a critical tool and integrates it with a frontier LLM to achieve valuable tasks, customers will willingly pay a premium for tokens resold by the tool-builder. But these tools aren't trivial MCP servers executing granular tasks. Instead, they involve large data, complex requirements, high compute needs, distributed systems, and advanced simulations.</p>
  <cite style="font-size: 0.9em;">— <a href="/2025/its-the-tools">It's the Tools</a></cite>
</blockquote>

Software is not dead. It's about to become orders of magnitude larger. What does that mean for the business of software? Does it stay the same? Unlikely.
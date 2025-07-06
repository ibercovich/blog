---
layout: post
title: "NLP Testing Memo (2021)"
author: Ivan Bercovich
date: 2025-07-06 01:01:02 -0700
categories:
---

My first inspiration for an AI company was the project [CheckList](https://github.com/marcotcr/checklist), also a paper, by [Marco Túlio Ribeiro](https://x.com/marcotcr). Ryan and I ended up going in a different direction with Unwrap.ai, but I still attribute my creative drive at the time to this idea.

Here's the memo from **May 2021**.

## Beliefs

**As the AI economy continues to grow, it will create a whole new ecosystem to support AI innovation.** Companies playing in the supporting layers will grow in parallel (e.g. GPUs, humans-in-the-loop/gigsters, compliance, security, etc.). Most of the AI ecosystem will look similar to software (DevOps ⇔ MLOps), and some will be unique (annotation workflows). In particular, general purpose model development is becoming analogous to open source software: large distributed efforts produce important and highly leveraged capabilities, which nevertheless are hard to monetize. As with software, corporate value will largely be concentrated in applications of general models tuned for domain-specific solutions.

**Text as an addressable market is enormous.** We spend most of our working hours interacting with text, both consuming and producing it. Furthermore, language is how we think and make complex decisions. NLP is having its ImageNet-like deep learning moment (especially with the advent of GPT-3), and the next decade is set for extraordinary growth. NLP will eventually penetrate all industries and be pivotal in making important decisions.

For this to happen, NLP models will need to be battle-tested, fair, and robust. While NLP is improving rapidly, we believe the general optimism in the industry has led to the attitude that all problems will be solved with bigger, one-size-fits-most models. We believe this to be insufficient. Ultimately, we believe that in order to capitalize on the NLP revolution, companies will need to invest in domain-specific solutions which will require significant resources in testing and validation.

## Problem

Testing to continuously improve and validate applied NLP models is hard. Most NLP development starts with an open source general purpose model which is then fine tuned and coupled with domain-specific components (models, code, or rules). The problem is that while general purpose benchmarks such as GLUE cover a lot of use cases, testing a domain-specific solution can require a lot of work. Typically, a team will need humans in the loop who are responsible for generating examples and/or annotating failed instances in production. These individuals are closer to domain experts than programming/ML professionals and therefore require a platform on which to perform their job. We seek to develop a human-in-the-loop command center from which this continuous improvement can happen.

### Who Has This Problem?

Customer Profile 1: Legaltech Company
Company uses AI to parse contracts and extract key facts like dates, relevant parties, etc. They update their model often, sometimes multiple times per week. They have two testing methods: i) a set of ‘golden test’ scenarios that are tested every ~5 minutes, which are very basic tasks that are never expected to fail, ii) customer-specific tests where the existing model is run against a new customer’s contracts. For this second testing method, they have an in-house QC/KE team which uses custom-built tooling to annotate errors and provide feedback to the science team. This entire process is the CTO’s “least favorite part of his job” and something that he would be “extremely excited to outsource”. A 3rd party workflow could handle testing new customer data, and perhaps generate synthetic contracts to help improve Lexion’s model even if new customer intake stagnates.

Customer Profile 2: PM at Spotify working on music recommendation
Spotify currently uses NLP to analyze trending articles from the web related to music and identify relevant artists to recommend to Spotify users. We imagine they currently have their own QC team which is continuously validating the model by seeing if it is correctly ranking high-quality new articles that are extremely relevant, and dismissing others that aren’t. Spotify could save money by outsourcing this process using a 3rd party workflow, which helps them generate fictitious articles that specifically test for model robustness and fairness. For example, if you change an article’s artist name from a male to female name, or from an English to Arabic name, does that change the models’ recommendation? Should it?

Customer Profile 2: California Court System
For the 2020 election cycle, Prop 25 was on the ballot which abolished the cash bail business and replaced it with algorithms to make bail decisions. The proposition was rejected, so cash bail remains for now, but it’s only a matter of time until bail decisions (and other similar ones) are made at least with the assistance of algorithms/models, if not entirely so. When the California court system wants to select an NLP model / system to scour court documents, police reports, etc., how do they know which is best? A 3rd party tool should create a fair rubric for analysis, ensure that models are fair and unbiased, and make a recommendation to the court system.

### Evidence of Demand

- [TextAttack](https://github.com/QData/TextAttack)
  - Open-sourced tool for generating adversarial examples for NLP models
  - Started by a number of students at UVA
  - Github repo stats:
    - 1.4k stars, 29 watchers, forked 161 times
- [CheckList](https://github.com/marcotcr/checklist)

  - Open-sourced tool for testing robustness and fairness of NLP models
  - Started by Marco Ribeiro
  - Project won best paper award at Association for Computational Linguistics (ACL) 2020 conference
  - Github stats:
    - 1.3k stars, 27 watchers, forked 123 times

- The European Union proposed sweeping restrictions on AI technologies and applications. What’s new: The executive arm of the 27-nation EU published [draft rules](https://digital-strategy.ec.europa.eu/en/library/proposal-regulation-laying-down-harmonised-rules-artificial-intelligence) that aim to regulate, and in some cases ban, a range of AI systems. The proposal is the first to advance broad controls on the technology by a major international body.

- FTC rules: Section 5 of the FTC Act. The FTC Act prohibits unfair or deceptive practices. That would include the sale or use of – for example – racially biased algorithms. Fair Credit Reporting Act. The FCRA comes into play in certain circumstances where an algorithm is used to deny people employment, housing, credit, insurance, or other benefits. Equal Credit Opportunity Act. The ECOA makes it illegal for a company to use a biased algorithm that results in credit discrimination on the basis of race, color, religion, national origin, sex, marital status, age, or because a person receives public assistance.

## Product Hypothesis

### Phase 1 - “Penetration testing” (consulting) approach

- Customer comes to us with NLP model with example inputs and outputs
- We spend time altering the testing inputs to generate new tests, see which new tests lead to unexpected outputs
- We send customer report with specific inputs that produced bad outputs, with additional examples to test
- We charge on a per test basis

### Phase 2 - Self service approach

- Customer signs up for testing account
- Customers are walked through a workflow to link their model, provide input data, and suggested output
- Our tool alters the input data based on common patterns observed with past customers, we generate new tests and run them against the model
- Customers can view test results, generate more tests, use resulting tests to further train the model, and ask for a more in-depth consulting session to seek our help in interpreting results / improving their model
- We charge a subscription fee for ongoing access to our testing tool

## Market Opportunity

The global NLP market is already massive, and growing quickly. In 2020 it’s an $11.6B market, and expected to triple to $35.1B in the next 6 years for a CAGR of 20.3% (source). This growth is predicated on growing demand for cloud-based NLP solutions as overall costs continue to decrease, ML capabilities are pushed to more devices, and capabilities continue to see significant improvements. This growth has been accelerated by COVID-19, which has increased the need for individuals and organizations to communicate with text as in-person interactions are more difficult and rarer. Additionally, “the services segment is expected to grow at a higher CAGR during the forecast period”.

On LinkedIn, there are currently 90,000 people in the U.S. with experience with NLP, 10,000 of which are actively in an ML role. The top 10 companies/institutions employing these 10,000 people are (in order) Google, Apple, Facebook, Microsoft, LinkedIn, IBM, Capital One, JP Morgan, Walmart, and Adobe.

## AI Strategy?

AI will help us create new tests for our customers' NLP models by using NLP and NLG. Some examples include replacing words with less-popular synonyms to test a model’s perturbation robustness, and rearranging sentences / paragraphs while still maintaining the same intent of the text.

## Key Assumptions

- People will trust a third-party to test their model
- We will be able to scalably test NLP models/use cases by building tooling which can be shared between customers
- A testing product will be easy to integrate into engineering workflow
- Market is mature enough to implement these tools

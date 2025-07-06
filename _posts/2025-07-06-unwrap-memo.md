---
layout: post
title: "Unwrap Memo (May 2021)"
author: Ivan Bercovich
date: 2025-07-06 01:01:02 -0700
categories:
---

This is the original memo for Unwrap.ai

## Beliefs

Over the past decade, with the advance of analytics and data-science, there has been an advent of data-driven decision making in the workplace. Today, most companies have people in analytics related roles across all departments.

While pervasive, this transition has been mostly in the context of quantitative/numerical data, which is easier to analyze using traditional statistical and learning methods. There is still a huge body of relevant information that is unstructured in nature and which can serve to further improve decision-making in data-driven functions or enable the same type of thinking in roles that have traditionally been more qualitative. This opportunity will be best leveraged where modern NLP/ML techniques overlap with large quantities of regularly updating text which is consumed with a high frequency. Examples of these "streams" include customer tickets, email, chat, meeting transcripts, interviews, resumes, contracts, etc.

Among these streams, we believe product feedback is currently under-exploited. At every software organization, multiple teams receive a constant flow of feedback, often in more volume than can realistically be processed. This leads to an incomplete feedback loop, with low response times, valuable team members doing mechanical-turk-like work, and missed product/customer opportunities. Either backlogs continue to grow and become stale, product managers spend hours per week manually sifting through feedback, or, in the worst-case scenario, customers feel unheard and stop submitting feedback altogether.

There is valuable information locked in the corpus of feedback. While some feedback is more valuable than others, nearly all feedback contains some value. For example, a backlog of feedback can help answer questions like 'what parts of my codebase/product are the most problematic?', 'is my current sprint roadmap aligned with the most pressing requests?', 'what teams submit the most requests to my team?', 'does it make sense to work on feature X or feature Y for our next sprint?', and 'what is the most important role to hire for today?'. NLP can help improve all aspects of this lifecycle, by clustering similar feedback together, de-duping similar issues, and identifying trends across multiple feedback sources (e.g. internal bugs and customer support tickets).

## Problem

As we have seen firsthand multiple times, software organizations have too many pieces of feedback and too little time. Feedback has a tendency to pile up, reaching a critical mass that makes it difficult to understand completely. Organizations may then hold 'bug bashes' or 'maintenance days', but these are merely stopgaps to a ceaseless problem. Eventually, people stop checking the feedback, as the amount of content grows out of hand, and valuable feedback begins to fall on deaf ears. This problem isn't a difficult one to solve if given more resources, as it's not difficult for a software engineer or product manager to sift through bugs and categorize, prioritize, and route them. It's simply a resource allocation problem, as engineers' time is often better spent on other problems, and most companies don't dedicate enough time and energy to evaluate their feedback, instead relying on intuition.

### Who Has This Problem?

**Michelle - Product Manager, Amazon Alexa:** As a Product Manager on Alexa, Michelle is responsible for directing her engineering team to the most valuable tasks to make Alexa smarter. Given that Alexa is a popular consumer product with over 40M users, there is a continual stream of helpful feedback on how to improve the product. This feedback has a few different input streams: requests submitted by other team members, high-severity outages to the service, Alexa customer support tickets, bugs submitted by Alexa VPs who notice particular device shortcomings, etc. In total, Michelle has a constant backlog of feedback items numbering in the thousands, with 10+ items added each week. There isn't enough time in the day to sift through all of them on an ongoing basis, so she would like a tool to help her categorize issues into relevant cohorts (e.g. 'sports', 'security', 'language understanding', 'data visualizations', etc.) and merge duplicate issues. She could then better understand these backlog items and direct her team to address the most pressing cohorts.

**Tim - Engineering Manager, Appfolio:** Tim's team receives 30+ customer support tickets each week from users of Appfolio (i.e. property managers). While he likes to review as many as he can each day to keep a pulse on his customers, he simply can't keep up with the never-ending stream. And while Tim occasionally forwards support tickets to the relevant engineer, he'd like to take a more holistic approach. He's looking for a tool that can process all incoming support tickets, group them into helpful buckets, and provide a daily report of the makeup of these issues and see how that's changing over time.

### Evidence of Demand

**Personal experience.** While at Graphiq, the engineering team had a backlog of 500+ bugs and feature requests which always grew. It became this 'black box', where users and other employees submitted valuable feedback, but it was impossible to tease out these insights given how many other issues were also mixed into this data.

At Amazon Alexa, the Graphiq Knowledge team experienced a very similar phenomena. Despite starting with a clean slate after the acquisition, two years later the backlog quickly grew to nearly 1,000 bugs and feature requests. As engineers began to neglect the backlog, the feedback loop between builders and stakeholders broke, leaving no efficient way for helpful product ideas to reach those working on the product.

**Director of Engineering** says each product manager at the company spends 15% of their time sifting through employee and customer requests, and that each team has 400-500 issues in their backlog. He said he personally spends "an enormous amount of time reading and re-reading tickets", and would benefit greatly from a tool that automatically processed the backlog to pull out the most common areas in need of support.

**A product manager with the VA** and works on the Innovation Team, specifically in the Veteran's Mental Health division. Her team's responsibility is looking at Veteran's prescription history and identifying Opioid safety issues. Her team receives ~30 bugs / week, and she spends 25% of her time categorizing them, and determining if each bug is really a bug (some part of the system is not behaving as expected) vs. a feature request (an improvement to the system that is behaving as expected). A tool that classified issues between feature requests and bugs "would be amazing".

## Product Hypothesis

### Phase 1 - Open-Source GitHub Repositories

GitHub has over 30M public repositories, including many large, reputable projects. For nearly every project in an open-sourced repo, they use GitHub Issues to track bugs, feature requests, etc. All of this information is publicly available via APIs and free to access. We plan to build our first demo-able version using this data. The key features of this early product will be:

- Dashboards showing relevant trends for issues over time with various cohort analyses
- Automated categorizer to suggest labels to apply to relevant issues
- Bulk labeling tool to apply labels to issues that meet certain criteria

### Phase 2 - New Feedback Sources, New Features

We'll apply the same product features from Phase 1 to new data sources beyond GitHub. This will include other issue tracking platforms like Jira and Asana. We will also incorporate additional input streams outside of issue trackers, such as customer feedback via ZenDesk and support emails. We'll make it easy for customers to integrate 2-3 of the most popular sources of feedback (most likely GitHub, Jira, and ZenDesk).

Beyond adding new data sources, we'll add new features to better process feedback for customers. This will include:

- A shared ontology across feedback sources. This ensures that tickets from Jira, GitHub, ZenDesk, etc. will have the same labeling nomenclature and structure, so they can easily be organized and compared.
- Alerts when the distribution of feedback categories changes
  Ex: "Alert: tickets from ZenDesk labeled 'database issue' typically make up 15% of total tickets, but now make up 55% of tickets in the past 7 days (n=142)".
- A centralized dashboard to view feedback from different sources, and search for pieces of feedback from different datastores.
  Ex: "Show me issues related to our shopping cart feature."
  Displays 10 tickets from ZenDesk, 6 Jira tickets, and 7 relevant chat transcripts from Intercom

## Market Opportunity

[Sync w/ Jacob on how best to approach this]

Relevant companies:

- Atlassian (makers of Jira)
  - MC: $62B
- Asana
  - MC: $8B
- Trello
  - Acquired in 2017 for $425M

## Go To Market Strategy

### Ideal customer

B2C software organizations with more than 50 employees.

The more feedback a company has to process, the more valuable this product will be. Therefore, a B2C organization is a better buyer than a B2B organization because they will have a larger number of total customers, and more incoming feedback. 50+ employees is another signal for a sufficiently large enough customer base and corpus of feedback.

### Who's the buyer

This depends on the size/type of organization. I view the ideal buyer similar to whoever buys the organization's issue manager software license (e.g. Jira, Asana, etc.). Here are a few hypothetical scenarios:

**Engineering/Product focused organization**
Most of the employees are technical, there is a smaller sales team, and the engineering / product teams set the company vision. For these orgs, the buyer is most likely the CTO, the head of product, or the VP of Engineering.

**Sales/Marketing driven organization**
Most of the employees are non-technical, there is a large sales team, and the sales / business development teams set the company vision. For these orgs, the buyer is most likely the head of sales or head of customer success.

## AI Strategy?

Nearly every customer has mentioned that 'categorization' as their number one request for this product. We plan to lean on AI to help us do a number of 'categorization' tasks, as well as other similar tasks. Some examples include:

- Grouping issues into relevant cohorts
- Designating bugs from feature requests
- Finding duplicate issues
- Prioritizing issues
- Routing issues to the correct assignee

## Key Assumptions

- Most software organizations over 50 employees have large backlogs of underutilized product feedback, and this product feedback is inherently valuable.
- NLP and other ML technologies are now at a place to efficiently extract value from this corpus.
- More efficiently extracting value from this corpus is valuable to companies because it allows them to automate processes that they currently do manually, and it allows them to form a more complete picture of their customer needs, ultimately enabling them to develop a better product.

## Execution Plan

Talk to 20+ potential users of our product and begin to identify common patterns / use cases. Key questions to ask users:

- How does your organization receive incoming feedback?
- Does your team currently have a backlog of feedback that isn't scheduled to be addressed in the near term?
- Do you believe there is value stored in this backlog of feedback?
- How large is your team's current backlog of feedback?
- Outside of additional personnel, what would make it easier to get through this backlog?
- Build working demo based on public GitHub repositories
- Create pitch deck based, share with AI2 and potentially a handful of investors
- Present pitch deck and demo to potential investors

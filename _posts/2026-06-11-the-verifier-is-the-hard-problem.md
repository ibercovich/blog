---
layout: post
title: "The Verifier Is the Hard Problem"
author: Ivan Bercovich
date: 2026-06-11T00:00:00.000Z
---

I've been contributing to Terminal Bench since close to the beginning. A lot of my interest lately has been with reward hacking, specifically how elusive it is. I thought it was an obvious, important issue, and when you talk to people they say, sure, reward hacking is a big deal. But it keeps getting bigger. I think it's a bigger problem than most people thought.

The common take is that higher capabilities will solve it. My take is the opposite: the more capable the models get, the worse the reward hacking gets.

Here's why. We're trying to come up with tasks that are very hard. But what does hard mean? It's a very open-ended question. If you push toward hard, which means a benchmark that no AI can do yet, so you can test where the AIs can get to, then as you approach that frontier you are also approaching a space that is less well defined. And the less well defined the task, the more reward-hackable it is. The feedback loop breaks.

You see it in what people actually submit. A lot of what we get is someone who starts with a prompt that works, and then removes tokens from the prompt until it fails. That's tricky for the AI, but it isn't fundamentally hard. Hard and ill-defined start to look like the same thing, and that's where the reward hacking lives.

## We've run out of the low-hanging fruit

SWE-bench was a really clever way of producing a benchmark. And everybody is kind of hoping you can synthesize benchmarks from here: get a good task creator, brainstorm some ideas with a domain expert, and you can make good tasks. My sense is that, for the time being, you just can't. The best tasks require that a person who really understands the domain is at the epicenter. The open question is how we learn to produce that, at high quality and at volume, reliably.

And the hardest part isn't the task, it's the verifier. When you have something like a C++ compiler with its whole test suite, or SQLite, and you build the task around that, that's great. But there are only so many applications that come with that degree of testing. Most verifiers are too married to a particular solution. The solution someone provides and the verifier they write are linked to each other, because the same person made both. So you're not really testing the result, you're testing against the author's own answer. The SQLite test suite actually tests the output of the queries. That's the difference, and it's hard to produce.

I've stayed mostly in the terminal because it seems to me the native space where agents are going to operate. You should be able to port pretty much any concept into the terminal.

## Confront the real world

For now we still get a lot of mileage from really high-quality a priori thinking about how to test something. But that runs out too, and the best verifier is the one that confronts the real world.

Take the extreme. Say I want to teach my AI about aerodynamics. The ultimate setup is I raise some money and I buy a wind tunnel from a company going out of business. I get big 3D printers. Anybody can request the shape of a wing, and I print it precisely, put it in the wind tunnel, and give you back precise measurements. Maybe a simulator is the first-order approximation, but eventually the task, the verifier, is a wind tunnel somewhere in physical space. When you run my thing, I give you that data back.

There are softer versions of the same idea. In finance, here's five thousand dollars, turn it into ten thousand. At the end of the day you have to trade real money, in real time, to know the thing actually works. That's about the easiest way to confront the real world. A verifier that touches reality can't be gamed the way a verifier that's married to its author's solution can.

## Who makes the tasks

So if good tasks require a domain expert at the epicenter, and good verifiers are this hard to build, the real question is who makes them, and how you get them at quality and volume.

I don't think the current model is the right one. The work mostly runs through a couple of very large data vendors, and it's hard to know if they're not experts on the tasks they're making. They're worth tens of billions of dollars and they're still not doing an amazing job. The people actually making the tasks are anonymous. Nobody knows who they are, the names don't even get shared. All the reputation gets stripped out.

I think there's a better structure, closer to a marketplace, or at least a network. Imagine I make a task for Terminal Bench, and it has my name on it, and you can count how many times it's been a rolled out. Maybe I made a really good task and there have been a billion rollouts. Who is capturing that reputation? Right now it's some other entity that is effectively teaching AIs how to do things. That reputation, captured properly, might be incentive enough on its own.

And a lot of the incentive is already there if you set it up right. Think about SEO. Google wants high-quality content, people want to rank in Google, and there's some gaming along the way, but it mostly works. The same shape applies here. Every open-source project should have a library, documentation, and a number of tasks. Documentation is only good to a point; what you really want is tasks, because you want agents to use your project, and the way agents learn to use it is for a lab to train on good tasks. If I'm Salesforce and I want to be the system of record behind agents, I'm incentivized to publish high-quality tasks. If I'm a voice API and I want to be the one picked every time someone builds a voice app, that's a huge win, so I'm very incentivized to put that stuff out there. The labs are incentivized to use it, because there's generalization that comes from it. Both sides benefit, and nobody has to pay.

Building a high-quality task that passes a lot of checks is also much harder to game than stuffing keywords to rank a library. For the domain-specific cases where free incentives aren't enough, you can pay, more like a 99designs for environments: a lab says it has a gap, people submit environments, and the ones that create the most back-propagation benefit get paid.

There is a real open question about whether inserting a transaction into all of this lowers quality. The open-source community works partly because it isn't transactional. The first version of Terminal Bench got built on coauthorship, people a hop or two out got their name on the paper, which felt native to the open-source ethos. I don't have this fully worked out. But evals and benchmarks are how every one of these companies targets success, and when you peel back the layers it all comes down to a set of tasks made by a community of people. That makes the question of who makes them, and how they're rewarded, one of the more important problems in AI right now, and one nobody has really figured out.

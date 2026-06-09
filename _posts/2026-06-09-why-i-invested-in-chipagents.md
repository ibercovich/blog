---
layout: post
title: "Why I Invested in ChipAgents"
author: Ivan Bercovich
date: 2026-06-08T00:00:00.000Z
---

I invest in companies where AI is going to change how things get done. There are businesses that look like businesses you could have founded five years ago, and some of them will still do great, but that's not my area. My area is businesses that couldn't have existed before.

Today the best manifestation of that is the agent. You assign it a task, it can use tools, use a computer, do whatever it needs to do, for a long period of time. Right now the median interaction with an agent is maybe ten or twenty minutes. In a year it's going to be two or three hours. After that, four days at a time. As long as you're willing to pay for the tokens, it keeps going.

On one end you have an agent like Claude Code which can write software, and that's going to keep getting better and take more adjacencies around it. On the other end you can try to build an agent that's too far from what AI does well today: AI can do video generation, but ask it to make you a Oscar-winning film and we still don't know how that plays out. The companies that are really interesting in 2026 are close enough to software that we know it's going to work, but far enough that they won't get eaten up by the expansion of the labs. Every engineering discipline sits in that band, mechanical, aerospace, chemical. A lot of the thinking looks like software, but a lot of it is domain specific, with tools that are very unique to the field. Chip design is the hardest one I know, and that's why I like it.

## What the company does

The development of a semiconductor starts with something that looks like software. There's a language called Verilog, register transfer language, RTL, that describes the logic of the chip. That gets converted to gates, the gates get converted to physical design, and so on. But the stakes are nothing like software. When the first wafer comes out of the fab, depending on how advanced the process is, it can cost anywhere from thirty million to a billion dollars. There can't be any mistakes. In software you make a mistake, you lose some data, you deal with it. You can't operate that way with hardware. Which is why the whole thing starts from a blueprint, a very detailed spec.

ChipAgents operates at the front end. We grab that spec, turn it into tests, write the code, and verify the code works. Verifying isn't like normal code, where you execute it and if it ran you know it worked. You have to simulate it, because all of this is going to run on a clock, and everything has to happen in the physical window between clock cycles for the registers to capture the data. If it doesn't fit, you move the logic around so it does. There's a lot of that kind of simulation the agent has to interact with to make decisions.

So the picture is simple. We have an agent, the agent is the front end, and it's what the engineers interact with. Around the agent we're bolting a harness of tools. Some tools simulate the logic. Some make predictions about power consumption. Some, later, will be about layout, how the transistors are physically distributed over the wafer.

## The goal is not to beat Claude

It would be a bad strategy to fight hand to hand with a big lab on raw reasoning and coding. If anybody claims they can build a better model than Claude Opus at what Claude does, they're lying. The advantage is in the harness, and in the interactions between the tools and the harness.

There is room to build your own models, but not general-purpose ones. You build domain-specific models that act like sensors on a very particular kind of data. Take power. Instead of running a full simulation overnight on the cluster, you can train a model that takes a synthesis artifact as input and gives you a guess of the power consumption as output. It won't be exact, but it tells you immediately that some corner of the chip looks like it's drawing too much power, take another look. That's AI, but domain-specific AI, and nobody at a general-purpose lab is going to train it for you.

## Become the front end

This is the part I find most interesting. Verilog is free. Everybody uses Verilog, nobody cares, Verilog is free. That's the front end. The incumbents make their money on the back end: the simulators, the waveform analyzers. The agent becomes the front end of the front end. The heavy tools get called by the agent in the background, and we control the agent.

It will get to a point where a particular engineer won't know if the waveform simulation is coming from a Cadence tool, a Synopsys tool, or our tool. It doesn't matter, as long as the agent can solve the bug. And that gives us a ton of pricing power. If we can give something that's ninety percent of the way there but iterates much faster, we capture a lot of that power. We can go from using a vendor's simulator ninety percent of the time to ten percent of the time, on our own schedule.

## Innovator's dilemma

We're a complement to the EDA tools, not a competitor. The engineers used to write code by themselves in a normal IDE. We help them write the code and the tests, they send it off to be simulated, and our agent reads the results, looks for errors, and traces them back to the spec.

The physics simulators are extraordinarily precise, and they took decades and billions of dollars to build. That's fine, we'll keep using them. But they're slow and expensive, so today you run them constantly just for sanity checks. Our goal is to use them less, to lean on fast approximations during the design loop and save the full overnight run for the end. Instead of running a tool once a day and waiting overnight, you run something lower fidelity in five minutes. When that happens, EDA doesn't get displaced, it just becomes less important. The value moves to the front end, to the people actually designing the thing.

And speeding this up isn't only about cost. Demand for chips is bottlenecked on bandwidth, not just dollars. There's real revenue the big buyers can't capture because designs take too long, and a multi-year lag they would pay almost anything to shorten. So anything that accelerates design isn't just savings, it's new top-line revenue. The market as a whole gets larger.

## Why can't the incumbents do it?

Two reasons. The first is incentives. They charge by the compute-hour, so a tool that runs faster is a tool that bills less. Nobody builds the thing that cannibalizes their own meter.

The second is talent. Domain expertise is valuable, and it always will be. But AI is also its own domain, a very new one, and very few people have it at that level. AI is very deceptive, because everybody talks about it, and maybe twenty percent of them think they're experts. When you think about the people who can actually build a company like this, you're talking about a thousand people in the world. There's not that many. And finding people like that who also know chip design is very unlikely. They command very high salaries and they will go to a startup and take equity. There's no way the comp structure of a thirty-year-old EDA company can digest that, and those people don't want to work there anyway. You go to an AI conference and everyone wants to be at a startup or at one of the big labs. EDA isn't cool.

## Why the market keeps growing

Moore's law is tapped out, which means the only way to keep getting performance is domain-specific silicon. People are going to keep turning algorithms into chips, even high-frequency-trading firms burn their strategies into hardware. More chip diversity means more designs, and more designs means more demand for the front end they all run through.

Think about the IDE, the interface a developer uses to write code. For thirty years it was a free text editor nobody paid for. Then in the last few years it became very valuable; Cursor is a tens-of-billions-dollar company for what is, underneath, a text editor. What changed isn't the editor, it's that far more people are writing software. The same thing is starting in silicon. Companies that used to just buy chips are designing their own, Amazon has Trainium, and that moves down-market from here.

There's also a lot of leakage between the steps. Arm sells you intellectual property, blocks of compute you drop into your chip, but they're encrypted, so there isn't much of that on the internet. When you manufacture at TSMC, you have to hand it over in a very particular format, and TSMC only exposes that interface to a small number of companies. Every one of those bridges, from one step of the process to the next, is a place for an agent to play.

## What it comes down to

If you want to oversimplify the vertical AI industry, you're really reselling tokens at a premium. You just need an excuse to sell tokens at a premium. We package a few tools and a harness that makes using Claude through us better than using it directly, and for the privilege we get to charge more. It's a variation on fintech.

The most important question for anyone building in this space is whether there's enough durable differentiation for a ChipAgents to exist at the same time a Claude Code exists. I think the answer is yes, and it comes down to the sophistication of the tools. That's the whole bet.

This is one of the biggest industries in the world, and one of the fastest growing. The incumbents are hundred-billion-dollar companies. I think you can build something on that scale here, and you do it by owning the front end and letting the agent quietly take over everything behind it.

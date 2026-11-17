---
layout: post
title: "Why I Invested in ChipAgents"
author: Ivan Bercovich
date: 2026-06-08T00:00:00.000Z
---

I invest in companies where AI is going to change how things get done. There are businesses that look like businesses you could have founded five years ago, and some of them will still do great, but that's not my area. My area is businesses that couldn't have existed before.

Today the best manifestation of that is the agent. You assign it a task, it can use tools, use a computer, do whatever it needs to do, for a long period of time. Right now the median interaction with an agent is maybe ten or twenty minutes. In a year it's going to be two or three hours. After that, four days at a time. As long as you're willing to pay for the tokens, it keeps going.

On one end you have an agent like Claude Code which can write software, and that's going to keep getting better and take more adjacencies around it. On the other end you can try to build an agent that's too far from what AI does well today: AI can do video generation, but ask it to make you an Oscar-winning film and we still don't know how that plays out. The companies that are really interesting in 2026 are close enough to software that we know it's going to work, but far enough that they won't get eaten up by the expansion of the labs. Every engineering discipline sits in that band: mechanical, aerospace, chemical. A lot of the thinking looks like software, but a lot of it is domain specific, with tools that are very unique to the field. Chip design is the hardest one I know, and that's why I like it.

I've known William, the founder, for ten years, and when he was starting the company he came to us first. We wrote the very first check. I'm an electrical engineer by training, but I hadn't been in touch with semiconductors until joining the board.

## What the company does

The development of a semiconductor starts with something that looks like software. There's a language called Verilog that describes the logic of the chip at the register transfer level, RTL. That gets converted to gates, the gates get converted to physical design, and so on. But the stakes are nothing like software. When the first wafer comes out of the fab, depending on how advanced the process is, it can cost anywhere from thirty million to a billion dollars. There can't be any mistakes. In software you make a mistake, you lose some data, you deal with it. You can't operate that way with hardware. Which is why the whole thing starts from a blueprint, a very detailed spec.

ChipAgents grabs the spec, turns it into tests, writes the code, and verifies the code works. Verifying isn't like normal code, where you execute it and if it ran you know it worked. You have to simulate it, because all of this is going to run on a clock, and everything has to happen in the physical window between clock cycles for the registers to capture the data. If it doesn't fit, you move the logic around so it does. There's a lot of that kind of simulation the agent has to interact with to make decisions.

So the picture is simple. We have an agent, the agent is the front end, and it's what the engineers interact with. Around the agent we're bolting a harness of tools. Some tools simulate the logic. Some make predictions about power consumption. Some, later, will be about layout, how the transistors are physically distributed over the wafer.

## The goal is not to beat Claude

It would be a bad strategy to fight hand to hand with a big lab on raw reasoning and coding. If anybody claims they can build a better model than Claude Opus at what Claude does, they're lying. The advantage is in the harness, and in the interactions between the tools and the harness.

The tools are built for agents, not for people. We see a world where most of the tool calls, most of the technical decisions, are made by agents. A GUI, even if an agent can use it, is intended for people. Humans literally look at waveforms: you have a viewer, you scroll left and right, and you try to see when something changed. Agents don't want to do that. They just want to query it. So you have to turn the waveforms into a database with an API, so the agent can get to the answer quickly and iterate from there.

There is room to build your own models, but not general-purpose ones. You build domain-specific models that act like sensors on a very particular kind of data. They're not LLMs. The LLM is just the agent. Take power. Instead of running a full simulation overnight on the cluster, you can train a model that takes a synthesis artifact as input and gives you a guess of the power consumption as output. It won't be exact, but it tells you immediately that some corner of the chip looks like it's drawing too much power, take another look. That's AI, but domain-specific AI, and nobody at a general-purpose lab is going to train it for you.

## Become the front end

This is the part I find most interesting. Verilog is free. Everybody uses Verilog, nobody cares, Verilog is free. Engineers write it in VS Code, which was never owned by Synopsys or Cadence either. That's the front end. The incumbents make their money with the tools, the simulators and the waveform analyzers, each of which also has its own interface. The agent becomes the front end of the front end. The heavy tools get called by the agent in the background, and we control the agent.

It will get to a point where a particular engineer won't know if the waveform simulation is coming from a Cadence tool, a Synopsys tool, or our tool. It doesn't matter, as long as the agent can solve the bug. If we can give something that's ninety percent of the way there but iterates much more quickly, we converge on the solution faster. We can go from using a vendor's simulator ninety percent of the time to ten percent of the time, on our own schedule.

## Innovator's dilemma

We're a complement to the EDA tools, not a competitor. The engineers used to write code by themselves in a normal IDE. We help them write the code and the tests, they send it off to be simulated, and our agent reads the results, looks for errors, and traces them back to the spec. Agents are more similar to humans than they are to tools.

The physics simulators are extraordinarily precise, and they took decades and billions of dollars to build. Precision is the whole shtick. Every new release is more precise, uses more compute, and tries to give you more accuracy. That's fine, we'll keep using them. But they're slow and expensive, so today you run them constantly just for sanity checks. Take PrimeTime, the Synopsys timing tool. I asked a bunch of customers how long it takes to run on a block. Twelve hours. You run it before you go home, and nothing happens until you come in the morning. Sure, AI is helpful, but what's the point if the AI has to wait twelve hours?

Agents change the paradigm. There's a difference between a coding assistant, where a human is in the loop accepting help, and an agent working on its own, or a swarm of agents. With agents you want to scale in parallel, and you want them to take repeated actions. Agents need fast tools. So the tools we build are much lower precision. Precision is not a concern for us at all. Speed is. Can I get something in five or ten minutes, so the agent gets at least a hint of what the problems may be, iterates, comes back, and iterates again? It's cheaper too, and you can have a bunch of agents doing this in parallel across multiple blocks.

Our goal is to use the simulators less, to lean on fast approximations during the design loop and save the full overnight run for the end. Instead of running PrimeTime a hundred times over the creation of a block, twelve hundred hours, you run it ten times at the end. The person responsible for guaranteeing the timing is still using PrimeTime, just less frequently. When that happens, EDA doesn't get displaced, it just becomes less important. The value moves to the front end, to the people actually designing the thing.

And speeding this up isn't only about cost. Demand for chips is bottlenecked on bandwidth, not just dollars. There's real revenue the big buyers can't capture because designs take too long, and a multi-year lag they would pay almost anything to shorten. So anything that accelerates design isn't just savings, it's new top-line revenue. The market as a whole gets larger.

## Why can't the incumbents do it?

Two reasons. The first is incentives. They charge by the compute-hour, so a tool that runs faster is a tool that bills less. Nobody builds the thing that cannibalizes their own meter. And say they wanted to make fast tools anyway. It's antithetical to their marketing. They'd have to go to customers and say, hey, we have this tool, it's actually crappier. That's not how they sell.

The second is talent. Domain expertise is valuable, and it always will be. But AI is also its own domain, a very new one, and very few people have it at that level. AI is very deceptive, because everybody talks about it, and maybe twenty percent of them think they're experts. When you think about the people who can actually build a company like this, you're talking about a few thousand people in the world. There's not that many. And finding people like that who also know chip design is very unlikely. They command very high salaries and they will go to a startup and take equity. There's no way the comp structure of a forty-year-old EDA company can digest that, and those people don't want to work there anyway. You go to an AI conference and everyone wants to be at a startup or at one of the big labs. EDA isn't cool.

## What about the labs?

The labs are more of a threat to vertical AI companies than any of the incumbents. In chip design, Anthropic is more of a threat than Synopsys. But semiconductor design is the most complex manufacturing process in the world, and there's plenty of shit to do that Anthropic won't fall into by luck or by throwing five or ten people at the problem. It's hard for me to believe you'll install Claude Code, say "build me a chip," and it will do all the proper integrations, deal with everything that has to be dealt with, plus design its own tools.

Then there's the data. Chip design data is so scarce. There's some open-source chip design, and you can buy some IP, but for the most part it's proprietary. We don't have it, and Anthropic doesn't have it either. Even if a lab designs its own chip and trains on that, it's one chip. So where is the data? The data is inside the companies. Which means you have to go inside, with forward deployed engineers, and train on their data, inside their firewall, on their GPUs. The model is theirs, and it never leaves their infrastructure. And training here doesn't mean throwing a spreadsheet at a model. We're talking about reinforcement learning and complex training curriculums. To do that, you need a lot of trust.

That threat is smaller two years from now than it is today, because today we may be fifty percent Claude and fifty percent other stuff. Over time the agent becomes less important on a relative basis, and the integrations become more important. That's the race.

## Why the market keeps growing

Moore's law is tapped out, which means the only way to keep getting performance is domain-specific silicon. People are going to keep turning algorithms into chips. Even high-frequency trading firms burn their strategies into hardware. More chip diversity means more designs, and more designs means more demand for the front end they all run through.

Think about the IDE, the interface a developer uses to write code. For thirty years it was a free text editor nobody paid for. Then in the last few years it became very valuable; Cursor is worth tens of billions of dollars for what is, underneath, a text editor. What changed isn't the editor, it's that far more people are writing software. The same thing is starting in silicon. Companies that used to just buy chips are designing their own (Amazon has Trainium), and that moves down-market from here.

There's also a lot of leakage between the steps. Arm sells you intellectual property, blocks of compute you drop into your chip, but they're encrypted, so there isn't much of that on the internet. When you manufacture at TSMC, you have to hand it over in a very particular format, and TSMC only exposes that interface to a small number of companies. Every one of those bridges, from one step of the process to the next, is a place for an agent to play.

## What it comes down to

If you want to oversimplify the vertical AI industry, you're really reselling tokens at a premium. You just need an excuse to sell tokens at a premium. You can use Claude Code to generate RTL, but if verifying that RTL means waiting twelve hours on PrimeTime, that's not a good setup. We package a few tools and a harness that makes using Claude through us better than using it directly, and for the privilege we get to charge more. It's a variation on fintech.

The most important question for anyone building in this space is whether there's enough durable differentiation for a ChipAgents to exist at the same time a Claude Code exists. I think the answer is yes, and it comes down to the sophistication of the tools. That's the whole bet.

This is one of the biggest industries in the world, and one of the fastest growing. The incumbents are hundred-billion-dollar companies. I think you can build something on that scale here, and you do it by owning the front end and letting the agent quietly take over everything behind it.

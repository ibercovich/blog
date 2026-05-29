---
layout: post
title: "The Sequence of Verifiers"
author: Ivan Bercovich
date: 2026-05-26T00:00:00.000Z
---

Verification is a ladder.

**Next token prediction.** You have a lot of tokens on the internet and you have to predict the next one.

**Built-in verification.** A lot of artifacts naturally include a verification mechanism. Think of a multiple choice test and an answer sheet. There are also less obvious "free" verifiers implied in a particular workflow. In SWE-bench, we take successful PRs, rewind them, and now we have ourselves a problem statement and a way to validate a solution. Most human labor which leave a digital exhaust encodes some form of verification. One problem with this approach is that it tends to result in simple, one-shot tasks. It's straightforward to find traces of human work over the course of a day and within a single tool. It's much harder to understand a task that took several weeks, across tools and channels, and which was being executed in parallel with many unrelated tasks.

**Custom paid tasks.** This is what most people are doing today, mid-2026. Terminal Bench is in this category. You pay someone thousands of dollars to build you a custom task. These are well thought out for a specific objective, often include an oracle solution for auditing, and include a comprehensive verifier. But you have shops outsourcing to hourly workers, making them at scale, and it's hard to make good tasks consistently. As a professional, the best tasks are things you have had to deal with yourself. There are only so many things you have had to do that are really interesting and challenging that you understand better than everybody else. Otherwise, at scale, you can model the task, but it won't have the same fidelity. And of course, since task creators are using AI, it's hard to draw a line between purely synthetic and novel. As models get better, it becomes hard to scale. A-la-carte tasks have a complexity limit.

**Reconstruction tasks.** The next level of complexity involves things like building a web browser or compiler from scratch. We can do these because in the past we spent a lot of time building web browsers and compilers, and we have a lot of tests for them. The mechanisms to test that this really complex software was built actually exist. Nicholas Carlini spent 20,000 dollars building a C compiler benchmark of this kind. These tasks are hard. But we're going to saturate these too, maybe in 12-18 months.

And after that, we basically run out of low hanging fruit. People spent however many man hours creating a compiler and all of its tests. You can't just fabricate that for other domains.

**Reality.** Then you start coming into contact with reality. The AI comes up with an idea. You instrument the feedback loop to test whether the prediction was right. I want to make a better adhesive, so I mix these things, blow it up, and measure stickiness. I want to make a better plane, so I have a wind tunnel, the AI designs the plane, I print it with a 3D printer, I get the measurements, I feed them back to the AI. Instrumentation that confronts physics.

I think this is how the next iteration of AI gets developed. A nice property of it is that it's confronting physics, so presumably it's harder to reward hack. It's one thing to reward hack a physics simulator. It's another to reward hack physics.

People are already doing this. Biochemistry labs hooked up to the AI. Mix these two things, do this reaction, get the readings back. The more interesting version to me is the grounding version. The verifier as instrumentation. The verifier as the thing that drags the model back into the real world.

The pattern across all five rungs is the same. You start with verifiers that are cheap and abundant and loose, and you keep moving toward verifiers that are scarce and expensive and tight. The wishy washy reward signal at one end is what produces reward hacking at the other end. Some people in safety believe reward hacking is a really bad problem, and that as long as training has weaknesses it will continue to emerge. It's a natural consequence of weak signal. Reality is the tightest signal we have access to. Eventually the ladder ends there.

Right now most reward hacking is a software problem. You get a bug, bad things happen, you move on. But soon you'll be reward hacking things that become real. Either the AI designs a bridge and you build it, or it designs a policy and you implement it. It can be anything. So the question is, when the AI thinks it has a good idea, how do you verify? I was trying to clean rocks out of my quinoa the other day, where the rocks are the same size as the grains. I asked Claude to design a machine I could build to separate them. I asked for an animation of how it would function, and it showed me one. Does that actually work, or is it crazy? Who is building these things to know they're good ideas?

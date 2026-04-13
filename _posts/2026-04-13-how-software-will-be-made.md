---
layout: post
title: "How Software Will Be Made"
author: Ivan Bercovich
date: 2026-04-13T00:00:00.000Z
---

Lately, I only build things where I'm the sole author, and I 100% vibe code it. I don't really look at code. I look at commits a little bit, but not really. I look at the app. I look at the behavior.

First, I build the thing. I give a lot of feedback. If it uses data, I can see the data, check if it makes sense. Then I use it. I record usage, clicks, inputs, outputs. I get analytics on everything. Something that could have been a thousand lines of code is now three thousand. Messy, bloated, but functional.

Then I tell the AI: grab all my usage data, assume the app behaves as it's supposed to, and create a massive number of tests. Every input and output from my actual usage becomes the test set. Then I put it in a loop: keep making this smaller. The tests have to pass. Every time you change something, test, test, test.

It never gets back to a thousand lines. The AI isn't good enough yet at coming up with really clever new abstractions. But it cuts it by about 60%. The idea is: design, throw away, but use the artifacts as the new requirements and the test set, then do it again.

If your analytics record exactly what everybody did, and you can replay that and get the exact same output, pixel perfect, and you can achieve that with half the lines of code or twice the performance, you're in good shape.

The key insight is that you should be able to replay everything. Assume your application has no bugs, because what you're really trying to do is build a better application that behaves the same. If there's a bug, whatever, you can replicate the bug. That's a feature, not a problem.

I think replay analytics is a product someone should build. It's not trivial. You need the database in the right state. You need to replay everything end to end. But if you can do it, you get something powerful: a perfect specification that isn't a document. It's reality.

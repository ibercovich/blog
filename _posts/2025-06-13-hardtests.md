---
layout: post
title: "Announcing HardTests"
author: Ivan Bercovich
date: 2025-06-13 01:01:02 -0700
categories:
---

The challenge of truly robust Reinforcement Learning with Verifiable Rewards (RLVR) is immense, and there's so much opportunity to push the boundaries. Working with Kexun Zhang, Zhongmou He, Yee Man Choi, Jiabao Ji, Junting Zhou, Dejia Xu, Aidan Zhang, and Lei Li on our latest paper has been a reminder of how much exciting work there is to do in making AI more reliable.

Verifiers play a crucial role in RL, but building reliable ones is tough, especially for difficult coding problems. Existing test datasets can often be too simple, letting buggy or inefficient code slip through.

To tackle this, we developed HARDTESTGEN, a pipeline that uses LLMs to synthesize significantly more challenging and comprehensive test cases. It isn't just about quantity; it's about crafting tests that find those well-disguised wrong solutions and edge cases that simpler tests miss.

Our 47k HARDTESTGEN tests show dramatically higher precision and recall when evaluating LLM-generated code.
We've demonstrated that using these harder, better tests significantly improves downstream LLM performance in post-training scenarios like reinforcement learning and self-distillation.

Relevant Links:
[Dataset and Synthesis Pipeline](https://leililab.github.io/HardTests/)
[The Full Paper](https://arxiv.org/abs/2505.24098)

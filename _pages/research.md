---
layout: centered
author: Ivan Bercovich
title: Research
permalink: /research/
---

## Publications

### 2026

**[Terminal-bench: Benchmarking agents on hard, realistic tasks in command line interfaces](https://arxiv.org/abs/2601.11868)**
MA Merrill, AG Shaw, N Carlini, B Li, H Raj, I Bercovich, L Shi, JY Shin, et al.
*arXiv preprint arXiv:2601.11868*

A benchmark of 89 hard terminal tasks from real workflows, where frontier models achieve less than 65% success. Tasks span legacy system configuration, research paper reimplementation, and software engineering problems with human-written solutions and comprehensive verification tests.

![Terminal-Bench Task Architecture](../assets/terminal-bench-architecture.png)

### 2025

**[Agents of change: Self-evolving LLM agents for strategic planning](https://arxiv.org/abs/2506.04651)**
N Belle, D Barnes, A Amayuelas, I Bercovich, XE Wang, W Wang
*arXiv preprint arXiv:2506.04651*

HexMachina, a continual learning multi-agent system for long-horizon strategic planning in adversarial environments. Tested on Settlers of Catan, it learns from scratch and evolves players that outperform human-crafted baselines with 54% win rate by separating environment discovery from strategy refinement.

**[Hardtests: Synthesizing high-quality test cases for LLM coding](https://arxiv.org/abs/2505.24098)**
Z He, YM Choi, K Zhang, J Ji, J Zhou, D Xu, I Bercovich, A Zhang, L Li
*arXiv preprint arXiv:2505.24098*

A pipeline for synthesizing high-quality test cases for competitive programming, achieving 11.3pp higher precision and 17.5pp higher recall than existing tests. Includes a dataset of 47k problems demonstrating that test quality significantly impacts self-distillation and reinforcement learning performance.

**[MessIRve: A large-scale Spanish information retrieval dataset](https://arxiv.org/abs/2409.05994)**
F Valentini, V Cotik, D Furman, I Bercovich, E Altszyler, JM Pérez
*Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing*

A Spanish IR dataset with 730k queries from 20 Spanish-speaking countries sourced from Google autocomplete and Wikipedia documents. Unlike translated datasets, MessIRve captures regional dialectal variations and culturally relevant topics to advance Spanish information retrieval research.

## Research Interests

- **Large Language Models & Agents**: Self-evolving systems, benchmarking, and strategic planning
- **Code Generation & Testing**: Automated test synthesis and quality assessment for LLM-generated code
- **Information Retrieval**: Large-scale multilingual datasets and retrieval systems
- **Knowledge Graphs & NLP**: Semantic understanding and structured knowledge representation
- **Command Line Interfaces**: Agent performance in realistic terminal environments

## Industry Experience

### Graphiq (2011-2017), Amazon Alexa (2017-2020)

Led the architecture and scaling of Graphiq's Knowledge Graph, building an ontology of 1.7 billion entities, 285 billion data points, and roughly 1.5 trillion relationships across hundreds of domains. The core technical challenge involved creating automated ETL infrastructure that non-engineers could operate autonomously, integrating over 1,200 data sources while processing 300 million daily updates. What previously took years to ingest and publish was compressed to weeks or minutes.

Built a natural language question-answering system using bottoms-up semantic parsing over the structured Knowledge Graph. By sequentially combining NER, intent extraction, and NLG templating, we translated text queries into database operations with auto-generated visualizations. Through distributed database optimization and automated indexing, maintained 150-200ms response times at 25,000 queries per second. Internal benchmarks showed higher accuracy than Amazon Alexa and Google on standard query batteries.

![Graphiq Knowledge Platform & Answering Engine Architecture](../assets/graphiq-architecture.png)

## Academic Background

**Ph.D. Studies, Statistics and Applied Probability** (2010, unfinished)
University of California, Santa Barbara
*Financial Mathematics*

**B.S. Electrical Engineering and Mathematics** (2005-2009)
University of Massachusetts Amherst
*Summa Cum Laude, GPA 3.95/4.00*
*Departmental Honors with greatest distinction*

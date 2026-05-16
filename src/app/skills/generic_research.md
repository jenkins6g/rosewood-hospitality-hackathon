---
name: generic_research
description: Research a question using provided docs and tools, then synthesize a grounded answer.
when_to_use: Use for questions that require finding evidence, comparing sources, or summarizing relevant material before answering.
tags:
  - research
  - evidence
  - synthesis
inputs:
  - user question
  - available local documents
  - current session memory
steps:
  - Restate the information need in one sentence.
  - Search the available local materials before answering from memory.
  - Pull only the smallest excerpts needed to answer.
  - Synthesize the answer and call out uncertainty when evidence is thin.
examples:
  - Find the most relevant local docs for a question and summarize them.
  - Compare two approaches using the available materials.
---
# Generic Research

Operate like an analyst:

1. Translate the user request into a concrete research target.
2. Use document lookup when local evidence would improve the answer.
3. Prefer direct evidence over speculation.
4. Produce a concise synthesis, not a dump of snippets.

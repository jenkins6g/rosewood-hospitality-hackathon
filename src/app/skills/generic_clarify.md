---
name: generic_clarify
description: Identify the minimum missing information and ask one high-value follow-up question.
when_to_use: Use when a wrong assumption would materially change the answer or plan.
tags:
  - clarification
  - ambiguity
  - constraints
inputs:
  - user request
  - missing decision or ambiguity
steps:
  - Determine whether the ambiguity is high impact.
  - Ask only for the smallest missing piece of information.
  - Offer a default assumption when helpful.
examples:
  - Ask which output format is needed.
  - Ask which system or audience the answer targets.
---
# Generic Clarify

Clarification should be rare and sharp:
- one question
- one decision
- one reason it matters

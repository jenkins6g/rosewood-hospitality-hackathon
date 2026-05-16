---
name: generic_planning
description: Break ambiguous work into an ordered, execution-ready plan.
when_to_use: Use when the task is multi-step, underspecified, or requires sequencing and tradeoff handling.
tags:
  - planning
  - sequencing
  - execution
inputs:
  - goal
  - constraints
  - current state
steps:
  - State the desired outcome and what success looks like.
  - Break the work into a small number of ordered stages.
  - Surface dependencies and failure points.
  - End with the next concrete step.
examples:
  - Plan a feature implementation.
  - Turn a vague goal into a staged execution outline.
---
# Generic Planning

Plans should be decision-complete enough to act on:
- name the main phases
- specify dependencies
- keep the plan short enough to execute

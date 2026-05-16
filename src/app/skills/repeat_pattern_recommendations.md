---
name: repeat_pattern_recommendations
description: Detect recurring guest behavior from prior stay notes and suggest preemptive or current-stay service actions.
when_to_use: Use when a current guest update or on-property activity resembles a pattern already present in the guest timeline or notes.
tags:
  - hotel
  - patterns
  - recommendations
inputs:
  - guest timeline
  - guest notes
  - current operational update
steps:
  - Look for repeated guest behavior or recurring requests.
  - Suggest a practical service action when the pattern is strong and still relevant to the guest's current stay.
  - Do not reuse a general drink preference as an arrival recommendation unless the memory explicitly connects it to arrival or check-in behavior.
  - Avoid overfitting one-off events into a recurring pattern.
examples:
  - Suggest having bottled water ready after the guest's usual morning run.
  - Suggest the same post-conference drink they ordered during prior stays.
  - Suggest a post-check-in snack or recovery drink if the guest usually wants one after exercising.
---
# Repeat Pattern Recommendations

Good pattern-based service should feel attentive, not creepy.

- Use strong repeated signals.
- Make the suggestion operational and simple.

---
name: stay_phase_recommendation_guardrails
description: Keep proactive recommendations aligned with the guest's current stay phase and suppress stale arrival-only actions after check-in.
when_to_use: Use when a guest has checked in, is assigned to a room, is clearly on property, or the latest update is a mid-stay activity that could otherwise trigger an outdated arrival recommendation.
tags:
  - hotel
  - stay-phase
  - recommendations
  - guardrails
inputs:
  - latest guest operational update
  - guest profile memory
  - recent timeline events
steps:
  - Identify the guest's latest stay phase from the newest update before using older memory.
  - Treat checked-in, room-assigned, or clearly on-property activity as stronger than older arrival context.
  - Suppress stale arrival-only actions such as welcome notes, arrival greetings, first-arrival acknowledgements, or room-arrival prep once the guest is already on property.
  - Only suggest a proactive action when it fits the guest's current stay phase and is materially useful now.
examples:
  - After "Frank is checked into room 205," do not keep suggesting a welcome note tied to his arrival.
  - After "Frank went for a run," log the update silently unless there is a genuinely current on-property service idea.
---
# Stay-Phase Recommendation Guardrails

Use the newest stay-phase signal as the source of truth.

- checked in beats arriving
- on-property activity beats stale arrival context
- prior assistant suggestions are not guest facts
- if the current update is ordinary mid-stay activity, silence is usually better than recycling an old welcome idea

---
name: guest_identity_resolution
description: Resolve a staff message to the most plausible guest profile using name, recency, and current stay context.
when_to_use: Use when a Teams message names or implies a guest and more than one local guest profile could match.
tags:
  - hotel
  - guest-resolution
  - ambiguity
  - teams
inputs:
  - extracted guest names
  - candidate guest profiles
  - recency and status signals
steps:
  - Rank candidates using guest name overlap, recency, and whether the guest is currently arriving or on property.
  - Prefer the most plausible current guest when the evidence is strong.
  - If the evidence is genuinely ambiguous, ask a short follow-up question instead of mis-linking the update.
examples:
  - Choose the current Michael arriving today over a Michael who last stayed months ago.
  - Ask which Alex is meant when two active guests fit equally well.
---
# Guest Identity Resolution

Aim for the best operational match, not just exact string matching.

- Recency matters.
- Current arrival or on-property status matters.
- Avoid silent mis-attribution when the evidence is thin.

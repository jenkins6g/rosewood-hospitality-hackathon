---
name: guest_profile_tracking
description: Track durable guest facts and timeline updates from hotel-team communication in Teams.
when_to_use: Use when staff mention a hotel guest, their arrival, stay details, activities, or service preferences that should be saved to a local guest profile.
tags:
  - hotel
  - guest-profile
  - memory
  - teams
inputs:
  - teams message text
  - sender and conversation metadata
  - existing guest profile summaries
steps:
  - Identify whether the message is about a specific guest.
  - Extract only the durable guest-relevant facts worth saving.
  - Prefer concise event summaries over verbose transcript storage.
  - Update the guest timeline and notes silently unless clarification is required.
examples:
  - Michael Johnson lands at 6:10 PM and is heading to the property.
  - Sarah asked for a vegetarian dinner setup in her room.
---
# Guest Profile Tracking

Treat hotel staff messages as operational updates, not casual chat logs.

- Save guest-relevant facts to a local profile and timeline.
- Favor compact summaries that help future service decisions.
- Do not store every surrounding chat message when only one guest fact matters.
- If a message is not clearly about a guest, do not force it into a guest profile.

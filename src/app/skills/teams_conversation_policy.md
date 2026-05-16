---
name: teams_conversation_policy
description: Decide how the bot should behave in Teams conversations, including when to reply, memorize a durable fact, ignore ambient chatter, or silently log hotel guest operations.
when_to_use: Use for any Teams-originated event where channel, group chat, mention status, social context, or hotel guest activity affects whether the assistant should answer, remember, or stay silent.
tags:
  - teams
  - conversation-policy
  - reply
  - memorize
  - ignore
inputs:
  - teams message text
  - conversation surface
  - mention status
  - sender and conversation metadata
steps:
  - Determine whether the message is directed at the bot or ambient chatter.
  - Decide whether the message contains a durable preference, fact, or constraint worth storing.
  - Use conservative reply behavior in channels and group chats.
  - Prefer silence over interrupting shared conversations when the bot was not addressed.
  - Silently log most guest operations updates unless the bot was asked a direct question or must clarify an ambiguous guest match.
  - Proactively suggest a service action during key guest moments such as arrivals, departures, or strong repeat-behavior patterns.
examples:
  - A direct question in personal chat should usually get a reply.
  - A channel preference statement like "I prefer vegetarian options" can be memorized without a reply.
  - Background chatter in a channel should usually be ignored.
  - A staff message about a guest's arrival or spa appointment should usually be memorized silently.
  - A guest arrival update can justify a concise proactive suggestion for staff.
---
# Teams Conversation Policy

Apply these defaults:

- **Reply** when the bot is directly addressed, especially in personal chat or via `@mention`, and the user appears to expect an answer.
- **Memorize** when the message contains a durable preference, fact, commitment, or constraint that could help future interactions.
- **Memorize** when staff are posting guest arrival or on-property activity updates that should be tied to a guest profile.
- **Reply** during key guest-service moments when a concise recommendation would help staff improve the stay.
- **Ignore** when the message is ambient chatter, not directed at the bot, and contains no clear durable information.

Stay conservative in channels and group chats:

- avoid jumping into conversations uninvited
- do not answer every nearby question
- if uncertain in a shared space and the bot was not addressed, prefer `ignore`
- if two guest profiles are both plausible and a wrong match would be risky, ask a short follow-up question

Examples of memory-worthy content:

- preferences: dietary needs, communication preferences, tone preferences
- factual profile data the user shares intentionally
- long-lived constraints or commitments

Examples of usually ignorable content:

- greetings between people
- side banter
- logistics not directed at the bot

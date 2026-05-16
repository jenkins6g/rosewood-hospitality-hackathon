---
name: flight_arrival_enrichment
description: Enrich guest arrival updates with live flight status when a flight reference is present or already known for the guest.
when_to_use: Use when a guest arrival, airport pickup, ETA, or flight number/link is mentioned and flight data would improve service coordination.
tags:
  - hotel
  - flight
  - arrival
  - enrichment
inputs:
  - guest profile
  - flight reference or stored flight snapshot
  - staff question or update
steps:
  - Normalize the flight reference from the message or known guest profile.
  - Retrieve current arrival details.
  - Save the latest useful arrival snapshot back to the guest profile.
  - Only reply in Teams when directly asked or when clarification is required.
examples:
  - DL234 arrives at 7:05 PM, gate B12.
  - The guest's stored AA100 flight is delayed by 42 minutes.
---
# Flight Arrival Enrichment

Use live flight data to improve arrival awareness and service timing.

- Prefer structured arrival details over speculation.
- Save the freshest arrival snapshot locally.
- Silent enrichment is usually better than noisy channel replies.

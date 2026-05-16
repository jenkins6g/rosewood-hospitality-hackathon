---
name: arrival_service_recommendations
description: Recommend personalized arrival touches based on prior stay memory, travel context, and current arrival details.
when_to_use: Use when a guest is arriving, checking in, or nearing the property and the staff would benefit from a proactive service suggestion.
tags:
  - hotel
  - arrival
  - recommendations
inputs:
  - guest profile memory
  - recent timeline events
  - flight and weather context
steps:
  - Identify the guest's likely immediate needs on arrival.
  - Use this skill only while the latest update still reflects an active arrival moment, not after the guest has clearly moved into the stay.
  - Use prior preferences and recent patterns only when the memory explicitly supports the arrival moment.
  - Do not turn a general beverage preference into an arrival drink suggestion unless the history ties it to arrival, check-in, welcome, landing, or immediate first-on-property behavior.
  - Keep the recommendation concise and actionable for hotel staff.
examples:
  - Suggest offering the guest's usual whiskey on arrival only if the guest history specifically connects that drink to arrival or check-in.
  - Suggest asking how the weather was in their departure city.
---
# Arrival Service Recommendations

Great arrival suggestions should be concrete:

- welcome gesture
- beverage or amenity cue when the arrival history supports it
- travel-aware conversation starter

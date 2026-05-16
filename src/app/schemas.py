from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


ChatSurface = Literal["personal", "channel", "group_chat", "unknown"]
AdapterSource = Literal["cli", "teams"]
TurnAction = Literal["reply", "memorize", "ignore"]
GuestMatchStatus = Literal["matched", "created", "ambiguous", "unmatched", "not_guest_related"]


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    when_to_use: str
    tags: list[str]
    inputs: list[str]
    steps: list[str]
    examples: list[str]
    body: str
    path: Path


@dataclass(frozen=True)
class ChatEvent:
    text: str
    source: AdapterSource
    surface: ChatSurface
    is_mentioned: bool
    sender_id: str
    sender_name: str
    conversation_id: str
    channel_id: str = ""
    team_id: str = ""
    message_id: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FlightSnapshot:
    flight_reference: str
    airline: str = ""
    status: str = ""
    departure_airport: str = ""
    arrival_airport: str = ""
    scheduled_arrival: str = ""
    estimated_arrival: str = ""
    actual_arrival: str = ""
    arrival_terminal: str = ""
    arrival_gate: str = ""
    baggage_claim: str = ""
    delay_minutes: str = ""
    source: str = "aviationstack"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class OperationalUpdate:
    is_guest_related: bool = False
    guest_name_candidates: list[str] = field(default_factory=list)
    event_kind: str = "note"
    summary: str = ""
    details: str = ""
    flight_reference: str = ""
    flight_link: str = ""
    needs_arrival_lookup: bool = False


@dataclass(frozen=True)
class GuestEvent:
    timestamp: str
    source: AdapterSource
    surface: ChatSurface
    sender_id: str
    sender_name: str
    conversation_id: str
    channel_id: str
    team_id: str
    message_id: str
    event_kind: str
    summary: str
    details: str
    raw_text: str
    confidence_note: str = ""
    flight_snapshot: FlightSnapshot | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.flight_snapshot is None:
            payload["flight_snapshot"] = None
        return payload


@dataclass(frozen=True)
class GuestProfile:
    guest_id: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    status: str = "active"
    last_seen_at: str = ""
    latest_flight: FlightSnapshot | None = None
    profile_notes: list[str] = field(default_factory=list)
    timeline: list[GuestEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.latest_flight is None:
            payload["latest_flight"] = None
        return payload


@dataclass(frozen=True)
class GuestMatchDecision:
    status: GuestMatchStatus
    guest_id: str = ""
    guest_name: str = ""
    reasoning: str = ""
    clarification_question: str = ""
    candidate_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryNote:
    timestamp: str
    source: AdapterSource
    surface: ChatSurface
    sender_id: str
    sender_name: str
    conversation_id: str
    channel_id: str
    team_id: str
    message_id: str
    original_text: str
    note: str
    category: str = "durable_fact"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class TurnResult:
    action: TurnAction
    content: str = ""
    reply_content: str | None = None
    reason: str = ""
    selected_skills: list[str] = field(default_factory=list)
    memory_summary: str = ""
    tool_trace: list[str] = field(default_factory=list)
    memory_note: MemoryNote | None = None
    guest_profile_id: str = ""
    guest_event_kind: str = ""

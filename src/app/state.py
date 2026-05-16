from typing import Any, TypedDict

from langchain_core.messages import BaseMessage

from src.app.schemas import ChatEvent, FlightSnapshot, GuestEvent, GuestMatchDecision, GuestProfile, OperationalUpdate, TurnAction, WeatherContext


class AgentState(TypedDict, total=False):
    user_input: str
    event: ChatEvent
    messages: list[BaseMessage]
    memory_summary: str
    selected_skill_names: list[str]
    resolver_notes: str
    execution_plan: list[str]
    context_bundle: str
    action: TurnAction
    action_reason: str
    memory_candidate: str
    operational_update: OperationalUpdate | None
    guest_match: GuestMatchDecision | None
    guest_profile: GuestProfile | None
    guest_event: GuestEvent | None
    flight_snapshot: FlightSnapshot | None
    weather_context: WeatherContext | None
    enrichment_summary: str
    recommendation_reason: str
    final_response: str
    reply_content: str
    tool_trace: list[str]
    tool_rounds: int
    clarification_question: str
    last_turn: dict[str, str]
    debug: dict[str, Any]

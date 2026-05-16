from dataclasses import dataclass
from datetime import UTC, datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.app.classifier import ActionClassifier, ActionDecision
from src.app.config import Settings
from src.app.extractor import OperationalExtractor
from src.app.guests.matcher import GuestMatcher
from src.app.guests.store import GuestProfileStore
from src.app.recommender import RecommendationEngine, RecommendationDecision
from src.app.resolver.context_builder import build_context_bundle
from src.app.resolver.router import ResolverDecision, SkillResolver
from src.app.schemas import FlightSnapshot, GuestEvent, GuestMatchDecision, GuestProfile, MemoryNote, OperationalUpdate, Skill, WeatherContext
from src.app.state import AgentState
from src.app.tools.flight_status import FLIGHT_LINK_RE, format_flight_snapshot, get_cached_flight_status_result, normalize_flight_reference, parse_flight_reference_from_text
from src.app.tools.weather_lookup import WeatherLocationSummary, format_weather_summary, get_cached_weather_result


RECOMMENDATION_SKILLS = {
    "arrival_service_recommendations",
    "departure_service_recommendations",
    "repeat_pattern_recommendations",
    "travel_weather_context",
}


def _stringify_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


@dataclass
class GraphNodes:
    settings: Settings
    model_with_tools: object
    classifier: ActionClassifier
    extractor: OperationalExtractor
    guest_matcher: GuestMatcher
    guest_store: GuestProfileStore
    recommender: RecommendationEngine
    resolver: SkillResolver
    registry: object
    compressor: object
    harness_prompt: str
    max_tool_rounds: int
    tools_by_name: dict[str, object]

    def _format_event_context(self, state: AgentState) -> str:
        event = state["event"]
        return "\n".join(
            [
                f"source: {event.source}",
                f"surface: {event.surface}",
                f"is_mentioned: {event.is_mentioned}",
                f"sender_name: {event.sender_name}",
                f"sender_id: {event.sender_id}",
                f"conversation_id: {event.conversation_id}",
                f"channel_id: {event.channel_id or '(none)'}",
                f"team_id: {event.team_id or '(none)'}",
            ]
        )

    def _format_guest_profile(self, profile: GuestProfile | None) -> str:
        if profile is None:
            return ""
        lines = [
            f"guest_id: {profile.guest_id}",
            f"canonical_name: {profile.canonical_name}",
            f"aliases: {', '.join(profile.aliases) if profile.aliases else '(none)'}",
            f"status: {profile.status}",
            f"last_seen_at: {profile.last_seen_at or '(unknown)'}",
        ]
        if profile.profile_notes:
            lines.append("profile_notes:")
            lines.extend(f"- {note}" for note in profile.profile_notes[-5:])
        if profile.latest_flight:
            lines.append("latest_flight:")
            lines.append(format_flight_snapshot(profile.latest_flight))
        return "\n".join(lines)

    def _format_weather_context(self, weather_context: WeatherContext | None) -> str:
        if weather_context is None:
            return ""
        sections: list[str] = []
        if weather_context.departure is not None:
            sections.append("Departure weather:\n" + format_weather_summary(weather_context.departure))
        if weather_context.arrival is not None:
            sections.append("Arrival weather:\n" + format_weather_summary(weather_context.arrival))
        return "\n\n".join(sections)

    def _format_recent_timeline(self, profile: GuestProfile | None) -> str:
        if profile is None or not profile.timeline:
            return ""
        lines = []
        for event in profile.timeline[-6:]:
            lines.append(f"- {event.timestamp} | {event.event_kind} | {event.summary}")
        return "\n".join(lines)

    def resolve(self, state: AgentState) -> AgentState:
        decision: ResolverDecision = self.resolver.resolve_with_context(
            user_input=state["user_input"],
            memory_summary=state.get("memory_summary", ""),
            skills=self.registry.all(),
            extra_context=self._format_event_context(state),
        )

        return {
            "selected_skill_names": decision.selected_skills,
            "resolver_notes": decision.route_reason,
            "execution_plan": decision.execution_plan,
            "clarification_question": decision.clarification_question if decision.needs_clarification else "",
        }

    def build_context(self, state: AgentState) -> AgentState:
        selected_skills: list[Skill] = self.registry.get_many(state.get("selected_skill_names", []))
        bundle = build_context_bundle(
            selected_skills=selected_skills,
            memory_summary=state.get("memory_summary", ""),
            resolver_notes=state.get("resolver_notes", ""),
            execution_plan=state.get("execution_plan", []),
        )

        return {"context_bundle": bundle}

    def classify(self, state: AgentState) -> AgentState:
        decision: ActionDecision = self.classifier.classify(
            user_input=state["user_input"],
            event_context=self._format_event_context(state),
            context_bundle=state.get("context_bundle", ""),
        )
        return {
            "action": decision.action,
            "action_reason": decision.reason,
            "memory_candidate": decision.memory_candidate,
        }

    def extract_operational_update(self, state: AgentState) -> AgentState:
        if state.get("action") == "ignore":
            return {"operational_update": None}

        update = self.extractor.extract(
            user_input=state["user_input"],
            event_context=self._format_event_context(state),
            context_bundle=state.get("context_bundle", ""),
        )
        if not update.flight_reference:
            normalized = parse_flight_reference_from_text(state["user_input"])
            if normalized:
                update = OperationalUpdate(
                    **{
                        **update.__dict__,
                        "flight_reference": normalized,
                        "needs_arrival_lookup": True,
                    }
                )
        elif not normalize_flight_reference(update.flight_reference):
            update = OperationalUpdate(
                **{
                    **update.__dict__,
                    "flight_reference": "",
                    "needs_arrival_lookup": False,
                }
            )
        elif not update.needs_arrival_lookup:
            link_present = bool(update.flight_link and FLIGHT_LINK_RE.search(update.flight_link))
            explicit_flight_text = "flight" in state["user_input"].lower()
            if link_present or explicit_flight_text or update.event_kind.lower() == "flight":
                update = OperationalUpdate(
                    **{
                        **update.__dict__,
                        "needs_arrival_lookup": True,
                    }
                )
        return {"operational_update": update}

    def resolve_guest(self, state: AgentState) -> AgentState:
        update = state.get("operational_update")
        if update is None:
            return {"guest_match": None, "guest_profile": None}

        decision: GuestMatchDecision = self.guest_matcher.match(update)
        profile = None

        if decision.status == "created" and decision.guest_name and not (
            state["action"] == "reply" and state["user_input"].strip().endswith("?")
        ):
            profile = self.guest_store.create_profile(decision.guest_name)
            decision = GuestMatchDecision(
                status="created",
                guest_id=profile.guest_id,
                guest_name=profile.canonical_name,
                reasoning=decision.reasoning,
            )
        elif decision.status == "matched" and decision.guest_id:
            profile = self.guest_store.get(decision.guest_id)
        elif decision.status == "ambiguous":
            return {
                "guest_match": decision,
                "guest_profile": None,
                "action": "reply",
                "clarification_question": decision.clarification_question,
                "action_reason": decision.reasoning or state.get("action_reason", ""),
            }

        return {"guest_match": decision, "guest_profile": profile}

    def enrich_operational_update(self, state: AgentState) -> AgentState:
        update = state.get("operational_update")
        profile = state.get("guest_profile")
        tool_trace = list(state.get("tool_trace", []))

        if update is None:
            return {"tool_trace": tool_trace}

        flight_reference = update.flight_reference.strip()
        if not flight_reference and update.needs_arrival_lookup and profile and profile.latest_flight:
            flight_reference = profile.latest_flight.flight_reference

        if not flight_reference:
            return {"tool_trace": tool_trace}

        flight_tool = self.tools_by_name["flight_status"]
        try:
            if not self.settings.aviationstack_api_key:
                raise ValueError("AVIATIONSTACK_API_KEY is not configured.")
            lookup_result = get_cached_flight_status_result(
                flight_reference,
                self.settings.aviationstack_api_key,
                self.settings.http_timeout_seconds,
            )
            tool_output = flight_tool.invoke({"flight_reference": flight_reference})
            tool_trace.append(f"flight_status({flight_reference}) -> {tool_output}")
        except Exception as exc:
            tool_trace.append(f"flight_status({flight_reference}) -> ERROR: {exc}")
            return {"tool_trace": tool_trace, "enrichment_summary": ""}

        return {
            "tool_trace": tool_trace,
            "flight_snapshot": lookup_result.snapshot,
            "enrichment_summary": lookup_result.text,
        }

    def enrich_weather_context(self, state: AgentState) -> AgentState:
        flight_snapshot: FlightSnapshot | None = state.get("flight_snapshot")
        tool_trace = list(state.get("tool_trace", []))
        if flight_snapshot is None:
            return {"tool_trace": tool_trace}

        weather_tool = self.tools_by_name["weather_lookup"]
        weather_context = WeatherContext()

        def fetch(location: str) -> WeatherLocationSummary | None:
            if not location.strip():
                return None
            result = get_cached_weather_result(
                location.strip(),
                self.settings.weather_forecast_days,
                self.settings.http_timeout_seconds,
            )
            tool_output = weather_tool.invoke({"location": location})
            tool_trace.append(f"weather_lookup({location}) -> {tool_output}")
            return result.summary

        try:
            departure = fetch(flight_snapshot.departure_airport)
            arrival = fetch(flight_snapshot.arrival_airport)
        except Exception as exc:
            tool_trace.append(f"weather_lookup -> ERROR: {exc}")
            return {"tool_trace": tool_trace}

        weather_context = WeatherContext(departure=departure, arrival=arrival)
        sections = [state.get("enrichment_summary", "").strip()]
        formatted_weather = self._format_weather_context(weather_context)
        if formatted_weather:
            sections.append(formatted_weather)
        return {
            "tool_trace": tool_trace,
            "weather_context": weather_context,
            "enrichment_summary": "\n\n".join(section for section in sections if section),
        }

    def recommend_guest_moment(self, state: AgentState) -> AgentState:
        update = state.get("operational_update")
        profile = state.get("guest_profile")
        selected_skill_names = set(state.get("selected_skill_names", []))

        if state.get("action") == "reply":
            return {}
        if update is None or profile is None or not (selected_skill_names & RECOMMENDATION_SKILLS):
            return {}

        decision: RecommendationDecision = self.recommender.recommend(
            event_context=self._format_event_context(state),
            context_bundle=state.get("context_bundle", ""),
            guest_profile=self._format_guest_profile(profile),
            operational_update="\n".join(
                [
                    f"event_kind: {update.event_kind}",
                    f"summary: {update.summary}",
                    f"details: {update.details}",
                ]
            ),
            weather_context=self._format_weather_context(state.get("weather_context")),
            recent_timeline=self._format_recent_timeline(profile),
        )
        if not decision.should_reply or not decision.reply_text.strip():
            return {"recommendation_reason": decision.reason}

        return {
            "action": "reply",
            "final_response": decision.reply_text.strip(),
            "reply_content": decision.reply_text.strip(),
            "recommendation_reason": decision.reason,
            "action_reason": decision.reason or state.get("action_reason", ""),
        }

    def agent(self, state: AgentState) -> AgentState:
        if state.get("clarification_question"):
            return {
                "action": "reply",
                "final_response": state["clarification_question"],
                "reply_content": state["clarification_question"],
            }

        system_parts = [self.harness_prompt]
        context_bundle = state.get("context_bundle", "").strip()
        if context_bundle:
            system_parts.append(context_bundle)

        operational_update = state.get("operational_update")
        if operational_update is not None:
            system_parts.append(
                "## Operational Update\n"
                f"Guest related: {operational_update.is_guest_related}\n"
                f"Guest candidates: {', '.join(operational_update.guest_name_candidates) or '(none)'}\n"
                f"Event kind: {operational_update.event_kind}\n"
                f"Summary: {operational_update.summary or '(none)'}\n"
                f"Details: {operational_update.details or '(none)'}"
            )

        profile = state.get("guest_profile")
        guest_profile_block = self._format_guest_profile(profile)
        if guest_profile_block:
            system_parts.append("## Guest Profile\n" + guest_profile_block)

        enrichment_summary = state.get("enrichment_summary", "").strip()
        if enrichment_summary:
            system_parts.append("## Enrichment\n" + enrichment_summary)

        system_message = SystemMessage(content="\n\n".join(system_parts))
        input_messages = [system_message, *state["messages"]]
        response: AIMessage = self.model_with_tools.invoke(input_messages)

        return {"messages": [*state["messages"], response]}

    def run_tools(self, state: AgentState) -> AgentState:
        last_message = state["messages"][-1]
        tool_messages: list[ToolMessage] = []
        tool_trace = list(state.get("tool_trace", []))

        for tool_call in last_message.tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            result = tool.invoke(tool_call["args"])
            tool_trace.append(f"{tool_call['name']}({tool_call['args']}) -> {result}")
            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"],
                )
            )

        return {
            "messages": [*state["messages"], *tool_messages],
            "tool_trace": tool_trace,
            "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    def finalize(self, state: AgentState) -> AgentState:
        action = state["action"]
        update: OperationalUpdate | None = state.get("operational_update")
        guest_profile: GuestProfile | None = state.get("guest_profile")
        guest_match: GuestMatchDecision | None = state.get("guest_match")
        flight_snapshot: FlightSnapshot | None = state.get("flight_snapshot")
        weather_context: WeatherContext | None = state.get("weather_context")

        memory_note = None
        candidate = state.get("memory_candidate", "").strip()
        if candidate:
            event = state["event"]
            memory_note = MemoryNote(
                timestamp=datetime.now(UTC).isoformat(),
                source=event.source,
                surface=event.surface,
                sender_id=event.sender_id,
                sender_name=event.sender_name,
                conversation_id=event.conversation_id,
                channel_id=event.channel_id,
                team_id=event.team_id,
                message_id=event.message_id,
                original_text=event.text,
                note=candidate,
            )

        guest_profile_id = ""
        guest_event_kind = ""

        should_persist_guest_event = (
            guest_profile is not None
            and update is not None
            and update.summary.strip()
            and (action == "memorize" or not state["user_input"].strip().endswith("?"))
        )
        if should_persist_guest_event:
            event = state["event"]
            guest_event = GuestEvent(
                timestamp=datetime.now(UTC).isoformat(),
                source=event.source,
                surface=event.surface,
                sender_id=event.sender_id,
                sender_name=event.sender_name,
                conversation_id=event.conversation_id,
                channel_id=event.channel_id,
                team_id=event.team_id,
                message_id=event.message_id,
                event_kind=update.event_kind,
                summary=update.summary,
                details=update.details or update.summary,
                raw_text=event.text,
                stay_phase=update.stay_phase,
                confidence_note=(guest_match.reasoning if guest_match else ""),
                flight_snapshot=flight_snapshot,
                weather_context=weather_context,
            )
            updated_profile = self.guest_store.append_event(
                guest_profile,
                guest_event,
                profile_note=candidate or update.summary,
                latest_flight=flight_snapshot,
            )
            guest_profile = updated_profile
            guest_profile_id = updated_profile.guest_id
            guest_event_kind = guest_event.event_kind

        if action != "reply":
            return {
                "reply_content": "",
                "final_response": "",
                "memory_note": memory_note,
                "guest_profile_id": guest_profile_id,
                "guest_event_kind": guest_event_kind,
                "last_turn": {
                    "user_input": state["user_input"],
                    "assistant_output": "",
                },
            }

        if state.get("final_response"):
            final_response = state["final_response"]
        else:
            last_ai = next(
                (
                    message
                    for message in reversed(state["messages"])
                    if isinstance(message, AIMessage) and not message.tool_calls
                ),
                None,
            )
            final_response = (
                _stringify_content(last_ai.content)
                if last_ai is not None
                else "I could not complete the tool-assisted response cleanly."
            )

        last_user = next(
            message for message in reversed(state["messages"]) if isinstance(message, HumanMessage)
        )

        return {
            "final_response": final_response,
            "reply_content": final_response,
            "memory_note": memory_note,
            "guest_profile_id": guest_profile_id,
            "guest_event_kind": guest_event_kind,
            "last_turn": {
                "user_input": _stringify_content(last_user.content),
                "assistant_output": final_response,
            },
        }

    def summarize(self, state: AgentState) -> AgentState:
        if state["action"] == "ignore":
            return {"memory_summary": state.get("memory_summary", "")}

        last_turn = state["last_turn"]
        update = state.get("operational_update")
        candidate = (state.get("memory_candidate", "") or "").strip()
        if update is not None and update.summary and update.summary not in candidate:
            candidate = f"{candidate} | {update.summary}".strip(" |")
        updated_summary = self.compressor.compress(
            memory_summary=state.get("memory_summary", ""),
            user_input=last_turn["user_input"],
            action=state["action"],
            assistant_output=last_turn["assistant_output"],
            memory_note=candidate,
        )
        return {"memory_summary": updated_summary}

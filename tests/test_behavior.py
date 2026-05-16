import asyncio
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.adapters.teams import TeamsAdapter, normalize_teams_activity
from src.app.agent import ReactSkillAgent, build_chat_model
from src.app.config import Settings
from src.app.graph.nodes import GraphNodes
from src.app.guests.store import GuestProfileStore
from src.app.memory.note_store import MemoryNoteStore
from src.app.memory.session import SessionMemory
from src.app.memory.session_store import SessionStore
from src.app.schemas import ChatEvent, FlightSnapshot, GuestEvent, GuestProfile, MemoryNote, OperationalUpdate, TurnResult, WeatherContext, WeatherLocationSummary
from src.app.tracing import build_runnable_config, format_tracing_status
from src.app.tools.flight_status import parse_flight_reference_from_text


class BehaviorTests(unittest.TestCase):
    def test_build_chat_model_selects_openai_provider(self) -> None:
        captured = {}

        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        with patch.dict(sys.modules, {"langchain_openai": SimpleNamespace(ChatOpenAI=FakeChatOpenAI)}):
            model = build_chat_model(
                Settings(model_provider="openai", openai_model="gpt-4o-mini", temperature=0.25)
            )

        self.assertIsInstance(model, FakeChatOpenAI)
        self.assertEqual(captured["model"], "gpt-4o-mini")
        self.assertEqual(captured["temperature"], 0.25)

    def test_build_chat_model_selects_anthropic_provider(self) -> None:
        captured = {}

        class FakeChatAnthropic:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        with patch.dict(sys.modules, {"langchain_anthropic": SimpleNamespace(ChatAnthropic=FakeChatAnthropic)}):
            model = build_chat_model(
                Settings(
                    model_provider="anthropic",
                    anthropic_model="claude-3-5-sonnet-latest",
                    temperature=0.15,
                )
            )

        self.assertIsInstance(model, FakeChatAnthropic)
        self.assertEqual(captured["model"], "claude-3-5-sonnet-latest")
        self.assertEqual(captured["temperature"], 0.15)

    def test_build_chat_model_rejects_unknown_provider(self) -> None:
        with self.assertRaises(ValueError):
            build_chat_model(Settings(model_provider="bogus"))

    def test_session_memory_ignores_ignore_action(self) -> None:
        session = SessionMemory()
        event = ChatEvent(
            text="ambient chatter",
            source="teams",
            surface="channel",
            is_mentioned=False,
            sender_id="u1",
            sender_name="User",
            conversation_id="c1",
        )
        result = TurnResult(action="ignore")

        session.apply_result(result, event)

        self.assertEqual(session.messages, [])
        self.assertEqual(session.memory_summary, "")

    def test_session_memory_updates_on_memorize(self) -> None:
        session = SessionMemory()
        event = ChatEvent(
            text="I prefer SMS reminders",
            source="teams",
            surface="personal",
            is_mentioned=True,
            sender_id="u1",
            sender_name="User",
            conversation_id="c1",
        )
        result = TurnResult(action="memorize", memory_summary="- prefers SMS reminders")

        session.apply_result(result, event)

        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.memory_summary, "- prefers SMS reminders")

    def test_note_store_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryNoteStore(Path(tmpdir) / "notes.jsonl")
            note = MemoryNote(
                timestamp="2026-01-01T00:00:00+00:00",
                source="teams",
                surface="channel",
                sender_id="u1",
                sender_name="User",
                conversation_id="c1",
                channel_id="ch1",
                team_id="t1",
                message_id="m1",
                original_text="remember this",
                note="User prefers aisle seats",
            )
            store.append(note)

            data = (Path(tmpdir) / "notes.jsonl").read_text(encoding="utf-8").strip()
            payload = json.loads(data)
            self.assertEqual(payload["note"], "User prefers aisle seats")

    def test_guest_profile_store_prefers_recent_arriving_guest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GuestProfileStore(Path(tmpdir))
            stale = GuestProfile(
                guest_id="michael-old",
                canonical_name="Michael Carter",
                status="departed",
                last_seen_at=(datetime.now(UTC) - timedelta(days=120)).isoformat(),
            )
            current = GuestProfile(
                guest_id="michael-current",
                canonical_name="Michael Carter",
                status="arriving",
                last_seen_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            )
            store.save(stale)
            store.save(current)

            candidates = store.find_candidates(["Michael Carter"])

            self.assertGreaterEqual(len(candidates), 2)
            self.assertEqual(candidates[0].guest_id, "michael-current")

    def test_guest_profile_store_appends_event_and_updates_flight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GuestProfileStore(Path(tmpdir))
            profile = GuestProfile(
                guest_id="sarah-1",
                canonical_name="Sarah Lee",
            )
            store.save(profile)
            snapshot = FlightSnapshot(
                flight_reference="DL234",
                status="active",
                estimated_arrival="2026-05-16T18:10:00+00:00",
            )
            guest_event = GuestEvent(
                timestamp=datetime.now(UTC).isoformat(),
                source="teams",
                surface="channel",
                sender_id="u1",
                sender_name="Staff",
                conversation_id="c1",
                channel_id="ch1",
                team_id="t1",
                message_id="m1",
                event_kind="flight",
                summary="Sarah Lee is arriving on DL234.",
                details="Airport pickup requested.",
                raw_text="Sarah Lee is arriving on DL234. Airport pickup requested.",
                stay_phase="arrival",
                flight_snapshot=snapshot,
            )

            updated = store.append_event(profile, guest_event, profile_note="Airport pickup requested.", latest_flight=snapshot)

            self.assertEqual(updated.status, "arriving")
            self.assertEqual(updated.latest_flight.flight_reference, "DL234")
            self.assertEqual(updated.timeline[-1].event_kind, "flight")

    def test_guest_profile_store_round_trips_weather_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GuestProfileStore(Path(tmpdir))
            profile = GuestProfile(guest_id="ray-1", canonical_name="Ray")
            store.save(profile)
            guest_event = GuestEvent(
                timestamp=datetime.now(UTC).isoformat(),
                source="teams",
                surface="channel",
                sender_id="u1",
                sender_name="Staff",
                conversation_id="c1",
                channel_id="ch1",
                team_id="t1",
                message_id="m1",
                event_kind="Arrival Update",
                summary="Ray is arriving tonight.",
                details="Weather-aware arrival prep suggested.",
                raw_text="Ray is arriving tonight.",
                stay_phase="arrival",
                weather_context=WeatherContext(
                    departure=WeatherLocationSummary(query="Philadelphia", resolved_name="Philadelphia, Pennsylvania, United States"),
                    arrival=WeatherLocationSummary(query="San Francisco", resolved_name="San Francisco, California, United States"),
                ),
            )
            store.append_event(profile, guest_event)

            loaded = store.get("ray-1")

            assert loaded is not None
            self.assertEqual(loaded.status, "arriving")
            self.assertEqual(loaded.timeline[-1].weather_context.arrival.resolved_name, "San Francisco, California, United States")

    def test_guest_profile_store_marks_checked_in_guest_as_on_property(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GuestProfileStore(Path(tmpdir))
            profile = GuestProfile(guest_id="frank-1", canonical_name="Frank Espaillat")
            store.save(profile)

            arrival_event = GuestEvent(
                timestamp=datetime.now(UTC).isoformat(),
                source="teams",
                surface="channel",
                sender_id="u1",
                sender_name="Staff",
                conversation_id="c1",
                channel_id="ch1",
                team_id="t1",
                message_id="m1",
                event_kind="Arrival Update",
                summary="Frank is arriving tonight.",
                details="Expected around 11 PM.",
                raw_text="Frank is arriving tonight.",
                stay_phase="arrival",
            )
            checked_in_event = GuestEvent(
                timestamp=datetime.now(UTC).isoformat(),
                source="teams",
                surface="channel",
                sender_id="u1",
                sender_name="Staff",
                conversation_id="c1",
                channel_id="ch1",
                team_id="t1",
                message_id="m2",
                event_kind="Arrival Update",
                summary="Frank is checked into room 205.",
                details="He requested it for the pool view.",
                raw_text="Frank just arrived and he is checked into room 205.",
                stay_phase="on_property",
            )

            after_arrival = store.append_event(profile, arrival_event)
            after_check_in = store.append_event(after_arrival, checked_in_event)

            self.assertEqual(after_arrival.status, "arriving")
            self.assertEqual(after_check_in.status, "on_property")

    def test_guest_profile_store_keeps_on_property_for_mid_stay_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GuestProfileStore(Path(tmpdir))
            profile = GuestProfile(
                guest_id="frank-1",
                canonical_name="Frank Espaillat",
                status="on_property",
            )
            store.save(profile)

            run_event = GuestEvent(
                timestamp=datetime.now(UTC).isoformat(),
                source="teams",
                surface="channel",
                sender_id="u1",
                sender_name="Staff",
                conversation_id="c1",
                channel_id="ch1",
                team_id="t1",
                message_id="m3",
                event_kind="activity",
                summary="Frank went for a run.",
                details="He mentioned that his goal is a mile.",
                raw_text="Frank went for a run, he mentioned that his goal is a mile.",
                stay_phase="on_property",
            )

            updated = store.append_event(profile, run_event)

            self.assertEqual(updated.status, "on_property")

    def test_enrichment_invokes_flight_status_tool(self) -> None:
        class FakeTool:
            def __init__(self):
                self.calls = []

            def invoke(self, payload):
                self.calls.append(payload)
                return "Flight: AA2797\nStatus: scheduled"

        fake_tool = FakeTool()
        nodes = GraphNodes(
            settings=Settings(aviationstack_api_key="test-key"),
            model_with_tools=None,
            classifier=None,
            extractor=None,
            guest_matcher=None,
            guest_store=GuestProfileStore(Path("/tmp/unused")),
            recommender=None,
            resolver=None,
            registry=None,
            compressor=None,
            harness_prompt="",
            max_tool_rounds=3,
            tools_by_name={"flight_status": fake_tool, "weather_lookup": fake_tool},
        )
        with patch("src.app.graph.nodes.get_cached_flight_status_result") as lookup_mock:
            lookup_mock.return_value = SimpleNamespace(
                snapshot=FlightSnapshot(
                    flight_reference="AA2797",
                    airline="American Airlines",
                    status="scheduled",
                    arrival_airport="San Francisco International",
                ),
                text="Flight: AA2797\nStatus: scheduled",
            )
            result = nodes.enrich_operational_update(
                {
                    "operational_update": OperationalUpdate(
                        is_guest_related=True,
                        guest_name_candidates=["Ray"],
                        event_kind="flight",
                        summary="Ray is arriving today around 9 PM.",
                        details="Flight AA 2797 is scheduled for arrival.",
                        flight_reference="AA2797",
                        needs_arrival_lookup=True,
                    ),
                    "tool_trace": [],
                }
            )

        lookup_mock.assert_called_once()
        self.assertEqual(fake_tool.calls, [{"flight_reference": "AA2797"}])
        self.assertIn("flight_status(AA2797)", result["tool_trace"][0])
        self.assertEqual(result["flight_snapshot"].flight_reference, "AA2797")

    def test_parse_flight_reference_ignores_arriving_in_minutes_phrase(self) -> None:
        self.assertEqual(parse_flight_reference_from_text("Ray is arriving in 15 minutes."), "")

    def test_parse_flight_reference_keeps_explicit_flight_reference(self) -> None:
        self.assertEqual(parse_flight_reference_from_text("Ray is arriving on AA2797 tonight."), "AA2797")

    def test_extract_operational_update_skips_arrival_lookup_without_valid_flight_reference(self) -> None:
        class FakeExtractor:
            def extract(self, **_kwargs):
                return OperationalUpdate(
                    is_guest_related=True,
                    guest_name_candidates=["Ray"],
                    event_kind="Arrival Update",
                    summary="Ray is arriving in 15 minutes.",
                    details="Front desk should be ready.",
                    stay_phase="arrival",
                    flight_reference="",
                    needs_arrival_lookup=False,
                )

        nodes = GraphNodes(
            settings=Settings(),
            model_with_tools=None,
            classifier=None,
            extractor=FakeExtractor(),
            guest_matcher=None,
            guest_store=GuestProfileStore(Path("/tmp/unused")),
            recommender=None,
            resolver=None,
            registry=None,
            compressor=None,
            harness_prompt="",
            max_tool_rounds=3,
            tools_by_name={"flight_status": object(), "weather_lookup": object()},
        )

        result = nodes.extract_operational_update(
            {
                "user_input": "Ray is arriving in 15 minutes.",
                "event": ChatEvent(
                    text="Ray is arriving in 15 minutes.",
                    source="teams",
                    surface="channel",
                    is_mentioned=False,
                    sender_id="u1",
                    sender_name="Staff",
                    conversation_id="c1",
                ),
                "context_bundle": "",
                "action": "memorize",
            }
        )

        self.assertEqual(result["operational_update"].flight_reference, "")
        self.assertFalse(result["operational_update"].needs_arrival_lookup)

    def test_weather_enrichment_invokes_weather_lookup_tool(self) -> None:
        class FakeWeatherTool:
            def __init__(self):
                self.calls = []

            def invoke(self, payload):
                self.calls.append(payload)
                return "Location: Philadelphia\nCurrent: 18C, clear"

        weather_tool = FakeWeatherTool()
        nodes = GraphNodes(
            settings=Settings(weather_forecast_days=3),
            model_with_tools=None,
            classifier=None,
            extractor=None,
            guest_matcher=None,
            guest_store=GuestProfileStore(Path("/tmp/unused")),
            recommender=None,
            resolver=None,
            registry=None,
            compressor=None,
            harness_prompt="",
            max_tool_rounds=3,
            tools_by_name={"flight_status": weather_tool, "weather_lookup": weather_tool},
        )
        flight_snapshot = FlightSnapshot(
            flight_reference="AA2797",
            departure_airport="Philadelphia International",
            arrival_airport="San Francisco International",
        )
        with patch("src.app.graph.nodes.get_cached_weather_result") as weather_lookup_mock:
            weather_lookup_mock.side_effect = [
                SimpleNamespace(
                    summary=WeatherLocationSummary(
                        query="Philadelphia International",
                        resolved_name="Philadelphia International",
                        current_temperature_c="18",
                        current_weather="clear",
                        forecast_summary=["2026-05-16: clear, high 22C, low 14C"],
                    ),
                    text="Location: Philadelphia International\nCurrent: 18C, clear",
                ),
                SimpleNamespace(
                    summary=WeatherLocationSummary(
                        query="San Francisco International",
                        resolved_name="San Francisco International",
                        current_temperature_c="14",
                        current_weather="foggy",
                        forecast_summary=["2026-05-16: foggy, high 16C, low 11C"],
                    ),
                    text="Location: San Francisco International\nCurrent: 14C, foggy",
                ),
            ]
            result = nodes.enrich_weather_context(
                {
                    "flight_snapshot": flight_snapshot,
                    "tool_trace": [],
                    "enrichment_summary": "Flight info here",
                }
            )

        self.assertEqual(
            weather_tool.calls,
            [
                {"location": "Philadelphia International"},
                {"location": "San Francisco International"},
            ],
        )
        self.assertEqual(result["weather_context"].departure.query, "Philadelphia International")
        self.assertIn("Departure weather", result["enrichment_summary"])

    def test_recommendation_runs_for_repeat_pattern_skill_on_property_update(self) -> None:
        class FakeRecommender:
            def recommend(self, **_kwargs):
                return SimpleNamespace(
                    should_reply=True,
                    reason="Recurring pattern on property.",
                    reply_text="Ray is on property and often wants a recovery snack after a run. Offer bottled water and a light snack.",
                )

        nodes = GraphNodes(
            settings=Settings(),
            model_with_tools=None,
            classifier=None,
            extractor=None,
            guest_matcher=None,
            guest_store=GuestProfileStore(Path("/tmp/unused")),
            recommender=FakeRecommender(),
            resolver=None,
            registry=None,
            compressor=None,
            harness_prompt="",
            max_tool_rounds=3,
            tools_by_name={"flight_status": object(), "weather_lookup": object()},
        )
        profile = GuestProfile(
            guest_id="ray-1",
            canonical_name="Ray",
            profile_notes=["Prefers bourbon in the evening."],
            timeline=[
                GuestEvent(
                    timestamp=datetime.now(UTC).isoformat(),
                    source="teams",
                    surface="channel",
                    sender_id="u1",
                    sender_name="Staff",
                    conversation_id="c1",
                    channel_id="ch1",
                    team_id="t1",
                    message_id="m1",
                    event_kind="drink",
                    summary="Ray ordered bourbon after dinner.",
                    details="Maker's Mark on the rocks.",
                    raw_text="Ray ordered bourbon after dinner.",
                )
            ],
        )
        result = nodes.recommend_guest_moment(
            {
                "action": "memorize",
                "event": ChatEvent(
                    text="Ray went for a run and mentioned his goal is a mile",
                    source="teams",
                    surface="channel",
                    is_mentioned=False,
                    sender_id="u1",
                    sender_name="Staff",
                    conversation_id="c1",
                ),
                "context_bundle": "",
                "operational_update": OperationalUpdate(
                    is_guest_related=True,
                    guest_name_candidates=["Ray"],
                    event_kind="activity",
                    summary="Ray went for a run.",
                    details="He mentioned that his goal is a mile.",
                    stay_phase="on_property",
                ),
                "guest_profile": profile,
                "selected_skill_names": ["repeat_pattern_recommendations"],
                "weather_context": WeatherContext(
                    departure=WeatherLocationSummary(query="Philadelphia", resolved_name="Philadelphia", current_temperature_c="18", current_weather="clear"),
                    arrival=WeatherLocationSummary(query="San Francisco", resolved_name="San Francisco", current_temperature_c="14", current_weather="foggy"),
                ),
            }
        )

        self.assertEqual(result["action"], "reply")
        self.assertIn("recovery snack", result["reply_content"])
        self.assertIn("bottled water", result["reply_content"])

    def test_agent_returns_all_actions_from_graph(self) -> None:
        class FakeGraph:
            def __init__(self, action: str):
                self.action = action
                self.last_config = None

            def invoke(self, _state, config=None):
                self.last_config = config
                return {
                    "action": self.action,
                    "final_response": "hello" if self.action == "reply" else "",
                    "reply_content": "hello" if self.action == "reply" else "",
                    "action_reason": "test",
                    "selected_skill_names": [],
                    "memory_summary": "summary" if self.action != "ignore" else "",
                    "tool_trace": [],
                    "memory_note": None,
                    "guest_profile_id": "",
                    "guest_event_kind": "",
                }

        event = ChatEvent(
            text="test",
            source="cli",
            surface="personal",
            is_mentioned=True,
            sender_id="cli-user",
            sender_name="CLI User",
            conversation_id="cli",
        )

        for action in ("reply", "memorize", "ignore"):
            graph = FakeGraph(action)
            agent = ReactSkillAgent(graph=graph)
            result = agent.handle_event(event, SessionMemory())
            self.assertEqual(result.action, action)
            self.assertEqual(graph.last_config["run_name"], "react_skill_agent_turn")
            self.assertEqual(graph.last_config["tags"], ["langgraph-react-skill-chatbot"])
            self.assertEqual(
                graph.last_config["metadata"],
                {
                    "source": "cli",
                    "surface": "personal",
                    "conversation_id": "cli",
                    "channel_id": "",
                    "team_id": "",
                },
            )

    def test_teams_adapter_dispatches_reply_only(self) -> None:
        class FakeAgent:
            def __init__(self, result):
                self.result = result
                self.events = []

            def handle_event(self, event, session):
                self.events.append((event, session))
                return self.result

        class FakeCtx:
            def __init__(self):
                self.activity = SimpleNamespace(
                    text="<at>Echo Bot</at> what time is it?",
                    id="m1",
                    from_=SimpleNamespace(id="u1", name="User"),
                    recipient=SimpleNamespace(id="bot1", name="Echo Bot"),
                    conversation=SimpleNamespace(id="c1", conversation_type="channel"),
                    channel_data=SimpleNamespace(
                        channel=SimpleNamespace(id="ch1"),
                        team=SimpleNamespace(id="t1"),
                    ),
                )
                self.sent = []

            async def send(self, text):
                self.sent.append(text)

        reply_result = TurnResult(action="reply", reply_content="Hi there")
        memorize_result = TurnResult(action="memorize")
        ignore_result = TurnResult(action="ignore")

        for result, expected_messages in (
            (reply_result, ["Hi there"]),
            (memorize_result, []),
            (ignore_result, []),
        ):
            ctx = FakeCtx()
            adapter = TeamsAdapter(agent=FakeAgent(result), sessions=SessionStore())
            asyncio.run(adapter.handle_message(ctx))
            self.assertEqual(ctx.sent, expected_messages)

    def test_normalize_teams_activity_extracts_metadata(self) -> None:
        activity = SimpleNamespace(
            text="<at>Echo Bot</at> can you help?",
            id="m1",
            from_=SimpleNamespace(id="u1", name="User"),
            recipient=SimpleNamespace(id="bot1", name="Echo Bot"),
            conversation=SimpleNamespace(id="c1", conversation_type="groupChat"),
            channel_data=SimpleNamespace(
                channel=SimpleNamespace(id="ch1"),
                team=SimpleNamespace(id="t1"),
            ),
        )

        event = normalize_teams_activity(activity)

        self.assertEqual(event.surface, "group_chat")
        self.assertTrue(event.is_mentioned)
        self.assertEqual(event.team_id, "t1")

    def test_tracing_helper_formats_root_config(self) -> None:
        event = ChatEvent(
            text="hello",
            source="teams",
            surface="channel",
            is_mentioned=True,
            sender_id="u1",
            sender_name="User",
            conversation_id="c1",
            channel_id="ch1",
            team_id="t1",
        )

        config = build_runnable_config(event)

        self.assertEqual(config["run_name"], "react_skill_agent_turn")
        self.assertEqual(config["tags"], ["langgraph-react-skill-chatbot"])
        self.assertEqual(config["metadata"]["team_id"], "t1")

    def test_settings_reads_langsmith_env(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "LANGSMITH_TRACING": "true",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_WORKSPACE_ID": "ws_123",
                "LANGCHAIN_BASE_URL": "https://eu.api.smith.langchain.com",
                "LANGCHAIN_CALLBACKS_BACKGROUND": "false",
            },
            clear=False,
        ):
            settings = Settings()

        self.assertTrue(settings.langsmith_tracing)
        self.assertEqual(settings.langsmith_project, "test-project")
        self.assertEqual(settings.langsmith_workspace_id, "ws_123")
        self.assertEqual(settings.langsmith_api_url, "https://eu.api.smith.langchain.com")
        self.assertEqual(settings.langchain_callbacks_background, "false")

    def test_format_tracing_status_reflects_settings(self) -> None:
        fake_settings = Settings(
            langsmith_tracing=True,
            langsmith_project="debug-project",
        )

        with patch("src.app.tracing.settings", fake_settings):
            self.assertEqual(
                format_tracing_status(),
                "LangSmith tracing: enabled (project: debug-project)",
            )


if __name__ == "__main__":
    unittest.main()

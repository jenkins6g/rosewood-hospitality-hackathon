from src.app.classifier import ActionClassifier
from src.app.config import settings
from src.app.extractor import OperationalExtractor
from src.app.graph.builder import build_graph
from src.app.graph.nodes import GraphNodes
from src.app.guests.matcher import GuestMatcher
from src.app.guests.store import GuestProfileStore
from src.app.memory.compressor import MemoryCompressor
from src.app.memory.note_store import MemoryNoteStore
from src.app.memory.session import SessionMemory
from src.app.prompts import load_prompt
from src.app.recommender import RecommendationEngine
from src.app.resolver.router import SkillResolver
from src.app.schemas import ChatEvent, TurnResult
from src.app.skills.registry import SkillRegistry
from src.app.tracing import build_runnable_config
from src.app.tools.registry import build_toolset


def build_chat_model(active_settings):
    if active_settings.model_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=active_settings.model_name,
            temperature=active_settings.temperature,
        )

    if active_settings.model_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=active_settings.model_name,
            temperature=active_settings.temperature,
        )

    raise ValueError(
        f"Unsupported MODEL_PROVIDER: {active_settings.model_provider}. "
        "Expected one of: openai, anthropic."
    )


class ReactSkillAgent:
    def __init__(
        self,
        graph=None,
        note_store: MemoryNoteStore | None = None,
        guest_store: GuestProfileStore | None = None,
    ) -> None:
        self.note_store = note_store or MemoryNoteStore(settings.memory_notes_path)
        self.guest_store = guest_store or GuestProfileStore(settings.guest_profiles_dir)
        if graph is not None:
            self.graph = graph
            return

        registry = SkillRegistry(settings.skill_dir)
        tools, _ = build_toolset(settings, settings.skill_dir)

        model = build_chat_model(settings)

        harness_prompt = load_prompt(settings.prompt_dir / "harness.md")
        resolver_prompt = load_prompt(settings.prompt_dir / "resolver.md")
        summarizer_prompt = load_prompt(settings.prompt_dir / "summarizer.md")
        classifier_prompt = load_prompt(settings.prompt_dir / "classifier.md")
        recommendation_prompt = load_prompt(settings.prompt_dir / "recommendation.md")

        resolver = SkillResolver(
            model=model,
            resolver_prompt=resolver_prompt,
            max_selected_skills=settings.max_selected_skills,
        )
        classifier = ActionClassifier(
            model=model,
            classifier_prompt=classifier_prompt,
        )
        extractor = OperationalExtractor(model=model)
        guest_matcher = GuestMatcher(model=model, store=self.guest_store)
        recommender = RecommendationEngine(
            model=model,
            recommendation_prompt=recommendation_prompt,
        )
        compressor = MemoryCompressor(
            model=model,
            summarizer_prompt=summarizer_prompt,
            max_points=settings.memory_max_points,
        )

        nodes = GraphNodes(
            settings=settings,
            model_with_tools=model.bind_tools(tools),
            classifier=classifier,
            extractor=extractor,
            guest_matcher=guest_matcher,
            guest_store=self.guest_store,
            recommender=recommender,
            resolver=resolver,
            registry=registry,
            compressor=compressor,
            harness_prompt=harness_prompt,
            max_tool_rounds=settings.max_tool_rounds,
            tools_by_name={tool.name: tool for tool in tools},
        )
        self.graph = build_graph(nodes)

    def handle_event(self, event: ChatEvent, session: SessionMemory) -> TurnResult:
        state = session.build_state(event)
        state["debug"] = {"max_tool_rounds": settings.max_tool_rounds}
        result = self.graph.invoke(state, config=build_runnable_config(event))

        turn_result = TurnResult(
            action=result["action"],
            content=result.get("final_response", ""),
            reply_content=result.get("reply_content") or None,
            reason=result.get("action_reason", ""),
            selected_skills=result.get("selected_skill_names", []),
            memory_summary=result.get("memory_summary", ""),
            tool_trace=result.get("tool_trace", []),
            memory_note=result.get("memory_note"),
            guest_profile_id=result.get("guest_profile_id", ""),
            guest_event_kind=result.get("guest_event_kind", ""),
        )
        session.apply_result(turn_result, event=event)
        if turn_result.memory_note is not None:
            self.note_store.append(turn_result.memory_note)
        return turn_result

    def reply(self, user_input: str, session: SessionMemory) -> TurnResult:
        event = ChatEvent(
            text=user_input,
            source="cli",
            surface="personal",
            is_mentioned=True,
            sender_id="cli-user",
            sender_name="CLI User",
            conversation_id="cli-session",
        )
        return self.handle_event(event, session)

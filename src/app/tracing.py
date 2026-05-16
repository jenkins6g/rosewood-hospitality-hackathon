from src.app.config import settings
from src.app.schemas import ChatEvent


def build_runnable_config(event: ChatEvent) -> dict[str, object]:
    return {
        "run_name": "react_skill_agent_turn",
        "tags": ["langgraph-react-skill-chatbot"],
        "metadata": {
            "source": event.source,
            "surface": event.surface,
            "conversation_id": event.conversation_id,
            "channel_id": event.channel_id,
            "team_id": event.team_id,
        },
    }


def format_tracing_status() -> str:
    status = "enabled" if settings.langsmith_tracing else "disabled"
    return f"LangSmith tracing: {status} (project: {settings.langsmith_project})"

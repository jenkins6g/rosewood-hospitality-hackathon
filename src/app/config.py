import os
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    app_name: str = "langgraph-react-skill-chatbot"
    model_provider: str = field(default_factory=lambda: os.getenv("MODEL_PROVIDER", "openai").strip().lower())
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    )
    temperature: float = field(default_factory=lambda: float(os.getenv("MODEL_TEMPERATURE", "0.1")))
    max_tool_rounds: int = field(default_factory=lambda: int(os.getenv("MAX_TOOL_ROUNDS", "3")))
    max_selected_skills: int = field(default_factory=lambda: int(os.getenv("MAX_SELECTED_SKILLS", "2")))
    history_window: int = field(default_factory=lambda: int(os.getenv("HISTORY_WINDOW", "8")))
    memory_max_points: int = field(default_factory=lambda: int(os.getenv("MEMORY_MAX_POINTS", "8")))
    docs_lookup_k: int = field(default_factory=lambda: int(os.getenv("DOCS_LOOKUP_K", "3")))
    teams_port: int = field(default_factory=lambda: int(os.getenv("TEAMS_PORT", "3978")))
    http_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("HTTP_TIMEOUT_SECONDS", "8")))
    web_search_max_results: int = field(default_factory=lambda: int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5")))
    weather_forecast_days: int = field(default_factory=lambda: int(os.getenv("WEATHER_FORECAST_DAYS", "3")))
    tavily_api_key: str | None = field(default_factory=lambda: _get_optional("TAVILY_API_KEY"))
    aviationstack_api_key: str | None = field(default_factory=lambda: _get_optional("AVIATIONSTACK_API_KEY"))
    langsmith_tracing: bool = field(default_factory=lambda: _get_bool("LANGSMITH_TRACING", default=False))
    langsmith_project: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "langgraph-react-skill-chatbot")
    )
    langsmith_workspace_id: str | None = field(
        default_factory=lambda: _get_optional("LANGSMITH_WORKSPACE_ID")
    )
    langsmith_api_url: str | None = field(default_factory=lambda: _get_optional("LANGCHAIN_BASE_URL"))
    langchain_callbacks_background: str | None = field(
        default_factory=lambda: _get_optional("LANGCHAIN_CALLBACKS_BACKGROUND")
    )
    memory_notes_path: Path = PROJECT_ROOT / "var" / "memory_notes.jsonl"
    guest_profiles_dir: Path = PROJECT_ROOT / "var" / "guest_profiles"
    prompt_dir: Path = PROJECT_ROOT / "src" / "app" / "prompts"
    skill_dir: Path = PROJECT_ROOT / "src" / "app" / "skills"
    docs_paths: tuple[Path, ...] = (
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "REACT_CHATBOT_LANGCHAIN_PYTHON_SCAFFOLD.md",
    )

    @property
    def model_name(self) -> str:
        if self.model_provider == "anthropic":
            return self.anthropic_model
        return self.openai_model


settings = Settings()

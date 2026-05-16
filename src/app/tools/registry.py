from pathlib import Path

from langchain_core.tools import BaseTool

from src.app.config import Settings
from src.app.tools.calculator import calculator
from src.app.tools.clock import clock
from src.app.tools.docs_lookup import DocsLookupIndex, build_docs_lookup
from src.app.tools.flight_status import build_flight_status
from src.app.tools.weather_lookup import build_weather_lookup
from src.app.tools.web_search import build_web_search


def build_toolset(settings: Settings, skill_dir: Path) -> tuple[list[BaseTool], DocsLookupIndex]:
    docs_paths = list(settings.docs_paths)
    docs_paths.extend(sorted(skill_dir.glob("*.md")))

    docs_index = DocsLookupIndex(docs_paths)
    docs_lookup = build_docs_lookup(docs_index)
    web_search = build_web_search(settings)
    flight_status = build_flight_status(settings)
    weather_lookup = build_weather_lookup(settings)

    return [calculator, clock, docs_lookup, web_search, flight_status, weather_lookup], docs_index

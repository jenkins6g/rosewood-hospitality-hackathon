import json
from dataclasses import dataclass
from functools import lru_cache
from urllib import error, parse, request

from langchain_core.tools import tool

from src.app.config import Settings
from src.app.schemas import WeatherLocationSummary


WEATHER_CODES = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorm",
}


@dataclass(frozen=True)
class WeatherLookupResult:
    summary: WeatherLocationSummary
    text: str


def _weather_description(code: int | None) -> str:
    if code is None:
        return "(unknown)"
    return WEATHER_CODES.get(code, f"weather code {code}")


def format_weather_summary(summary: WeatherLocationSummary) -> str:
    lines = [
        f"Location: {summary.resolved_name or summary.query}",
        f"Current: {summary.current_temperature_c or '(unknown)'}C, {summary.current_weather or '(unknown)'}",
    ]
    if summary.forecast_summary:
        lines.append("Forecast:")
        lines.extend(f"- {line}" for line in summary.forecast_summary)
    return "\n".join(lines)


def _fetch_json(url: str, timeout: float) -> dict:
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Weather request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise ValueError(f"Weather request failed: {exc.reason}") from exc


def resolve_weather_summary(location: str, settings: Settings) -> WeatherLookupResult:
    geocode_url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + parse.urlencode({"name": location, "count": "1", "language": "en", "format": "json"})
    )
    geocode_payload = _fetch_json(geocode_url, settings.http_timeout_seconds)
    results = geocode_payload.get("results") or []
    if not results:
        raise ValueError(f"Could not resolve a weather location for: {location}")

    top = results[0]
    latitude = top["latitude"]
    longitude = top["longitude"]
    resolved_name = ", ".join(
        part for part in [top.get("name", ""), top.get("admin1", ""), top.get("country", "")] if part
    )
    forecast_url = (
        "https://api.open-meteo.com/v1/forecast?"
        + parse.urlencode(
            {
                "latitude": str(latitude),
                "longitude": str(longitude),
                "current": "temperature_2m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "forecast_days": str(settings.weather_forecast_days),
                "timezone": "auto",
            }
        )
    )
    forecast_payload = _fetch_json(forecast_url, settings.http_timeout_seconds)
    current = forecast_payload.get("current", {}) or {}
    daily = forecast_payload.get("daily", {}) or {}
    forecast_lines: list[str] = []
    for index, date in enumerate(daily.get("time", []) or []):
        forecast_lines.append(
            f"{date}: {_weather_description((daily.get('weather_code') or [None])[index])}, "
            f"high {(daily.get('temperature_2m_max') or ['?'])[index]}C, "
            f"low {(daily.get('temperature_2m_min') or ['?'])[index]}C"
        )

    summary = WeatherLocationSummary(
        query=location,
        resolved_name=resolved_name,
        latitude=float(latitude),
        longitude=float(longitude),
        current_temperature_c=str(current.get("temperature_2m", "")),
        current_weather=_weather_description(current.get("weather_code")),
        forecast_summary=forecast_lines,
    )
    return WeatherLookupResult(summary=summary, text=format_weather_summary(summary))


@lru_cache(maxsize=256)
def get_cached_weather_result(location: str, forecast_days: int, timeout_seconds: float) -> WeatherLookupResult:
    settings = Settings(weather_forecast_days=forecast_days, http_timeout_seconds=timeout_seconds)
    return resolve_weather_summary(location, settings)


def build_weather_lookup(settings: Settings):
    @tool("weather_lookup")
    def weather_lookup(location: str) -> str:
        """Look up current weather and a short multi-day forecast for a city or airport location."""
        result = get_cached_weather_result(
            location.strip(),
            settings.weather_forecast_days,
            settings.http_timeout_seconds,
        )
        return result.text

    return weather_lookup

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from urllib import error, parse, request

from langchain_core.tools import tool

from src.app.config import Settings
from src.app.schemas import FlightSnapshot


FLIGHT_REF_RE = re.compile(r"\b([A-Z0-9]{2,3})[- ]?(\d{1,4})\b", re.IGNORECASE)


@dataclass(frozen=True)
class FlightStatusResult:
    snapshot: FlightSnapshot
    text: str


def normalize_flight_reference(value: str) -> str:
    match = FLIGHT_REF_RE.search(value.upper())
    if not match:
        return ""
    return f"{match.group(1)}{match.group(2)}"


def snapshot_from_api_record(record: dict) -> FlightSnapshot:
    flight = record.get("flight", {}) or {}
    airline = record.get("airline", {}) or {}
    departure = record.get("departure", {}) or {}
    arrival = record.get("arrival", {}) or {}
    reference = flight.get("iata") or normalize_flight_reference(
        f"{airline.get('iata', '')}{flight.get('number', '')}"
    )
    return FlightSnapshot(
        flight_reference=reference,
        airline=airline.get("name", "") or airline.get("iata", ""),
        status=record.get("flight_status", "") or "",
        departure_airport=departure.get("airport", "") or departure.get("iata", ""),
        arrival_airport=arrival.get("airport", "") or arrival.get("iata", ""),
        scheduled_arrival=arrival.get("scheduled", "") or "",
        estimated_arrival=arrival.get("estimated", "") or arrival.get("estimated_runway", "") or "",
        actual_arrival=arrival.get("actual", "") or arrival.get("actual_runway", "") or "",
        arrival_terminal=str(arrival.get("terminal", "") or ""),
        arrival_gate=str(arrival.get("gate", "") or ""),
        baggage_claim=str(arrival.get("baggage", "") or ""),
        delay_minutes=str(arrival.get("delay", "") or ""),
    )


def _best_snapshot(records: list[dict]) -> FlightSnapshot | None:
    if not records:
        return None

    def sort_key(record: dict) -> tuple[int, str]:
        status = str(record.get("flight_status", "")).lower()
        status_rank = {
            "active": 4,
            "scheduled": 3,
            "landed": 2,
            "unknown": 1,
        }.get(status, 0)
        arrival = record.get("arrival", {}) or {}
        timestamp = arrival.get("estimated") or arrival.get("scheduled") or ""
        return (status_rank, str(timestamp))

    best = sorted(records, key=sort_key, reverse=True)[0]
    return snapshot_from_api_record(best)


def format_flight_snapshot(snapshot: FlightSnapshot) -> str:
    return "\n".join(
        [
            f"Flight: {snapshot.flight_reference}",
            f"Airline: {snapshot.airline or '(unknown)'}",
            f"Status: {snapshot.status or '(unknown)'}",
            f"Route: {snapshot.departure_airport or '(unknown)'} -> {snapshot.arrival_airport or '(unknown)'}",
            f"Scheduled arrival: {snapshot.scheduled_arrival or '(unknown)'}",
            f"Estimated arrival: {snapshot.estimated_arrival or '(unknown)'}",
            f"Actual arrival: {snapshot.actual_arrival or '(unknown)'}",
            f"Arrival gate: {snapshot.arrival_gate or '(unknown)'}",
            f"Arrival terminal: {snapshot.arrival_terminal or '(unknown)'}",
            f"Baggage claim: {snapshot.baggage_claim or '(unknown)'}",
            f"Arrival delay minutes: {snapshot.delay_minutes or '(unknown)'}",
        ]
    )


def resolve_flight_status(flight_reference: str, settings: Settings) -> FlightStatusResult:
    snapshot = lookup_flight_snapshot(flight_reference, settings)
    return FlightStatusResult(snapshot=snapshot, text=format_flight_snapshot(snapshot))


@lru_cache(maxsize=256)
def get_cached_flight_status_result(
    flight_reference: str,
    aviationstack_api_key: str,
    http_timeout_seconds: float,
) -> FlightStatusResult:
    settings = Settings(
        aviationstack_api_key=aviationstack_api_key,
        http_timeout_seconds=http_timeout_seconds,
    )
    return resolve_flight_status(flight_reference, settings)


def lookup_flight_snapshot(flight_reference: str, settings: Settings) -> FlightSnapshot:
    normalized = normalize_flight_reference(flight_reference)
    if not normalized:
        raise ValueError(f"Could not parse a flight reference from: {flight_reference}")
    if not settings.aviationstack_api_key:
        raise ValueError("AVIATIONSTACK_API_KEY is not configured.")

    airline_code = re.match(r"([A-Z0-9]{2,3})(\d{1,4})", normalized)
    query_attempts = [
        {"flight_iata": normalized, "limit": "5"},
    ]
    if airline_code:
        query_attempts.append(
            {
                "airline_iata": airline_code.group(1),
                "flight_number": airline_code.group(2),
                "limit": "5",
            }
        )

    for query in query_attempts:
        params = {"access_key": settings.aviationstack_api_key, **query}
        url = "https://api.aviationstack.com/v1/flights?" + parse.urlencode(params)
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=settings.http_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Aviationstack request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise ValueError(f"Aviationstack request failed: {exc.reason}") from exc

        records = body.get("data") or body.get("results") or []
        snapshot = _best_snapshot(records)
        if snapshot is not None:
            return snapshot

    raise ValueError(f"No live flight information found for {normalized}.")


def build_flight_status(settings: Settings):
    @tool("flight_status")
    def flight_status(flight_reference: str) -> str:
        """Look up live flight arrival and status information for a flight reference like AA100."""
        if not settings.aviationstack_api_key:
            raise ValueError("AVIATIONSTACK_API_KEY is not configured.")
        result = get_cached_flight_status_result(
            flight_reference,
            settings.aviationstack_api_key,
            settings.http_timeout_seconds,
        )
        return result.text

    return flight_status

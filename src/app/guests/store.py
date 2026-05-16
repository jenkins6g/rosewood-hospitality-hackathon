import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.app.schemas import FlightSnapshot, GuestEvent, GuestProfile


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "guest"


def _parse_timestamp(value: str) -> datetime:
    if not value:
        return datetime(1970, 1, 1, tzinfo=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=UTC)


def _status_weight(status: str) -> int:
    return {
        "on_property": 50,
        "arriving": 40,
        "active": 20,
        "departed": 0,
    }.get(status, 5)


def _name_variants(profile: GuestProfile) -> list[str]:
    values = [profile.canonical_name, *profile.aliases]
    return [value.strip().lower() for value in values if value.strip()]


class GuestProfileStore:
    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir

    def all(self) -> list[GuestProfile]:
        if not self.profiles_dir.exists():
            return []

        profiles: list[GuestProfile] = []
        for path in sorted(self.profiles_dir.glob("*.json")):
            profiles.append(self._load(path))
        return profiles

    def get(self, guest_id: str) -> GuestProfile | None:
        path = self.profiles_dir / f"{guest_id}.json"
        if not path.exists():
            return None
        return self._load(path)

    def find_candidates(self, guest_names: list[str], limit: int = 5) -> list[GuestProfile]:
        if not guest_names:
            return []

        normalized_queries = [name.strip().lower() for name in guest_names if name.strip()]
        scored: list[tuple[float, GuestProfile]] = []

        for profile in self.all():
            score = 0.0
            variants = _name_variants(profile)
            for query in normalized_queries:
                query_tokens = set(query.split())
                for variant in variants:
                    variant_tokens = set(variant.split())
                    overlap = len(query_tokens & variant_tokens)
                    if query == variant:
                        score = max(score, 100.0)
                    elif query in variant or variant in query:
                        score = max(score, 80.0)
                    elif overlap:
                        score = max(score, 50.0 + overlap * 5.0)

            if score <= 0:
                continue

            recency_days = max(
                0.0,
                (datetime.now(UTC) - _parse_timestamp(profile.last_seen_at)).total_seconds() / 86400.0,
            )
            score += max(0.0, 20.0 - min(recency_days, 20.0))
            score += _status_weight(profile.status)
            scored.append((score, profile))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [profile for _, profile in scored[:limit]]

    def create_profile(self, guest_name: str) -> GuestProfile:
        guest_id = f"{_slugify(guest_name)}-{uuid4().hex[:8]}"
        profile = GuestProfile(
            guest_id=guest_id,
            canonical_name=guest_name.strip(),
        )
        self.save(profile)
        return profile

    def save(self, profile: GuestProfile) -> None:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        path = self.profiles_dir / f"{profile.guest_id}.json"
        path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")

    def append_event(
        self,
        profile: GuestProfile,
        guest_event: GuestEvent,
        profile_note: str = "",
        latest_flight: FlightSnapshot | None = None,
    ) -> GuestProfile:
        timeline = [*profile.timeline, guest_event]
        notes = list(profile.profile_notes)
        if profile_note and profile_note not in notes:
            notes.append(profile_note)

        status = profile.status
        if guest_event.event_kind == "flight":
            status = "arriving"
        elif guest_event.event_kind in {"meal", "spa", "conference", "activity"}:
            status = "on_property"

        updated = replace(
            profile,
            status=status,
            last_seen_at=guest_event.timestamp,
            latest_flight=latest_flight or profile.latest_flight,
            profile_notes=notes,
            timeline=timeline,
        )
        self.save(updated)
        return updated

    def _load(self, path: Path) -> GuestProfile:
        payload = json.loads(path.read_text(encoding="utf-8"))
        latest_flight = payload.get("latest_flight")
        timeline = [
            GuestEvent(
                **{
                    **item,
                    "flight_snapshot": FlightSnapshot(**item["flight_snapshot"])
                    if item.get("flight_snapshot")
                    else None,
                }
            )
            for item in payload.get("timeline", [])
        ]
        return GuestProfile(
            guest_id=payload["guest_id"],
            canonical_name=payload["canonical_name"],
            aliases=list(payload.get("aliases", [])),
            status=payload.get("status", "active"),
            last_seen_at=payload.get("last_seen_at", ""),
            latest_flight=FlightSnapshot(**latest_flight) if latest_flight else None,
            profile_notes=list(payload.get("profile_notes", [])),
            timeline=timeline,
        )

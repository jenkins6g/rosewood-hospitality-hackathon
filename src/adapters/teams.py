from dataclasses import dataclass

from src.app.agent import ReactSkillAgent
from src.app.memory.session_store import SessionStore
from src.app.schemas import ChatEvent, TurnResult


def _safe_getattr(obj, *path, default=""):
    current = obj
    for part in path:
        current = getattr(current, part, None)
        if current is None:
            return default
    return current


def _normalize_surface(conversation_type: str) -> str:
    normalized = (conversation_type or "").lower()
    if normalized == "groupchat":
        return "group_chat"
    if normalized in {"personal", "channel", "group_chat"}:
        return normalized
    return "unknown"


def _is_mentioned(text: str, recipient_name: str, recipient_id: str) -> bool:
    lowered = (text or "").lower()
    return any(
        candidate
        for candidate in ((recipient_name or "").lower(), (recipient_id or "").lower())
        if candidate and candidate in lowered
    )


def normalize_teams_activity(activity) -> ChatEvent:
    conversation_type = _safe_getattr(activity, "conversation", "conversation_type")
    recipient_name = _safe_getattr(activity, "recipient", "name")
    recipient_id = _safe_getattr(activity, "recipient", "id")
    text = getattr(activity, "text", "") or ""

    return ChatEvent(
        text=text,
        source="teams",
        surface=_normalize_surface(conversation_type),
        is_mentioned=_is_mentioned(text, recipient_name, recipient_id),
        sender_id=_safe_getattr(activity, "from_", "id"),
        sender_name=_safe_getattr(activity, "from_", "name"),
        conversation_id=_safe_getattr(activity, "conversation", "id"),
        channel_id=_safe_getattr(activity, "channel_data", "channel", "id"),
        team_id=_safe_getattr(activity, "channel_data", "team", "id"),
        message_id=getattr(activity, "id", "") or "",
    )


@dataclass
class TeamsAdapter:
    agent: ReactSkillAgent
    sessions: SessionStore

    async def handle_message(self, ctx) -> TurnResult:
        event = normalize_teams_activity(ctx.activity)
        session = self.sessions.get(event.conversation_id)
        result = self.agent.handle_event(event, session)
        await self.dispatch_result(ctx, result)
        return result

    async def dispatch_result(self, ctx, result: TurnResult) -> None:
        if result.action == "reply" and result.reply_content:
            await ctx.send(result.reply_content)

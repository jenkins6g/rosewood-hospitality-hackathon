from dataclasses import dataclass, field

from src.app.memory.session import SessionMemory


@dataclass
class SessionStore:
    sessions: dict[str, SessionMemory] = field(default_factory=dict)

    def get(self, conversation_id: str) -> SessionMemory:
        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = SessionMemory()
        return self.sessions[conversation_id]

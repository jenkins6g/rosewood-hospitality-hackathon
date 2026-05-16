from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.app.config import settings
from src.app.schemas import ChatEvent, TurnResult
from src.app.state import AgentState


@dataclass
class SessionMemory:
    messages: list[BaseMessage] = field(default_factory=list)
    memory_summary: str = ""

    def build_state(self, event: ChatEvent) -> AgentState:
        messages = list(self.messages[-settings.history_window :])
        messages.append(HumanMessage(content=event.text))

        return {
            "user_input": event.text,
            "event": event,
            "messages": messages,
            "memory_summary": self.memory_summary,
            "tool_trace": [],
            "tool_rounds": 0,
        }

    def apply_result(self, result: TurnResult, event: ChatEvent) -> None:
        if result.action == "ignore":
            return

        self.messages.append(HumanMessage(content=event.text))
        if result.action == "reply" and result.reply_content:
            self.messages.append(AIMessage(content=result.reply_content))

        self.memory_summary = result.memory_summary

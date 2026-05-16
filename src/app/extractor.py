from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from src.app.schemas import OperationalUpdate


class _ExtractedUpdate(BaseModel):
    is_guest_related: bool = Field(default=False)
    guest_name_candidates: list[str] = Field(default_factory=list)
    event_kind: str = Field(default="note")
    summary: str = Field(default="")
    details: str = Field(default="")
    flight_reference: str = Field(default="")
    flight_link: str = Field(default="")
    needs_arrival_lookup: bool = Field(default=False)


class OperationalExtractor:
    def __init__(self, model):
        self.model = model
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Extract a structured operational update from the message. "
                    "Use active skill context to decide whether the message is about a hotel guest and what should be recorded. "
                    "Return concise fields only.",
                ),
                (
                    "human",
                    "Event metadata:\n{event_context}\n\n"
                    "Active context:\n{context_bundle}\n\n"
                    "Message text:\n{user_input}",
                ),
            ]
        )

    def extract(self, *, user_input: str, event_context: str, context_bundle: str) -> OperationalUpdate:
        runnable = self.prompt | self.model.with_structured_output(_ExtractedUpdate)
        payload = runnable.invoke(
            {
                "user_input": user_input,
                "event_context": event_context,
                "context_bundle": context_bundle or "(none)",
            }
        )
        return OperationalUpdate(**payload.model_dump())

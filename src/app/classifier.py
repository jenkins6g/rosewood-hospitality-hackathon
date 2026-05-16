from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate


class ActionDecision(BaseModel):
    action: str = Field(pattern="^(reply|memorize|ignore)$")
    reason: str = Field(default="")
    memory_candidate: str = Field(default="")


class ActionClassifier:
    def __init__(self, model, classifier_prompt: str):
        self.model = model
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", classifier_prompt),
                (
                    "human",
                    "Event metadata:\n{event_context}\n\n"
                    "Active context:\n{context_bundle}\n\n"
                    "Message text:\n{user_input}",
                ),
            ]
        )

    def classify(self, *, user_input: str, event_context: str, context_bundle: str) -> ActionDecision:
        runnable = self.prompt | self.model.with_structured_output(ActionDecision)
        return runnable.invoke(
            {
                "user_input": user_input,
                "event_context": event_context,
                "context_bundle": context_bundle or "(none)",
            }
        )

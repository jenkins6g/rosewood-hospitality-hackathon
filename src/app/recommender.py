from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate


class RecommendationDecision(BaseModel):
    should_reply: bool = Field(default=False)
    reason: str = Field(default="")
    reply_text: str = Field(default="")


class RecommendationEngine:
    def __init__(self, model, recommendation_prompt: str):
        self.model = model
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", recommendation_prompt),
                (
                    "human",
                    "Event metadata:\n{event_context}\n\n"
                    "Active context:\n{context_bundle}\n\n"
                    "Guest profile:\n{guest_profile}\n\n"
                    "Current operational update:\n{operational_update}\n\n"
                    "Weather/travel context:\n{weather_context}\n\n"
                    "Recent guest timeline:\n{recent_timeline}",
                ),
            ]
        )

    def recommend(
        self,
        *,
        event_context: str,
        context_bundle: str,
        guest_profile: str,
        operational_update: str,
        weather_context: str,
        recent_timeline: str,
    ) -> RecommendationDecision:
        runnable = self.prompt | self.model.with_structured_output(RecommendationDecision)
        return runnable.invoke(
            {
                "event_context": event_context,
                "context_bundle": context_bundle or "(none)",
                "guest_profile": guest_profile or "(none)",
                "operational_update": operational_update or "(none)",
                "weather_context": weather_context or "(none)",
                "recent_timeline": recent_timeline or "(none)",
            }
        )

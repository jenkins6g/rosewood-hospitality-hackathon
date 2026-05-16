from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from src.app.guests.store import GuestProfileStore
from src.app.schemas import GuestMatchDecision, GuestProfile, OperationalUpdate


class _MatcherChoice(BaseModel):
    guest_id: str = Field(default="")
    reasoning: str = Field(default="")
    needs_clarification: bool = Field(default=False)
    clarification_question: str = Field(default="")


class GuestMatcher:
    def __init__(self, model, store: GuestProfileStore):
        self.model = model
        self.store = store
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Choose the best matching guest profile using the candidate list, recent activity, and status. "
                    "Prefer the guest who is most plausibly current or arriving soon. "
                    "If the evidence is still ambiguous, ask a short clarification question.",
                ),
                (
                    "human",
                    "Operational update:\n{update_summary}\n\n"
                    "Candidate guest profiles:\n{candidate_profiles}\n\n"
                    "Return the best guest id or request clarification.",
                ),
            ]
        )

    def match(self, update: OperationalUpdate) -> GuestMatchDecision:
        if not update.is_guest_related or not update.guest_name_candidates:
            return GuestMatchDecision(status="not_guest_related")

        candidates = self.store.find_candidates(update.guest_name_candidates)
        if not candidates:
            return GuestMatchDecision(
                status="created",
                guest_name=update.guest_name_candidates[0],
                reasoning="No existing guest profile matched the extracted guest name.",
            )

        if len(candidates) == 1:
            candidate = candidates[0]
            return GuestMatchDecision(
                status="matched",
                guest_id=candidate.guest_id,
                guest_name=candidate.canonical_name,
                candidate_ids=[candidate.guest_id],
                reasoning="Single strong guest profile candidate.",
            )

        choice = self._choose_with_model(update, candidates)
        if choice.needs_clarification or not choice.guest_id:
            return GuestMatchDecision(
                status="ambiguous",
                clarification_question=choice.clarification_question or self._default_question(candidates),
                candidate_ids=[candidate.guest_id for candidate in candidates],
                reasoning=choice.reasoning or "Multiple guest profiles remain plausible.",
            )

        selected = next((candidate for candidate in candidates if candidate.guest_id == choice.guest_id), None)
        if selected is None:
            return GuestMatchDecision(
                status="ambiguous",
                clarification_question=self._default_question(candidates),
                candidate_ids=[candidate.guest_id for candidate in candidates],
                reasoning="Model selected a guest outside the candidate set.",
            )

        return GuestMatchDecision(
            status="matched",
            guest_id=selected.guest_id,
            guest_name=selected.canonical_name,
            candidate_ids=[candidate.guest_id for candidate in candidates],
            reasoning=choice.reasoning or "Selected best current guest match.",
        )

    def _choose_with_model(
        self,
        update: OperationalUpdate,
        candidates: list[GuestProfile],
    ) -> _MatcherChoice:
        candidate_profiles = "\n".join(
            [
                f"- guest_id={candidate.guest_id} | canonical_name={candidate.canonical_name} | "
                f"aliases={', '.join(candidate.aliases) or '(none)'} | status={candidate.status} | "
                f"last_seen_at={candidate.last_seen_at or '(unknown)'}"
                for candidate in candidates
            ]
        )
        runnable = self.prompt | self.model.with_structured_output(_MatcherChoice)
        return runnable.invoke(
            {
                "update_summary": update.summary or update.details or ", ".join(update.guest_name_candidates),
                "candidate_profiles": candidate_profiles,
            }
        )

    def _default_question(self, candidates: list[GuestProfile]) -> str:
        names = ", ".join(candidate.canonical_name for candidate in candidates[:3])
        return f"Which guest did you mean: {names}?"

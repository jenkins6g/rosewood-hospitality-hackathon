from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from src.app.schemas import Skill


class ResolverDecision(BaseModel):
    selected_skills: list[str] = Field(default_factory=list)
    route_reason: str = Field(default="")
    needs_clarification: bool = Field(default=False)
    clarification_question: str = Field(default="")
    execution_plan: list[str] = Field(default_factory=list)


class SkillResolver:
    def __init__(self, model, resolver_prompt: str, max_selected_skills: int):
        self.model = model
        self.max_selected_skills = max_selected_skills
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", resolver_prompt),
                (
                    "human",
                    "User request:\n{user_input}\n\n"
                    "Extra context:\n{extra_context}\n\n"
                    "Current memory summary:\n{memory_summary}\n\n"
                    "Available skills:\n{skill_catalog}\n\n"
                    "Select at most {max_selected_skills} skills.",
                ),
            ]
        )

    def resolve(self, user_input: str, memory_summary: str, skills: list[Skill]) -> ResolverDecision:
        return self.resolve_with_context(
            user_input=user_input,
            memory_summary=memory_summary,
            skills=skills,
            extra_context="",
        )

    def resolve_with_context(
        self,
        *,
        user_input: str,
        memory_summary: str,
        skills: list[Skill],
        extra_context: str,
    ) -> ResolverDecision:
        skill_catalog = "\n".join(
            f"- {skill.name}: {skill.description} | when_to_use={skill.when_to_use} | tags={', '.join(skill.tags)}"
            for skill in skills
        )

        runnable = self.prompt | self.model.with_structured_output(ResolverDecision)
        return runnable.invoke(
            {
                "user_input": user_input,
                "extra_context": extra_context or "(none)",
                "memory_summary": memory_summary or "(none)",
                "skill_catalog": skill_catalog,
                "max_selected_skills": self.max_selected_skills,
            }
        )

from src.app.schemas import Skill


def build_context_bundle(
    selected_skills: list[Skill],
    memory_summary: str,
    resolver_notes: str,
    execution_plan: list[str],
) -> str:
    sections: list[str] = []

    if memory_summary:
        sections.append(f"## Session Memory\n{memory_summary}")

    if resolver_notes:
        sections.append(f"## Resolver Notes\n{resolver_notes}")

    if execution_plan:
        plan = "\n".join(f"{index + 1}. {step}" for index, step in enumerate(execution_plan))
        sections.append(f"## Execution Plan\n{plan}")

    if selected_skills:
        skill_blocks = []
        for skill in selected_skills:
            skill_blocks.append(
                "\n".join(
                    [
                        f"### {skill.name}",
                        f"Description: {skill.description}",
                        f"When to use: {skill.when_to_use}",
                        f"Inputs: {', '.join(skill.inputs) if skill.inputs else 'n/a'}",
                        "Steps:",
                        *[f"- {step}" for step in skill.steps],
                        skill.body,
                    ]
                )
            )

        sections.append("## Loaded Skills\n" + "\n\n".join(skill_blocks))

    return "\n\n".join(section for section in sections if section.strip())

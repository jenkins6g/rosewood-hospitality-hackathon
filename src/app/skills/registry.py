from pathlib import Path

from src.app.schemas import Skill
from src.app.skills.loader import load_skill


class SkillRegistry:
    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self._skills = self._load_skills()

    def _load_skills(self) -> dict[str, Skill]:
        skills: dict[str, Skill] = {}

        for path in sorted(self.skill_dir.glob("*.md")):
            skill = load_skill(path)
            skills[skill.name] = skill

        return skills

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def get_many(self, names: list[str]) -> list[Skill]:
        return [skill for name in names if (skill := self.get(name)) is not None]

from pathlib import Path

import yaml

from src.app.schemas import Skill


def load_skill(path: Path) -> Skill:
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)

    if len(parts) < 3:
        raise ValueError(f"Skill file is missing frontmatter: {path}")

    metadata = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()

    return Skill(
        name=metadata["name"],
        description=metadata["description"],
        when_to_use=metadata["when_to_use"],
        tags=list(metadata.get("tags", [])),
        inputs=list(metadata.get("inputs", [])),
        steps=list(metadata.get("steps", [])),
        examples=list(metadata.get("examples", [])),
        body=body,
        path=path,
    )

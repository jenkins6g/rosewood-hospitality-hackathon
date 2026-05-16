import json
from pathlib import Path

from src.app.schemas import MemoryNote


class MemoryNoteStore:
    def __init__(self, path: Path):
        self.path = path

    def append(self, note: MemoryNote) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(note.to_dict()) + "\n")

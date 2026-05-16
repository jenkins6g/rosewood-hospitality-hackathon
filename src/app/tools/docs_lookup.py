import re
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool


@dataclass(frozen=True)
class DocumentChunk:
    path: Path
    content: str


class DocsLookupIndex:
    def __init__(self, paths: list[Path]):
        self.documents = self._load_documents(paths)

    def _load_documents(self, paths: list[Path]) -> list[DocumentChunk]:
        documents: list[DocumentChunk] = []

        for path in paths:
            if path.exists():
                documents.append(DocumentChunk(path=path, content=path.read_text(encoding="utf-8")))

        return documents

    def search(self, query: str, top_k: int = 3) -> str:
        tokens = set(re.findall(r"\w+", query.lower()))
        scored: list[tuple[int, DocumentChunk]] = []

        for document in self.documents:
            content = document.content.lower()
            score = sum(token in content for token in tokens)
            if score:
                scored.append((score, document))

        if not scored:
            return "No relevant local documents found."

        scored.sort(key=lambda item: item[0], reverse=True)
        excerpts: list[str] = []

        for _, document in scored[:top_k]:
            snippet = document.content[:700].strip()
            excerpts.append(f"[{document.path.name}]\n{snippet}")

        return "\n\n".join(excerpts)


def build_docs_lookup(index: DocsLookupIndex):
    @tool("docs_lookup")
    def docs_lookup(query: str) -> str:
        """Search the local markdown knowledge base for relevant excerpts."""
        return index.search(query=query)

    return docs_lookup

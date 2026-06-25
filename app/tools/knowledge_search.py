import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.tools.registry import ToolResult


class KnowledgeSearchTool:
    name = "knowledge_search"
    description = "Search local Markdown knowledge base files and return relevant sections."
    requires_approval_for: list[str] = []
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "top_k": {"type": "integer", "description": "Maximum number of sections to return.", "default": 3},
        },
        "required": ["query"],
    }

    def __init__(self, knowledge_base_dir: str | None = None) -> None:
        settings = get_settings()
        self.knowledge_base_dir = Path(knowledge_base_dir or settings.knowledge_base_dir)

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        top_k = int(arguments.get("top_k", 3))
        top_k = max(1, min(top_k, 10))
        if not query:
            return ToolResult(False, "Search query is required.")
        if not self.knowledge_base_dir.exists():
            return ToolResult(False, f"Knowledge base directory not found: {self.knowledge_base_dir}")

        sections = self._load_sections()
        scored = []
        query_terms = self._terms(query)
        for section in sections:
            section_terms = self._terms(section["title"] + " " + section["content"])
            overlap = sum(section_terms.count(term) for term in query_terms)
            phrase_boost = 2 if query.lower() in section["content"].lower() else 0
            score = overlap + phrase_boost
            if score > 0:
                scored.append({**section, "score": score})

        scored.sort(key=lambda item: item["score"], reverse=True)
        results = scored[:top_k]
        if not results:
            return ToolResult(True, "No matching knowledge base sections found.", {"results": []})
        return ToolResult(True, "Knowledge search completed.", {"results": results})

    def _load_sections(self) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        for path in sorted(self.knowledge_base_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            current_title = path.stem.replace("_", " ").title()
            current_lines: list[str] = []
            for line in text.splitlines():
                if line.startswith("#"):
                    if current_lines:
                        sections.append(
                            {
                                "document": path.name,
                                "title": current_title,
                                "content": "\n".join(current_lines).strip(),
                            }
                        )
                        current_lines = []
                    current_title = line.lstrip("#").strip() or current_title
                else:
                    current_lines.append(line)
            if current_lines:
                sections.append(
                    {
                        "document": path.name,
                        "title": current_title,
                        "content": "\n".join(current_lines).strip(),
                    }
                )
        return [section for section in sections if section["content"]]

    def _terms(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

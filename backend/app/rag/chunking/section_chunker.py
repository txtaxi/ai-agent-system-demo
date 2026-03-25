import re

from app.rag.chunking.base import ChunkResult, ChunkStrategy
from app.rag.chunking.paragraph_chunker import ParagraphChunkStrategy
from app.rag.chunking.utils import normalize_text


class SectionChunkStrategy(ChunkStrategy):
    name = "section_heading"

    def __init__(self, fallback: ParagraphChunkStrategy | None = None) -> None:
        self.fallback = fallback or ParagraphChunkStrategy()
        self.heading_pattern = re.compile(r"^(#+\s+.+|[A-Z][A-Za-z0-9 _-]{2,}$|第.+章)")

    def matches(self, text: str) -> bool:
        normalized = normalize_text(text)
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        matched = sum(1 for line in lines[:80] if self.heading_pattern.match(line))
        return matched >= 2

    def split(self, text: str) -> list[ChunkResult]:
        normalized = normalize_text(text)
        lines = [line.rstrip() for line in normalized.split("\n") if line.strip()]
        sections: list[str] = []
        current: list[str] = []

        for line in lines:
            if self.heading_pattern.match(line) and current:
                sections.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)

        if current:
            sections.append("\n".join(current).strip())

        results: list[ChunkResult] = []
        for section in sections:
            if len(section) <= self.fallback.chunk_size:
                results.append(ChunkResult(content=section, metadata={"strategy": self.name}))
            else:
                for item in self.fallback.split(section):
                    item.metadata["strategy"] = self.name
                    results.append(item)
        return results

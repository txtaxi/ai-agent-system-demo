from app.rag.chunking.base import ChunkResult, ChunkStrategy
from app.rag.chunking.utils import (
    build_overlap_tail,
    normalize_text,
    split_by_char_window,
    split_into_paragraphs,
    split_into_sentences,
)


class ParagraphChunkStrategy(ChunkStrategy):
    name = "paragraph_first"

    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def matches(self, text: str) -> bool:
        return True

    def split(self, text: str) -> list[ChunkResult]:
        normalized = normalize_text(text)
        if not normalized:
            return []

        paragraphs = split_into_paragraphs(normalized)
        chunks: list[str] = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.extend(self._split_long_paragraph(paragraph))
                continue

            candidate = paragraph if not current_chunk else f"{current_chunk}\n\n{paragraph}"
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
                continue

            chunks.append(current_chunk.strip())
            carry = build_overlap_tail(current_chunk, self.overlap)
            current_chunk = f"{carry}\n\n{paragraph}".strip() if carry else paragraph

            if len(current_chunk) > self.chunk_size:
                chunks.extend(self._split_long_paragraph(current_chunk))
                current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [
            ChunkResult(content=chunk, metadata={"strategy": self.name})
            for chunk in chunks
            if chunk.strip()
        ]

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        sentences = split_into_sentences(paragraph)
        if len(sentences) <= 1:
            return split_by_char_window(paragraph, self.chunk_size, self.overlap)

        chunks: list[str] = []
        current_chunk = ""

        for sentence in sentences:
            candidate = sentence if not current_chunk else f"{current_chunk} {sentence}"
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(current_chunk.strip())
                carry = build_overlap_tail(current_chunk, self.overlap)
                current_chunk = f"{carry} {sentence}".strip() if carry else sentence
            else:
                chunks.extend(split_by_char_window(sentence, self.chunk_size, self.overlap))
                current_chunk = ""

            if len(current_chunk) > self.chunk_size:
                chunks.extend(split_by_char_window(current_chunk, self.chunk_size, self.overlap))
                current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

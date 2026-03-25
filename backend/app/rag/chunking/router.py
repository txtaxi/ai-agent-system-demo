from app.rag.chunking.base import ChunkResult
from app.rag.chunking.paragraph_chunker import ParagraphChunkStrategy
from app.rag.chunking.policy_chunker import PolicyChunkStrategy
from app.rag.chunking.section_chunker import SectionChunkStrategy


PARAGRAPH_CHUNKER = ParagraphChunkStrategy()
CHUNK_STRATEGIES = [
    PolicyChunkStrategy(PARAGRAPH_CHUNKER),
    SectionChunkStrategy(PARAGRAPH_CHUNKER),
    PARAGRAPH_CHUNKER,
]


def chunk_document(text: str) -> list[ChunkResult]:
    for strategy in CHUNK_STRATEGIES:
        if strategy.matches(text):
            return strategy.split(text)
    return PARAGRAPH_CHUNKER.split(text)

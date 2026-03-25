import re


def normalize_text(content: str) -> str:
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_paragraphs(content: str) -> list[str]:
    raw_parts = re.split(r"\n\s*\n", content)
    return [part.strip() for part in raw_parts if part.strip()]


def split_into_sentences(paragraph: str) -> list[str]:
    parts = re.split(r"(?<=[。！？.!?；;])\s+", paragraph)
    return [part.strip() for part in parts if part.strip()]


def split_by_char_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    text = text.strip()

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks


def build_overlap_tail(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    text = text.strip()
    if len(text) <= overlap:
        return text
    return text[-overlap:].strip()

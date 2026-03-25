import hashlib
import math

from app.core.config import settings


def generate_embedding(text: str) -> list[float]:
    """使用确定性的本地向量生成，便于开发阶段离线调试。"""
    dimension = settings.embedding_dimension
    values = [0.0] * dimension

    for token in text.split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for index in range(dimension):
            byte_value = digest[index % len(digest)]
            values[index] += (byte_value / 255.0) - 0.5

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]

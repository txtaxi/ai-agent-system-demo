from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChunkResult:
    content: str
    metadata: dict


class ChunkStrategy(ABC):
    name: str

    @abstractmethod
    def matches(self, text: str) -> bool:
        """判断当前策略是否适合这个文本。"""

    @abstractmethod
    def split(self, text: str) -> list[ChunkResult]:
        """执行分块。"""

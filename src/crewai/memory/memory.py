from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from crewai.memory.storage.rag_storage import RAGStorage


class Memory(BaseModel):
    """
    Base class for memory, now supporting agent tags and generic metadata.
    """

    def __init__(self, storage: Union[RAGStorage, Any]):
        self.storage = storage

    def save(
        self,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        agent: Optional[str] = None,
    ) -> None:
        metadata = metadata or {}
        if agent:
            metadata["agent"] = agent

        self.storage.save(value, metadata)

    def search(
        self,
        query: str,
        limit: int = 3,
        score_threshold: float = 0.35,
    ) -> List[Any]:
        return self.storage.search(
            query=query, limit=limit, score_threshold=score_threshold
        )

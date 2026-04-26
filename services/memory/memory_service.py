"""Memory Service – vector-based long/short-term memory for agents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


class MemoryService:
    """
    In-process memory service.
    Replace the in-memory store with Qdrant/Chroma for production.
    """

    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}

    def save(self, content: str, metadata: dict[str, Any] | None = None) -> MemoryEntry:
        entry = MemoryEntry(content=content, metadata=metadata or {})
        self._store[entry.id] = entry
        return entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self._store.get(entry_id)

    def search(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Naive keyword search – swap with vector similarity in production."""
        query_lower = query.lower()
        results = [
            e for e in self._store.values() if query_lower in e.content.lower()
        ]
        return results[:top_k]

    def delete(self, entry_id: str) -> bool:
        return self._store.pop(entry_id, None) is not None

    @property
    def count(self) -> int:
        return len(self._store)

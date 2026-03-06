"""
Per-session chat history.

Backends:
- ``InMemoryHistory`` — default, resets on server restart
- ``RedisHistory``    — activated via ``redis_history`` feature flag
- ``PostgresHistory`` — activated via ``postgres_history`` feature flag

Missing optional backend packages produce a WARNING and fall back
to in-memory.
"""

from __future__ import annotations

import abc
import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum sessions kept in memory
_MAX_SESSIONS = 256
# Maximum messages per session
_MAX_MESSAGES_PER_SESSION = 200


class ChatHistory(abc.ABC):
    """Abstract chat history backend."""

    @abc.abstractmethod
    def append(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session history."""
        ...

    @abc.abstractmethod
    def get(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve the full message list for a session."""
        ...

    @abc.abstractmethod
    def clear(self, session_id: str) -> None:
        """Remove all messages for a session."""
        ...


class InMemoryHistory(ChatHistory):
    """In-process dict-based history. Resets on server restart."""

    def __init__(self, max_sessions: int = _MAX_SESSIONS):
        self._store: OrderedDict[str, List[Dict[str, str]]] = OrderedDict()
        self._max = max_sessions

    def append(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
            # Evict oldest session if over capacity
            if len(self._store) > self._max:
                self._store.popitem(last=False)
        msgs = self._store[session_id]
        msgs.append({"role": role, "content": content})
        # Trim old messages if session gets too long
        if len(msgs) > _MAX_MESSAGES_PER_SESSION:
            self._store[session_id] = msgs[-_MAX_MESSAGES_PER_SESSION:]
        self._store.move_to_end(session_id)

    def get(self, session_id: str) -> List[Dict[str, str]]:
        return list(self._store.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)


class RedisHistory(ChatHistory):
    """Redis-backed history. Falls back to InMemoryHistory if
    Redis is unavailable or the ``redis`` package is not installed.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._fallback: Optional[InMemoryHistory] = None
        self._redis: Any = None
        try:
            import redis  # type: ignore

            self._redis = redis.from_url(redis_url)
            self._redis.ping()
            logger.info("RedisHistory connected to %s", redis_url)
        except Exception as exc:
            logger.warning(
                "Redis unavailable (%s) — falling back to in-memory history",
                exc,
            )
            self._fallback = InMemoryHistory()

    def _key(self, session_id: str) -> str:
        return f"govlens:chat:{session_id}"

    def append(self, session_id: str, role: str, content: str) -> None:
        if self._fallback:
            return self._fallback.append(session_id, role, content)
        import json

        self._redis.rpush(
            self._key(session_id),
            json.dumps({"role": role, "content": content}),
        )
        self._redis.ltrim(self._key(session_id), -_MAX_MESSAGES_PER_SESSION, -1)

    def get(self, session_id: str) -> List[Dict[str, str]]:
        if self._fallback:
            return self._fallback.get(session_id)
        import json

        raw = self._redis.lrange(self._key(session_id), 0, -1)
        return [json.loads(item) for item in raw]

    def clear(self, session_id: str) -> None:
        if self._fallback:
            return self._fallback.clear(session_id)
        self._redis.delete(self._key(session_id))


def create_history(backend: str = "memory", **kwargs) -> ChatHistory:
    """Factory for chat history backends."""
    if backend == "redis":
        return RedisHistory(**kwargs)
    return InMemoryHistory()

"""
Token usage and cost accounting for chatbot sessions.

Records ``prompt_tokens``, ``completion_tokens``, ``total_cost_usd``
per response. Stored in-memory per session; included in the
``POST /api/chat/save`` output.

Only active when ``CHAT_COST_TRACKING=true``.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class UsageRecord:
    """A single usage observation."""

    __slots__ = ("prompt_tokens", "completion_tokens", "total_cost_usd")

    def __init__(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_cost_usd = total_cost_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost_usd": self.total_cost_usd,
        }


class UsageTracker:
    """Collects per-session token/cost usage."""

    def __init__(self, enabled: bool = False):
        self._enabled = enabled
        self._sessions: Dict[str, List[UsageRecord]] = defaultdict(list)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def record(
        self,
        session_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> None:
        """Record a usage observation for the session."""
        if not self._enabled:
            return
        self._sessions[session_id].append(
            UsageRecord(prompt_tokens, completion_tokens, total_cost_usd)
        )

    def get_session_usage(self, session_id: str) -> Dict[str, Any]:
        """Return aggregated usage for a session."""
        records = self._sessions.get(session_id, [])
        total_prompt = sum(r.prompt_tokens for r in records)
        total_completion = sum(r.completion_tokens for r in records)
        total_cost = sum(r.total_cost_usd for r in records)
        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_cost_usd": round(total_cost, 6),
            "request_count": len(records),
        }

    def get_last_usage(self, session_id: str) -> Dict[str, Any]:
        """Return usage for the most recent request in a session."""
        records = self._sessions.get(session_id, [])
        if not records:
            return {}
        return records[-1].to_dict()

    def clear_session(self, session_id: str) -> None:
        """Remove usage records for a session."""
        self._sessions.pop(session_id, None)

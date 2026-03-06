"""
GovLens Chatbot Package (Phase 5)

Contextual chatbot with LLM integration, scope enforcement,
streaming WebSocket support, and graceful degradation.
"""

from .protocol import (
    StartFrame,
    TokenFrame,
    PartialUsageFrame,
    DoneFrame,
    ErrorFrame,
    CancelFrame,
)
from .llm import LLMClient, MockLLMClient
from .context import build_scoped_context
from .scope import ScopeRefusal, check_scope
from .history import ChatHistory, InMemoryHistory
from .usage import UsageTracker

__all__ = [
    "StartFrame",
    "TokenFrame",
    "PartialUsageFrame",
    "DoneFrame",
    "ErrorFrame",
    "CancelFrame",
    "LLMClient",
    "MockLLMClient",
    "build_scoped_context",
    "ScopeRefusal",
    "check_scope",
    "ChatHistory",
    "InMemoryHistory",
    "UsageTracker",
]

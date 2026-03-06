"""
WebSocket message envelope protocol for the chatbot.

Defines the Pydantic models used as the contract between backend
and frontend for streaming chat over WebSocket.

Envelope types:
- ``start``   — server → client when a generation begins
- ``token``   — server → client per-token during streaming
- ``partial_usage`` — server → client mid-stream usage stats
- ``done``    — server → client when generation is complete
- ``error``   — server → client on error
- ``cancel``  — client → server to abort generation

All frames are JSON-serialised via ``model_dump()``.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StartFrame(BaseModel):
    """Sent at the beginning of a generation."""

    type: str = Field(default="start", frozen=True)
    session_id: str
    degraded: bool = False
    provider: str = "mock"


class TokenFrame(BaseModel):
    """A single token emitted during streaming."""

    type: str = Field(default="token", frozen=True)
    content: str


class PartialUsageFrame(BaseModel):
    """Mid-stream token usage statistics (optional)."""

    type: str = Field(default="partial_usage", frozen=True)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ProvenanceItem(BaseModel):
    """A single source document referenced by the answer."""

    id: str
    title: str
    excerpt: str = ""


class ScopeRefusalData(BaseModel):
    """Structured data when the query is out of scope."""

    reason: str
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    hint_endpoint: str = ""


class DoneFrame(BaseModel):
    """Sent when generation is complete."""

    type: str = Field(default="done", frozen=True)
    content: str = ""
    cancelled: bool = False
    provenance: List[ProvenanceItem] = Field(default_factory=list)
    scope_refusal: Optional[ScopeRefusalData] = None
    usage: Optional[Dict[str, Any]] = None


class ErrorFrame(BaseModel):
    """Sent when an error occurs."""

    type: str = Field(default="error", frozen=True)
    message: str


class CancelFrame(BaseModel):
    """Client → server request to abort generation."""

    type: str = Field(default="cancel", frozen=True)

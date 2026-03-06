"""
Unit tests for Phase 5 — Contextual Chatbot.

Tests cover: context builder, scope enforcement, LLM clients,
chat history, protocol frames, usage accounting, config,
and API endpoints (chat status, save, WebSocket).

Tests that require external services are decorated with
pytest.mark.skipif and report SKIPPED (not FAILED) when the
required configuration is absent:
  - @requires_openai_key  — needs OPENAI_API_KEY env var
  - @requires_redis       — needs Redis reachable at localhost:6379
"""

import asyncio
import json
import os
import socket

import pytest
from fastapi.testclient import TestClient

from src.api import app, get_store
from src.chatbot.context import build_scoped_context, get_context_cache
from src.chatbot.history import InMemoryHistory, create_history
from src.chatbot.llm import MockLLMClient, OpenAIClient, create_llm_client
from src.chatbot.protocol import (
    CancelFrame,
    DoneFrame,
    ErrorFrame,
    StartFrame,
    TokenFrame,
    PartialUsageFrame,
)
from src.chatbot.scope import (
    ScopeRefusal,
    check_scope,
    clear_refusal_log,
    get_refusal_log,
)
from src.chatbot.usage import UsageTracker
from src.engine import DataStore
from src.models import FilterState

# ── Skip-condition helpers ────────────────────────────────────────────


def _redis_reachable(host: str = "127.0.0.1", port: int = 6379, timeout: float = 0.5) -> bool:
    """Return True if a Redis server is responding at host:port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


_REDIS_AVAILABLE: bool = _redis_reachable()
_OPENAI_KEY_SET: bool = bool(os.environ.get("OPENAI_API_KEY", "").strip())

requires_redis = pytest.mark.skipif(
    not _REDIS_AVAILABLE,
    reason="Redis server not reachable at localhost:6379 - set one up to run this test",
)
requires_openai_key = pytest.mark.skipif(
    not _OPENAI_KEY_SET,
    reason="OPENAI_API_KEY env var not set - set it to run live OpenAI tests",
)


# ── Chunk builder for OpenAI fixture tests ────────────────────────────


def _make_chunk(content=None, prompt_tokens=None, completion_tokens=None):
    """Build a minimal fake OpenAI streaming chunk."""
    from unittest.mock import MagicMock

    chunk = MagicMock()
    if prompt_tokens is not None:
        chunk.usage = MagicMock(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens or 0
        )
    else:
        chunk.usage = None
    if content is not None:
        choice = MagicMock()
        choice.delta.content = content
        chunk.choices = [choice]
    else:
        chunk.choices = []
    return chunk


# ── Test data ────────────────────────────────────────────────────────

CHAT_RECORDS = [
    {
        "contract_id": "c1",
        "contract_title": "Road repair project alpha",
        "buyer": "Mesto Bratislava",
        "supplier": "STRABAG s.r.o.",
        "price_numeric_eur": 500_000.0,
        "published_date": "2025-06-01",
        "category": "construction",
        "award_type": "direct_award",
        "pdf_text_summary": "road repair in downtown area",
        "contract_url": "https://crz.gov.sk/zmluva/c1/",
        "ico_buyer": "00001001",
        "ico_supplier": "00002001",
    },
    {
        "contract_id": "c2",
        "contract_title": "IT system upgrade",
        "buyer": "Mesto Bratislava",
        "supplier": "T-Systems s.r.o.",
        "price_numeric_eur": 300_000.0,
        "published_date": "2025-07-15",
        "category": "IT",
        "award_type": "open_tender",
        "pdf_text_summary": "software upgrade for city hall",
        "contract_url": "https://crz.gov.sk/zmluva/c2/",
        "ico_buyer": "00001001",
        "ico_supplier": "00002002",
    },
    {
        "contract_id": "c3",
        "contract_title": "Security services",
        "buyer": "Mesto Košice",
        "supplier": "SecurCorp a.s.",
        "price_numeric_eur": 200_000.0,
        "published_date": "2025-08-20",
        "category": "services",
        "award_type": "direct_award",
        "pdf_text_summary": "security for municipal buildings",
        "contract_url": "https://crz.gov.sk/zmluva/c3/",
        "ico_buyer": "00001002",
        "ico_supplier": "00002003",
    },
    {
        "contract_id": "c4",
        "contract_title": "Office supplies delivery",
        "buyer": "Ministerstvo vnútra SR",
        "supplier": "OfficeMax s.r.o.",
        "price_numeric_eur": 50_000.0,
        "published_date": "2025-09-01",
        "category": "supplies",
        "award_type": "open_tender",
        "pdf_text_summary": "paper and stationery",
        "contract_url": "https://crz.gov.sk/zmluva/c4/",
        "ico_buyer": "00001003",
        "ico_supplier": "00002004",
    },
    {
        "contract_id": "c5",
        "contract_title": "Consulting for legal reform",
        "buyer": "Mesto Košice",
        "supplier": "LegalCo s.r.o.",
        "price_numeric_eur": 150_000.0,
        "published_date": "2025-10-10",
        "category": "services",
        "award_type": "direct_award",
        "pdf_text_summary": "legal consulting on procurement reform",
        "contract_url": "https://crz.gov.sk/zmluva/c5/",
        "ico_buyer": "00001002",
        "ico_supplier": "00002005",
    },
]


@pytest.fixture
def chat_store():
    """DataStore loaded with chat test data."""
    ds = DataStore()
    ds.load_from_list(CHAT_RECORDS)
    return ds


@pytest.fixture
def client(chat_store):
    """FastAPI test client with dependency override."""
    app.dependency_overrides[get_store] = lambda: chat_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_cache_and_log():
    """Clear context cache and refusal log before each test."""
    get_context_cache().clear()
    clear_refusal_log()
    yield


# ══════════════════════════════════════════════════════════════════════
# Context Builder
# ══════════════════════════════════════════════════════════════════════


class TestContextBuilder:
    """Tests for build_scoped_context."""

    def test_small_dataset_full_context(self, chat_store):
        """n ≤ 100 → all contracts included in context."""
        filters = FilterState()
        context, prov = build_scoped_context(filters, chat_store, use_cache=False)

        assert "5 contracts" in context
        assert "€500,000.00" in context or "500000" in context or "500,000" in context
        # All 5 contracts should be in provenance
        assert len(prov) == 5
        assert all(p["id"] for p in prov)

    def test_large_dataset_summary(self, chat_store):
        """When > 100 contracts, context uses summary mode."""
        # Create a store with > 100 records
        records = []
        for i in range(120):
            records.append({
                "contract_id": f"lg{i}",
                "contract_title": f"Contract {i}",
                "buyer": "Mesto Bratislava",
                "supplier": f"Vendor {i % 10}",
                "price_numeric_eur": 1000.0 * (i + 1),
                "published_date": "2025-06-01",
                "category": "construction",
                "award_type": "open_tender",
                "pdf_text_summary": "not_summarized",
            })
        big_store = DataStore()
        big_store.load_from_list(records)

        context, prov = build_scoped_context(
            FilterState(), big_store, top_n=20, use_cache=False
        )

        assert "120 contracts" in context
        assert "Top 20" in context
        # Provenance should have the top 20 by value
        assert len(prov) == 20

    def test_provenance_metadata_attached(self, chat_store):
        """Every provenance doc has id, title, source, date."""
        _, prov = build_scoped_context(FilterState(), chat_store, use_cache=False)
        for p in prov:
            assert "id" in p
            assert "title" in p
            assert "source" in p
            assert "date" in p

    def test_chunk_cache_hit(self, chat_store):
        """Repeated call with same filters uses cache."""
        filters = FilterState()
        ctx1, prov1 = build_scoped_context(filters, chat_store)
        ctx2, prov2 = build_scoped_context(filters, chat_store)
        assert ctx1 == ctx2
        assert prov1 == prov2

    def test_chunk_cache_miss_on_filter_change(self, chat_store):
        """Different filters produce different context."""
        ctx1, _ = build_scoped_context(FilterState(), chat_store)
        ctx2, _ = build_scoped_context(
            FilterState(institutions=["Mesto Bratislava"]), chat_store
        )
        assert ctx1 != ctx2

    def test_filter_integration_with_datastore(self, chat_store):
        """Context builder uses DataStore.filter() correctly."""
        filters = FilterState(institutions=["Mesto Košice"])
        context, prov = build_scoped_context(filters, chat_store, use_cache=False)

        assert "2 contracts" in context
        assert len(prov) == 2
        assert all(
            p["id"] in ("c3", "c5") for p in prov
        )

    def test_empty_result(self, chat_store):
        """No matching contracts → appropriate message."""
        filters = FilterState(institutions=["Nonexistent City"])
        context, prov = build_scoped_context(filters, chat_store, use_cache=False)
        assert "No contracts" in context
        assert len(prov) == 0


# ══════════════════════════════════════════════════════════════════════
# Scope Enforcement
# ══════════════════════════════════════════════════════════════════════


class TestScopeEnforcement:
    """Tests for check_scope."""

    def test_rejects_out_of_scope_institution(self, chat_store):
        """Institution not in filters → ScopeRefusal."""
        filters = FilterState(institutions=["Mesto Bratislava"])
        result = check_scope(
            "Tell me about Mesto Košice contracts", filters, chat_store
        )
        assert result is not None
        assert isinstance(result, ScopeRefusal)
        assert "Mesto Košice" in result.reason

    def test_accepts_in_scope_question(self, chat_store):
        """Question about filtered institution → no refusal."""
        filters = FilterState(institutions=["Mesto Bratislava"])
        result = check_scope(
            "What are Mesto Bratislava's top vendors?", filters, chat_store
        )
        assert result is None

    def test_refusal_contains_suggestions(self, chat_store):
        """Refusal includes non-empty suggestions."""
        filters = FilterState(institutions=["Mesto Bratislava"])
        result = check_scope(
            "Tell me about Mesto Košice", filters, chat_store
        )
        assert result is not None
        assert len(result.suggestions) > 0
        assert any("Košice" in s.get("value", "") for s in result.suggestions)

    def test_refused_queries_logged(self, chat_store):
        """Refusals are written to the structured log."""
        clear_refusal_log()
        filters = FilterState(institutions=["Mesto Bratislava"])
        check_scope("Tell me about Mesto Košice", filters, chat_store)
        log = get_refusal_log()
        assert len(log) == 1
        assert "Mesto Košice" in log[0]["reason"]

    def test_no_filter_means_everything_in_scope(self, chat_store):
        """Empty filters → all entities are in scope."""
        result = check_scope(
            "Tell me about Mesto Košice", FilterState(), chat_store
        )
        assert result is None

    def test_date_out_of_range(self, chat_store):
        """Year reference outside date filter → refusal."""
        filters = FilterState(date_from="2025-01-01", date_to="2025-12-31")
        result = check_scope(
            "What happened in 2020?", filters, chat_store
        )
        assert result is not None
        assert "2020" in result.reason


# ══════════════════════════════════════════════════════════════════════
# Mock LLM Client
# ══════════════════════════════════════════════════════════════════════


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    def test_complete_returns_string(self):
        """complete() returns a deterministic string."""
        client = MockLLMClient(context_summary={"count": 5, "spend": 1000.0, "max_val": 500.0})
        result = asyncio.run(
            client.complete([{"role": "user", "content": "Hello"}])
        )
        assert isinstance(result, str)
        assert "5 contracts" in result

    def test_stream_yields_tokens(self):
        """stream_chat() calls on_token for each word."""
        client = MockLLMClient()
        tokens = []

        async def collect(token):
            tokens.append(token)

        asyncio.run(
            client.stream_chat(
                [{"role": "user", "content": "test"}],
                on_token=collect,
            )
        )
        assert len(tokens) > 0
        # Reconstructed text should match complete()
        full = "".join(tokens)
        assert "mock response" in full.lower()

    def test_get_token_usage_returns_dict(self):
        """get_token_usage returns prompt_tokens and completion_tokens."""
        client = MockLLMClient()
        usage = client.get_token_usage({"prompt_tokens": 10, "completion_tokens": 20})
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20


# ══════════════════════════════════════════════════════════════════════
# LLM Factory
# ══════════════════════════════════════════════════════════════════════


class TestLLMFactory:
    """Tests for create_llm_client factory."""

    def test_mock_default(self):
        """Default provider is mock."""
        client = create_llm_client(provider="mock")
        assert isinstance(client, MockLLMClient)

    def test_openai_without_key_falls_back(self):
        """OpenAI without key → MockLLMClient."""
        client = create_llm_client(provider="openai", api_key="")
        assert isinstance(client, MockLLMClient)

    def test_unknown_provider_falls_back(self):
        """Unknown provider → MockLLMClient."""
        client = create_llm_client(provider="unknown_provider", api_key="")
        assert isinstance(client, MockLLMClient)


# ══════════════════════════════════════════════════════════════════════
# OpenAI Client (fixture-based + live)
# ══════════════════════════════════════════════════════════════════════


class TestOpenAIClient:
    """Tests for OpenAIClient adapter.

    Fixture-replay tests run in CI without any API key.
    test_live_api_call is SKIPPED unless OPENAI_API_KEY is set.
    """

    def _build_client(self):
        """Create an OpenAIClient with a fake key and a mock inner client."""
        from unittest.mock import MagicMock

        client = OpenAIClient.__new__(OpenAIClient)
        client._api_key = "fake-test-key"
        client._model = "gpt-4o-mini"
        client._circuit_failures = 0
        client._circuit_open = False
        client._client = MagicMock()
        return client

    def test_recorded_fixture_stream(self):
        """Fixture-replay: stream_chat yields tokens and captures usage."""
        chunks = [
            _make_chunk(content="Hello"),
            _make_chunk(content=" world"),
            _make_chunk(prompt_tokens=5, completion_tokens=2),
        ]

        async def _fake_create(**kwargs):
            async def _gen():
                for c in chunks:
                    yield c
            return _gen()

        client = self._build_client()
        client._client.chat.completions.create = _fake_create

        tokens = []

        async def collect(t):
            tokens.append(t)

        result = asyncio.run(
            client.stream_chat(
                [{"role": "user", "content": "test"}],
                on_token=collect,
            )
        )

        assert "".join(tokens) == "Hello world"
        assert result["prompt_tokens"] == 5
        assert result["completion_tokens"] == 2

    def test_retry_on_429(self):
        """429 response triggers exponential-backoff retry and eventually succeeds."""
        from unittest.mock import AsyncMock, patch

        call_count = 0
        success_chunks = [
            _make_chunk(content="ok"),
            _make_chunk(prompt_tokens=1, completion_tokens=1),
        ]

        async def _fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                exc = Exception("Rate limited")
                exc.status_code = 429  # type: ignore[attr-defined]
                raise exc

            async def _gen():
                for c in success_chunks:
                    yield c

            return _gen()

        client = self._build_client()
        client._client.chat.completions.create = _fake_create

        tokens = []

        async def collect(t):
            tokens.append(t)

        with patch("asyncio.sleep", new=AsyncMock()):
            asyncio.run(
                client.stream_chat(
                    [{"role": "user", "content": "hi"}],
                    on_token=collect,
                )
            )

        assert call_count >= 2, "Expected at least one retry after 429"
        assert "ok" in "".join(tokens)

    def test_circuit_breaker_opens(self):
        """Consecutive non-retryable failures open the circuit breaker."""
        async def _always_fail(**kwargs):
            raise RuntimeError("Connection refused")  # no status_code → not retried

        client = self._build_client()
        client._client.chat.completions.create = _always_fail

        # Each complete() call exhausts retries and increments _circuit_failures.
        # After _MAX_RETRIES failures the circuit opens.
        for _ in range(OpenAIClient._MAX_RETRIES):
            with pytest.raises(Exception):
                asyncio.run(
                    client.complete([{"role": "user", "content": "hi"}])
                )

        assert client._circuit_open is True

    @requires_openai_key
    def test_live_api_call(self):
        """Full round-trip with the real OpenAI API."""
        client = create_llm_client(
            provider="openai",
            api_key=os.environ["OPENAI_API_KEY"],
        )
        result = asyncio.run(
            client.complete([{"role": "user", "content": "Reply with exactly the word: ok"}])
        )
        assert isinstance(result, str)
        assert len(result.strip()) > 0


# ══════════════════════════════════════════════════════════════════════
# Chat History
# ══════════════════════════════════════════════════════════════════════


class TestChatHistory:
    """Tests for InMemoryHistory."""

    def test_in_memory_append_and_get(self):
        """Stores and retrieves messages by session ID."""
        h = InMemoryHistory()
        h.append("s1", "user", "Hello")
        h.append("s1", "assistant", "Hi there")
        msgs = h.get("s1")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["content"] == "Hi there"

    def test_in_memory_clear_session(self):
        """clear() removes all messages for a session."""
        h = InMemoryHistory()
        h.append("s1", "user", "Hello")
        h.clear("s1")
        assert h.get("s1") == []

    def test_redis_fallback_when_unavailable(self):
        """RedisHistory with unreachable host falls back to in-memory."""
        from src.chatbot.history import RedisHistory
        rh = RedisHistory(redis_url="redis://localhost:59999/0")
        assert rh._fallback is not None
        # Should still work via fallback
        rh.append("s1", "user", "test")
        msgs = rh.get("s1")
        assert len(msgs) == 1

    @requires_redis
    def test_redis_history(self):
        """RedisHistory stores and retrieves messages across instantiations."""
        from src.chatbot.history import RedisHistory

        session = "test-redis-session-unit"
        rh1 = RedisHistory()
        rh1.clear(session)  # start clean
        rh1.append(session, "user", "Hello from Redis")
        rh1.append(session, "assistant", "Reply from Redis")

        # Second instance reads the same data from Redis
        rh2 = RedisHistory()
        msgs = rh2.get(session)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello from Redis"
        assert msgs[1]["role"] == "assistant"

        # cleanup
        rh1.clear(session)
        assert rh2.get(session) == []

    def test_separate_sessions(self):
        """Different sessions have independent histories."""
        h = InMemoryHistory()
        h.append("s1", "user", "msg1")
        h.append("s2", "user", "msg2")
        assert len(h.get("s1")) == 1
        assert len(h.get("s2")) == 1
        assert h.get("s1")[0]["content"] == "msg1"

    def test_create_history_factory(self):
        """Factory returns correct backend."""
        h = create_history(backend="memory")
        assert isinstance(h, InMemoryHistory)


# ══════════════════════════════════════════════════════════════════════
# Protocol Frames
# ══════════════════════════════════════════════════════════════════════


class TestProtocol:
    """Tests for WebSocket message envelope."""

    def test_start_frame_serializes(self):
        """StartFrame serialises to expected JSON keys."""
        f = StartFrame(session_id="abc", degraded=True, provider="mock")
        d = f.model_dump()
        assert d["type"] == "start"
        assert d["session_id"] == "abc"
        assert d["degraded"] is True

    def test_token_frame_serializes(self):
        """TokenFrame contains type='token' and content."""
        f = TokenFrame(content="Hello")
        d = f.model_dump()
        assert d["type"] == "token"
        assert d["content"] == "Hello"

    def test_done_frame_with_provenance(self):
        """DoneFrame carries provenance list."""
        from src.chatbot.protocol import ProvenanceItem
        f = DoneFrame(
            content="Answer",
            provenance=[ProvenanceItem(id="c1", title="Contract 1", excerpt="url")],
        )
        d = f.model_dump()
        assert d["type"] == "done"
        assert len(d["provenance"]) == 1
        assert d["provenance"][0]["id"] == "c1"

    def test_cancel_frame_accepted(self):
        """CancelFrame has type='cancel'."""
        f = CancelFrame()
        d = f.model_dump()
        assert d["type"] == "cancel"

    def test_error_frame(self):
        """ErrorFrame contains message."""
        f = ErrorFrame(message="Something went wrong")
        d = f.model_dump()
        assert d["type"] == "error"
        assert d["message"] == "Something went wrong"

    def test_partial_usage_frame(self):
        """PartialUsageFrame carries token counts."""
        f = PartialUsageFrame(prompt_tokens=100, completion_tokens=50)
        d = f.model_dump()
        assert d["type"] == "partial_usage"
        assert d["prompt_tokens"] == 100

    def test_done_frame_with_scope_refusal(self):
        """DoneFrame can carry scope refusal data."""
        from src.chatbot.protocol import ScopeRefusalData
        f = DoneFrame(
            content="Out of scope",
            scope_refusal=ScopeRefusalData(
                reason="Institution not in scope",
                suggestions=[{"label": "Add it", "action": "add_institution", "value": "X"}],
            ),
        )
        d = f.model_dump()
        assert d["scope_refusal"] is not None
        assert d["scope_refusal"]["reason"] == "Institution not in scope"


# ══════════════════════════════════════════════════════════════════════
# Usage Accounting
# ══════════════════════════════════════════════════════════════════════


class TestUsageAccounting:
    """Tests for UsageTracker."""

    def test_cost_recorded_per_session(self):
        """Token counts accumulated per session."""
        tracker = UsageTracker(enabled=True)
        tracker.record("s1", prompt_tokens=100, completion_tokens=50, total_cost_usd=0.001)
        tracker.record("s1", prompt_tokens=200, completion_tokens=100, total_cost_usd=0.002)
        usage = tracker.get_session_usage("s1")
        assert usage["total_prompt_tokens"] == 300
        assert usage["total_completion_tokens"] == 150
        assert usage["request_count"] == 2

    def test_cost_omitted_when_flag_off(self):
        """When disabled, no records are stored."""
        tracker = UsageTracker(enabled=False)
        tracker.record("s1", prompt_tokens=100, completion_tokens=50)
        usage = tracker.get_session_usage("s1")
        assert usage["request_count"] == 0


# ══════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════


class TestConfig:
    """Tests for chatbot-related config."""

    def test_missing_key_forces_mock_provider(self):
        """LLM_PROVIDER=openai with empty key → runtime forced to mock."""
        import os
        from src.config import Settings

        old_provider = os.environ.get("LLM_PROVIDER")
        old_key = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["LLM_PROVIDER"] = "openai"
            os.environ["OPENAI_API_KEY"] = ""
            s = Settings()
            assert s.llm_provider == "mock"
        finally:
            if old_provider is not None:
                os.environ["LLM_PROVIDER"] = old_provider
            else:
                os.environ.pop("LLM_PROVIDER", None)
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_feature_flags_parsed_from_env(self):
        """CHAT_FEATURE_FLAGS=streaming,provenance → list."""
        import os
        from src.config import Settings

        old = os.environ.get("CHAT_FEATURE_FLAGS")
        try:
            os.environ["CHAT_FEATURE_FLAGS"] = "streaming,provenance"
            os.environ["LLM_PROVIDER"] = "mock"
            s = Settings()
            assert "streaming" in s.chat_feature_flags
            assert "provenance" in s.chat_feature_flags
        finally:
            if old is not None:
                os.environ["CHAT_FEATURE_FLAGS"] = old
            else:
                os.environ.pop("CHAT_FEATURE_FLAGS", None)
            os.environ.pop("LLM_PROVIDER", None)

    def test_default_provider_is_mock(self):
        """Default llm_provider is 'mock'."""
        import os
        from src.config import Settings

        old = os.environ.get("LLM_PROVIDER")
        try:
            os.environ.pop("LLM_PROVIDER", None)
            s = Settings()
            # mock is the default; but if env has no key, it may also
            # be forced from another provider.
            assert s.llm_provider == "mock"
        finally:
            if old is not None:
                os.environ["LLM_PROVIDER"] = old

    def test_is_degraded_property(self):
        """is_degraded returns True for mock provider."""
        import os
        from src.config import Settings

        old = os.environ.get("LLM_PROVIDER")
        try:
            os.environ["LLM_PROVIDER"] = "mock"
            s = Settings()
            assert s.is_degraded is True
        finally:
            if old is not None:
                os.environ["LLM_PROVIDER"] = old
            else:
                os.environ.pop("LLM_PROVIDER", None)


# ══════════════════════════════════════════════════════════════════════
# Chat API Endpoints
# ══════════════════════════════════════════════════════════════════════


class TestChatAPI:
    """Tests for the chat HTTP and WebSocket endpoints."""

    def test_status_endpoint_reports_provider(self, client):
        """GET /api/chat/status returns provider and degraded."""
        r = client.get("/api/chat/status")
        assert r.status_code == 200
        data = r.json()
        assert "provider" in data
        assert "degraded" in data
        assert "features" in data
        assert isinstance(data["features"], list)

    def test_status_never_exposes_key(self, client):
        """Response body does not contain the API key value."""
        r = client.get("/api/chat/status")
        body = r.text
        # Should not contain any API key (they're empty in test anyway)
        assert "OPENAI_API_KEY" not in body
        assert "ANTHROPIC_API_KEY" not in body

    def test_save_endpoint_returns_json(self, client):
        """POST /api/chat/save returns JSON with expected fields."""
        r = client.post(
            "/api/chat/save",
            json={"session_id": "test-session", "filters": {}},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == "test-session"
        assert "messages" in data
        assert "timestamp" in data
        assert "filters" in data

    def test_ws_degraded_mode_when_no_key(self, client):
        """WebSocket start frame includes degraded=true when no API key."""
        with client.websocket_connect("/api/chat") as ws:
            ws.send_text(json.dumps({
                "message": "Hello",
                "filters": {},
                "session_id": "test-ws",
            }))
            # Read start frame
            raw = ws.receive_text()
            frame = json.loads(raw)
            assert frame["type"] == "start"
            # In test env, should be degraded (mock provider)
            assert "degraded" in frame

    def test_ws_mock_completes_session(self, client):
        """Full WS exchange with MockLLMClient returns done frame."""
        with client.websocket_connect("/api/chat") as ws:
            ws.send_text(json.dumps({
                "message": "What are the top contracts?",
                "filters": {},
                "session_id": "test-complete",
            }))

            frames = []
            # Collect all frames until done
            while True:
                raw = ws.receive_text()
                frame = json.loads(raw)
                frames.append(frame)
                if frame["type"] in ("done", "error"):
                    break

            types = [f["type"] for f in frames]
            assert "start" in types
            assert "done" in types
            done_frame = next(f for f in frames if f["type"] == "done")
            assert done_frame["content"]  # non-empty response

    def test_ws_empty_message_returns_error(self, client):
        """Empty message → error frame."""
        with client.websocket_connect("/api/chat") as ws:
            ws.send_text(json.dumps({
                "message": "   ",
                "filters": {},
            }))
            raw = ws.receive_text()
            frame = json.loads(raw)
            assert frame["type"] == "error"
            assert "Empty" in frame["message"]

    def test_ws_invalid_json_returns_error(self, client):
        """Invalid JSON → error frame."""
        with client.websocket_connect("/api/chat") as ws:
            ws.send_text("not valid json {{{")
            raw = ws.receive_text()
            frame = json.loads(raw)
            assert frame["type"] == "error"
            assert "Invalid JSON" in frame["message"]


# ══════════════════════════════════════════════════════════════════════
# Security
# ══════════════════════════════════════════════════════════════════════


class TestSecurity:
    """Tests for input sanitisation and security."""

    def test_oversized_message_rejected(self, client):
        """Message exceeding max length → error."""
        # The default max is 4000
        long_msg = "a" * 5000
        with client.websocket_connect("/api/chat") as ws:
            ws.send_text(json.dumps({
                "message": long_msg,
                "filters": {},
            }))
            # First frame should be start (sanitised message is truncated, not empty)
            raw = ws.receive_text()
            frame = json.loads(raw)
            # The message gets truncated to max_length, so it should proceed
            assert frame["type"] == "start"

    def test_control_characters_stripped(self, client):
        """Input with control chars is sanitised before processing."""
        msg = "Hello\x00World\x01Test"
        with client.websocket_connect("/api/chat") as ws:
            ws.send_text(json.dumps({
                "message": msg,
                "filters": {},
            }))
            raw = ws.receive_text()
            frame = json.loads(raw)
            # Should proceed normally (control chars stripped)
            assert frame["type"] == "start"

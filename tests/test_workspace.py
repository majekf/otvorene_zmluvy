"""
Unit tests for Phase 7 — Workspace save/load.

Tests cover: workspace save → load round-trip and chat-history inclusion.
"""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from src.api import app, get_store, _chat_history
from src.engine import DataStore


# ── Test data ────────────────────────────────────────────────────────

SMALL_RECORDS = [
    {
        "contract_id": "W001",
        "contract_title": "Workspace test contract",
        "buyer": "Mesto Bratislava",
        "supplier": "STRABAG s.r.o.",
        "price_numeric_eur": 100_000.0,
        "published_date": "2025-12-01",
        "category": "construction",
        "award_type": "direct_award",
    },
    {
        "contract_id": "W002",
        "contract_title": "IT projekt",
        "buyer": "Mesto Košice",
        "supplier": "T-Systems s.r.o.",
        "price_numeric_eur": 50_000.0,
        "published_date": "2026-01-15",
        "category": "IT",
        "award_type": "open_tender",
    },
]


@pytest.fixture
def test_store():
    ds = DataStore()
    ds.load_from_list(SMALL_RECORDS)
    return ds


@pytest.fixture
def client(test_store):
    app.dependency_overrides[get_store] = lambda: test_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Workspace save / load ────────────────────────────────────────────


class TestWorkspaceSaveLoad:
    """Tests for /api/workspace/save and /api/workspace/load."""

    def test_save_and_load_round_trip(self, client):
        """Save → load restores identical filter state and mode."""
        payload = {
            "filters": {
                "institutions": ["Mesto Bratislava"],
                "date_from": "2025-01-01",
            },
            "groupBy": "supplier",
            "sort": [["price_numeric_eur", "desc"]],
            "page": 2,
            "mode": "dashboard",
            "chartState": {"vizMode": "treemap"},
        }
        save_r = client.post("/api/workspace/save", json=payload)
        assert save_r.status_code == 200
        data = save_r.json()
        assert "token" in data
        assert "snapshot" in data

        token = data["token"]
        snapshot = data["snapshot"]
        assert snapshot["filters"]["institutions"] == ["Mesto Bratislava"]
        assert snapshot["groupBy"] == "supplier"
        assert snapshot["sort"] == [["price_numeric_eur", "desc"]]
        assert snapshot["page"] == 2
        assert snapshot["mode"] == "dashboard"
        assert "saved_at" in snapshot

        # Load
        load_r = client.get("/api/workspace/load", params={"token": token})
        assert load_r.status_code == 200
        loaded = load_r.json()["snapshot"]
        assert loaded["filters"] == snapshot["filters"]
        assert loaded["groupBy"] == snapshot["groupBy"]
        assert loaded["sort"] == snapshot["sort"]
        assert loaded["page"] == snapshot["page"]
        assert loaded["mode"] == snapshot["mode"]

    def test_save_includes_chat_history(self, client):
        """Workspace snapshot contains chat messages when session_id is given."""
        session_id = "test-ws-session-123"
        _chat_history.append(session_id, "user", "What is the total spend?")
        _chat_history.append(session_id, "assistant", "The total spend is 150,000 EUR.")

        payload = {
            "filters": {},
            "session_id": session_id,
        }
        save_r = client.post("/api/workspace/save", json=payload)
        assert save_r.status_code == 200
        snapshot = save_r.json()["snapshot"]
        assert len(snapshot["chat_history"]) == 2
        assert snapshot["chat_history"][0]["role"] == "user"
        assert snapshot["chat_history"][1]["role"] == "assistant"

        # Clean up
        _chat_history.clear(session_id)

    def test_load_invalid_token_returns_400(self, client):
        """Invalid base64 token returns 400."""
        r = client.get("/api/workspace/load", params={"token": "!!!invalid!!!"})
        assert r.status_code == 400

    def test_load_non_json_token_returns_400(self, client):
        """Base64 token that decodes to non-JSON returns 400."""
        token = base64.urlsafe_b64encode(b"not json at all").decode()
        r = client.get("/api/workspace/load", params={"token": token})
        assert r.status_code == 400

    def test_save_minimal_payload(self, client):
        """Empty payload produces a valid snapshot with defaults."""
        save_r = client.post("/api/workspace/save", json={})
        assert save_r.status_code == 200
        snapshot = save_r.json()["snapshot"]
        assert snapshot["version"] == 1
        assert snapshot["filters"] == {}
        assert snapshot["mode"] == "dashboard"

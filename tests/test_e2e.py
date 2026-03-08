"""
End-to-end integration tests for Phase 8.

Tests cover full workflows: load → filter → benchmark → export,
chatbot scoped-context, and rule evaluation pipeline.
Uses FastAPI TestClient (no real HTTP server needed).
"""

import csv
import io
import json
import os

import pytest
from fastapi.testclient import TestClient

import src.api as _api_module
from src.api import app, get_store
from src.chatbot.llm import MockLLMClient
from src.engine import DataStore
from src.models import FilterState

# ── Helpers ──────────────────────────────────────────────────────────

SAMPLE_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "test_data.json"
)


@pytest.fixture(autouse=True)
def _inject_sample_store():
    """Load the real sample data into the app for every test."""
    store = DataStore(SAMPLE_DATA_PATH)
    app.dependency_overrides[get_store] = lambda: store
    # Also set app.state.store for WebSocket handler (accesses it directly)
    app.state.store = store
    # Force mock LLM so tests are deterministic regardless of .env API keys
    _original_llm = _api_module._llm_client
    _api_module._llm_client = MockLLMClient()
    yield
    _api_module._llm_client = _original_llm
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def store():
    return DataStore(SAMPLE_DATA_PATH)


# ── Test: full_workflow ──────────────────────────────────────────────


class TestFullWorkflow:
    """
    End-to-end: load data → filter → aggregate → benchmark → export CSV
    and verify the content is consistent across the pipeline.
    """

    def test_load_contracts_and_filter(self, client: TestClient):
        """Load all contracts, then filter and verify subset."""
        # 1. List all contracts
        resp = client.get("/api/contracts?page_size=100")
        assert resp.status_code == 200
        all_data = resp.json()
        total = all_data["total"]
        assert total > 0, "Sample data should have contracts"

        # 2. Pick the first institution from the data
        first_buyer = all_data["contracts"][0]["buyer"]

        # 3. Filter by that institution (API uses 'institutions' param, comma-separated)
        resp2 = client.get(f"/api/contracts?institutions={first_buyer}&page_size=100")
        assert resp2.status_code == 200
        filtered = resp2.json()
        assert filtered["total"] <= total
        assert filtered["total"] > 0
        for c in filtered["contracts"]:
            assert c["buyer"] == first_buyer

    def test_filter_aggregate_export_consistency(self, client: TestClient):
        """Filter → aggregate → export CSV all return consistent data."""
        institution = None
        # Find an institution with contracts
        resp = client.get("/api/institutions")
        assert resp.status_code == 200
        institutions = resp.json()["institutions"]
        assert len(institutions) > 0
        institution = institutions[0]["name"]

        # Get filtered contracts
        resp_contracts = client.get(
            f"/api/contracts?institutions={institution}&page_size=200"
        )
        assert resp_contracts.status_code == 200
        contracts_data = resp_contracts.json()
        filtered_count = contracts_data["total"]

        # Get aggregations for same filter
        resp_agg = client.get(
            f"/api/aggregations?institutions={institution}&group_by=category"
        )
        assert resp_agg.status_code == 200
        agg_data = resp_agg.json()
        agg_count = agg_data["summary"]["contract_count"]
        assert agg_count == filtered_count, (
            f"Aggregation count ({agg_count}) must match filter count ({filtered_count})"
        )

        # Export CSV for same filter
        resp_csv = client.get(f"/api/export/csv?institutions={institution}")
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv.headers["content-type"]
        reader = csv.DictReader(io.StringIO(resp_csv.text))
        csv_rows = list(reader)
        assert len(csv_rows) == filtered_count, (
            f"CSV rows ({len(csv_rows)}) must match filter count ({filtered_count})"
        )

    def test_benchmark_comparison(self, client: TestClient):
        """Select institutions → compare → verify comparison data."""
        # Get institution list
        resp = client.get("/api/institutions")
        institutions = resp.json()["institutions"]
        if len(institutions) < 2:
            pytest.skip("Need at least 2 institutions for benchmark test")

        names = [institutions[0]["name"], institutions[1]["name"]]

        # API uses pipe-separated institution names
        institutions_param = "|".join(names)
        resp_bm = client.get(
            f"/api/benchmark?institutions={institutions_param}&metric=total_spend"
        )
        assert resp_bm.status_code == 200
        bm_data = resp_bm.json()
        assert "results" in bm_data
        assert len(bm_data["results"]) == 2

    def test_treemap_data_structure(self, client: TestClient):
        """Treemap endpoint returns valid hierarchical data."""
        resp = client.get("/api/treemap?group_by=category")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "children" in data

    def test_rankings_consistency(self, client: TestClient):
        """Rankings return valid sorted data."""
        resp = client.get("/api/rankings?metric=total_spend&entity=institutions")
        assert resp.status_code == 200
        data = resp.json()
        rankings = data["rankings"]
        assert len(rankings) > 0
        # Verify sorted descending
        values = [r["value"] for r in rankings]
        assert values == sorted(values, reverse=True), "Rankings must be sorted descending"

    def test_pdf_export(self, client: TestClient):
        """PDF export returns valid PDF content."""
        resp = client.get("/api/export/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF magic bytes
        assert resp.content[:4] == b"%PDF"


# ── Test: chatbot_workflow ───────────────────────────────────────────


class TestChatbotWorkflow:
    """
    End-to-end: set filters → ask chatbot → verify scoped response.
    Uses MockLLMClient (no real API key needed).
    """

    def test_chat_status_reports_mock(self, client: TestClient):
        """Chat status endpoint reports the mock provider."""
        resp = client.get("/api/chat/status")
        assert resp.status_code == 200
        status = resp.json()
        assert "provider" in status
        assert "degraded" in status
        # Mock provider should be active (no API key in test env)
        assert status["provider"] in ("mock", "openai")

    def test_chat_websocket_mock_session(self, client: TestClient):
        """Full WebSocket chat exchange with MockLLMClient."""
        with client.websocket_connect("/api/chat") as ws:
            ws.send_json({
                "message": "What are the largest contracts?",
                "filters": {},
                "session_id": "e2e-test-session",
            })
            # Read frames until we get a 'done' frame
            frames = []
            while True:
                try:
                    text = ws.receive_text()
                    frame = json.loads(text)
                    frames.append(frame)
                    if frame.get("type") in ("done", "error"):
                        break
                except Exception:
                    break

            # Should have at least a start and done frame
            frame_types = [f.get("type") for f in frames]
            assert "done" in frame_types, f"Expected 'done' frame, got: {frame_types}"

    def test_chat_save_endpoint(self, client: TestClient):
        """Save chat conversation returns valid JSON."""
        resp = client.post(
            "/api/chat/save",
            json={
                "session_id": "e2e-save-test",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"},
                ],
                "filters": {"institutions": ["Test"]},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data or "session_id" in data

    def test_scoped_context_with_filters(self, store: DataStore):
        """Build scoped context respects filter constraints."""
        from src.chatbot.context import build_scoped_context

        fs = FilterState(institutions=["Mesto Bratislava"])
        ctx = build_scoped_context(fs, store)
        # Context should be a non-empty string
        assert isinstance(ctx, str) or isinstance(ctx, tuple)
        if isinstance(ctx, tuple):
            ctx_str, provenance = ctx
            assert len(ctx_str) > 0
        else:
            assert len(ctx) > 0


# ── Test: rule_workflow ──────────────────────────────────────────────


class TestRuleWorkflow:
    """
    End-to-end: load data → evaluate rules → verify flagged contracts.
    """

    def test_preset_rules_listed(self, client: TestClient):
        """Presets endpoint returns available rules."""
        resp = client.get("/api/rules/presets")
        assert resp.status_code == 200
        data = resp.json()
        presets = data["presets"]
        assert isinstance(presets, list)
        assert len(presets) > 0
        # Each preset has a name and default params
        for preset in presets:
            assert "name" in preset
            assert "params" in preset

    def test_evaluate_all_presets(self, client: TestClient):
        """Evaluate all preset rules against the sample data."""
        # Get presets
        resp = client.get("/api/rules/presets")
        presets = resp.json()["presets"]
        # Build rules config as list of dicts with id + params
        rules_cfg = [{"id": p["id"], "params": p["params"]} for p in presets]

        # Evaluate
        resp_eval = client.post(
            "/api/rules/evaluate",
            json={"rules": rules_cfg},
        )
        assert resp_eval.status_code == 200
        result = resp_eval.json()
        assert "flags" in result
        # Flags is a list (may be empty if no rules fire on sample data)
        assert isinstance(result["flags"], list)

    def test_custom_condition_evaluation(self, client: TestClient):
        """Evaluate a custom condition against sample data."""
        resp = client.post(
            "/api/rules/custom",
            json={
                "logic": "AND",
                "conditions": [
                    {
                        "field": "price_numeric_eur",
                        "operator": "gt",
                        "value": 100000,
                    }
                ],
                "filters": {},
            },
        )
        assert resp.status_code == 200
        result = resp.json()
        assert "contracts" in result or "matches" in result or "flags" in result

    def test_rule_flags_have_severity(self, client: TestClient):
        """Flagged contracts include severity scores."""
        resp = client.post(
            "/api/rules/evaluate",
            json={
                "rules": [
                    {"id": "threshold_proximity", "params": {"threshold_eur": 100000, "proximity_pct": 10}},
                    {"id": "round_number_clustering", "params": {"round_modulus": 1000, "min_round_pct": 60, "min_contracts": 5}},
                ],
            },
        )
        assert resp.status_code == 200
        result = resp.json()
        flags = result["flags"]
        for flag in flags:
            assert "severity" in flag
            assert 0 <= flag["severity"] <= 1.0

    def test_workspace_save_load_round_trip(self, client: TestClient):
        """Save workspace → load → verify filter state survives."""
        # Save
        payload = {
            "filters": {"institutions": ["Mesto Bratislava"], "date_from": "2025-01-01"},
            "sort": [["price_numeric_eur", "desc"]],
            "mode": "dashboard",
        }
        resp_save = client.post("/api/workspace/save", json=payload)
        assert resp_save.status_code == 200
        token = resp_save.json()["token"]

        # Load — API returns {"snapshot": {...}}
        resp_load = client.get(f"/api/workspace/load?token={token}")
        assert resp_load.status_code == 200
        loaded = resp_load.json()["snapshot"]
        assert loaded["filters"]["institutions"] == ["Mesto Bratislava"]
        assert loaded["filters"]["date_from"] == "2025-01-01"

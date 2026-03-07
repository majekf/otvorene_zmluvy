"""
GovLens Backend API (Phase 2 + Phase 4 + Phase 5 + Phase 7)

FastAPI application exposing the in-memory query engine
over HTTP REST endpoints with filtering, aggregation,
treemap, benchmark, trends, rankings, CSV/PDF export,
workspace save/load, rule evaluation, condition builder,
and contextual chatbot.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import asyncio
import base64
import csv
import datetime
import io
import json
import logging
import math
import re
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import settings
from .engine import DataStore, SORTABLE_FIELDS
from .models import FilterState
from .rules.engine import RuleEngine, PRESET_RULES
from .rules.builder import ConditionGroup
from .chatbot.protocol import (
    StartFrame,
    TokenFrame,
    DoneFrame,
    ErrorFrame,
    ProvenanceItem,
    ScopeRefusalData,
)
from .chatbot.llm import create_llm_client, MockLLMClient
from .chatbot.context import build_scoped_context
from .chatbot.scope import check_scope
from .chatbot.history import create_history
from .chatbot.usage import UsageTracker

logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the DataStore at startup."""
    data_path = Path(settings.data_path)
    try:
        if data_path.exists():
            app.state.store = DataStore(str(data_path))
        else:
            app.state.store = DataStore()
    except Exception:
        app.state.store = DataStore()
    yield


# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="GovLens API",
    description="Slovak government contract analytics API",
    version="2.0.0",
    lifespan=lifespan,
)

# Shared rule engine instance
_rule_engine = RuleEngine()

# ── Chatbot state (Phase 5) ─────────────────────────────────────────
_llm_client = create_llm_client(
    provider=settings.llm_provider,
    api_key=settings.openai_api_key or settings.anthropic_api_key,
    model=settings.openai_model,
    temperature=settings.openai_temperature,
)
_chat_history = create_history(backend=settings.chat_history_backend)
_usage_tracker = UsageTracker(enabled=settings.chat_cost_tracking)


def _runtime_chat_state() -> Tuple[str, bool]:
    """Return effective provider and degraded flag for the active chat client."""
    if isinstance(_llm_client, MockLLMClient):
        return "mock", True
    return settings.llm_provider, False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Dependencies ─────────────────────────────────────────────────────


def get_store() -> DataStore:
    """Return the application DataStore instance."""
    return app.state.store


def parse_filters(
    institutions: Optional[str] = Query(
        None, description="Pipe-separated buyer names"
    ),
    date_from: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    date_to: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD)"
    ),
    categories: Optional[str] = Query(
        None, description="Pipe-separated categories"
    ),
    vendors: Optional[str] = Query(
        None, description="Pipe-separated supplier names"
    ),
    value_min: Optional[float] = Query(
        None, description="Minimum EUR value"
    ),
    value_max: Optional[float] = Query(
        None, description="Maximum EUR value"
    ),
    award_types: Optional[str] = Query(
        None, description="Pipe-separated award types"
    ),
    text_search: Optional[str] = Query(
        None, description="Full-text search query"
    ),
) -> FilterState:
    """Build a FilterState from query parameters.

    List-type fields are passed as pipe-separated strings.
    """
    return FilterState(
        institutions=(
            institutions.split("|") if institutions else None
        ),
        date_from=date_from,
        date_to=date_to,
        categories=categories.split("|") if categories else None,
        vendors=vendors.split("|") if vendors else None,
        value_min=value_min,
        value_max=value_max,
        award_types=(
            award_types.split("|") if award_types else None
        ),
        text_search=text_search,
    )


def parse_sort(
    sort: Optional[str] = Query(
        None,
        description=(
            "Sort spec: field:dir,field:dir "
            "(e.g. price_numeric_eur:desc,published_date:asc)"
        ),
    ),
) -> List[Tuple[str, str]]:
    """Parse the ``sort`` query parameter into a list of (field, direction) tuples.

    Each token is ``<field>:<direction>`` where direction is ``asc`` or ``desc``.
    Tokens with unknown fields are kept as-is; ``engine.sort_contracts`` silently
    ignores fields not in ``SORTABLE_FIELDS``.
    """
    if not sort:
        return []
    result: List[Tuple[str, str]] = []
    for part in sort.split(","):
        part = part.strip()
        if ":" in part:
            field, direction = part.split(":", 1)
            result.append((field.strip(), direction.strip().lower()))
        elif part:
            result.append((part.strip(), "asc"))
    return result


# ── Filter-state serialisation ───────────────────────────────────────


def encode_filter_state(
    fs: FilterState,
    sort_spec: Optional[List[Tuple[str, str]]] = None,
    group_by: Optional[str] = None,
    mode: Optional[str] = None,
    page: Optional[int] = None,
) -> Dict[str, str]:
    """Encode a FilterState into URL query-parameter dict.

    Round-trips with ``parse_filters`` and ``parse_sort``.

    Args:
        fs: The filter state to encode.
        sort_spec: Optional sort specification as a list of
                   ``(field, direction)`` tuples.  When provided, the
                   encoded dict will contain a ``sort`` key.
        group_by: Optional group-by field (e.g. ``'category'``, ``'supplier'``).
        mode: Optional active mode identifier (e.g. ``'dashboard'``, ``'benchmark'``).
        page: Optional current page number.
    """
    params: Dict[str, str] = {}
    if fs.institutions:
        params["institutions"] = "|".join(fs.institutions)
    if fs.date_from:
        params["date_from"] = fs.date_from
    if fs.date_to:
        params["date_to"] = fs.date_to
    if fs.categories:
        params["categories"] = "|".join(fs.categories)
    if fs.vendors:
        params["vendors"] = "|".join(fs.vendors)
    if fs.value_min is not None:
        params["value_min"] = str(fs.value_min)
    if fs.value_max is not None:
        params["value_max"] = str(fs.value_max)
    if fs.award_types:
        params["award_types"] = "|".join(fs.award_types)
    if fs.text_search:
        params["text_search"] = fs.text_search
    if sort_spec:
        params["sort"] = ",".join(
            f"{field}:{direction}" for field, direction in sort_spec
        )
    if group_by:
        params["group_by"] = group_by
    if mode:
        params["mode"] = mode
    if page is not None and page > 1:
        params["page"] = str(page)
    return params


# ── Endpoints — Contracts ────────────────────────────────────────────


@app.get("/api/contracts")
def list_contracts(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    sort_spec: List[Tuple[str, str]] = Depends(parse_sort),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
):
    """Paginated, filterable, sortable contract list."""
    all_contracts = store.filter(filters)
    if sort_spec:
        all_contracts = store.sort_contracts(all_contracts, sort_spec)
    total = len(all_contracts)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "contracts": [c.model_dump() for c in all_contracts[start:end]],
    }


@app.get("/api/contracts/{contract_id}")
def get_contract(
    contract_id: str,
    store: DataStore = Depends(get_store),
):
    """Single contract by ID."""
    for c in store.contracts:
        if c.contract_id == contract_id:
            return c.model_dump()
    raise HTTPException(
        status_code=404,
        detail=f"Contract {contract_id} not found",
    )


# ── Endpoints — Aggregations ────────────────────────────────────────


@app.get("/api/aggregations")
def get_aggregations(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    group_by: str = Query(
        "category", description="Field to group by"
    ),
):
    """Group-by + aggregation over filtered contracts."""
    filtered = store.filter(filters)
    results = store.aggregate_groups(group_by, filtered)
    return {
        "group_by": group_by,
        "results": [r.model_dump() for r in results],
        "summary": store.aggregate(filtered),
    }


# ── Endpoints — Treemap ─────────────────────────────────────────────


@app.get("/api/treemap")
def get_treemap(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    group_by: str = Query(
        "category", description="Primary grouping field"
    ),
    sub_group_by: Optional[str] = Query(
        None, description="Secondary grouping field"
    ),
):
    """Hierarchical data suitable for D3 treemap visualisation."""
    filtered = store.filter(filters)
    groups = store.group_by(group_by, filtered)

    children: List[Dict[str, Any]] = []
    for group_name, contracts in groups.items():
        if group_name is None:
            continue
        stats = store.aggregate(contracts)
        node: Dict[str, Any] = {
            "name": group_name,
            "value": stats["total_spend"],
            "contract_count": stats["contract_count"],
        }
        if sub_group_by:
            sub_groups = store.group_by(sub_group_by, contracts)
            sub_children: List[Dict[str, Any]] = []
            for sub_name, sub_contracts in sub_groups.items():
                if sub_name is None:
                    continue
                sub_stats = store.aggregate(sub_contracts)
                sub_children.append(
                    {
                        "name": sub_name,
                        "value": sub_stats["total_spend"],
                        "contract_count": sub_stats["contract_count"],
                    }
                )
            sub_children.sort(key=lambda x: x["value"], reverse=True)
            node["children"] = sub_children
        children.append(node)

    children.sort(key=lambda x: x["value"], reverse=True)
    summary = store.aggregate(filtered)

    return {
        "name": "root",
        "value": summary["total_spend"],
        "children": children,
    }


# ── Endpoints — Benchmark ───────────────────────────────────────────


@app.get("/api/benchmark")
def get_benchmark(
    store: DataStore = Depends(get_store),
    institutions: str = Query(
        ..., description="Pipe-separated institution names"
    ),
    metric: str = Query(
        "total_spend", description="Comparison metric"
    ),
    min_contracts: Optional[int] = Query(
        None, description="Minimum contract count for peer-group filter"
    ),
):
    """Compare institutions side-by-side on a metric."""
    inst_list = [n.strip() for n in institutions.split("|")]
    results = store.compare(inst_list, metric=metric)
    if min_contracts is not None:
        # Post-filter: only include institutions meeting the threshold
        inst_counts = {i.name: i.contract_count for i in store.institutions()}
        results = [
            r for r in results
            if inst_counts.get(r["institution"], 0) >= min_contracts
        ]
    return {
        "metric": metric,
        "results": results,
    }


@app.get("/api/benchmark/peers")
def get_benchmark_peers(
    store: DataStore = Depends(get_store),
    institution: str = Query(
        ..., description="Target institution name"
    ),
    min_contracts: int = Query(
        1, ge=1, description="Minimum contract count for peers"
    ),
):
    """Return a peer group for the given institution.

    Peers are institutions with at least ``min_contracts`` contracts,
    excluding the target institution itself.
    """
    peers = store.peer_group(institution, min_contracts=min_contracts)
    return {
        "institution": institution,
        "min_contracts": min_contracts,
        "peers": peers,
    }


@app.get("/api/benchmark/compare")
def get_benchmark_compare(
    store: DataStore = Depends(get_store),
    institutions: str = Query(
        ..., description="Pipe-separated institution names"
    ),
    metrics: str = Query(
        "total_spend",
        description="Comma-separated metrics to compare",
    ),
):
    """Compare institutions across multiple metrics simultaneously."""
    inst_list = [n.strip() for n in institutions.split("|")]
    metric_list = [m.strip() for m in metrics.split(",")]
    results = store.compare_multi_metric(inst_list, metric_list)
    return {
        "metrics": metric_list,
        "results": results,
    }


# ── Endpoints — Trends ──────────────────────────────────────────────

# Well-known overlay dates (election / budget events in Slovakia)
OVERLAY_DATES: List[Dict[str, str]] = [
    {"date": "2020-02-29", "label": "Parliamentary Election 2020"},
    {"date": "2023-09-30", "label": "Parliamentary Election 2023"},
    {"date": "2022-10-29", "label": "Municipal Election 2022"},
    {"date": "2024-01-01", "label": "Budget Year 2024"},
    {"date": "2025-01-01", "label": "Budget Year 2025"},
    {"date": "2026-01-01", "label": "Budget Year 2026"},
]


@app.get("/api/trends")
def get_trends(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    granularity: str = Query(
        "month", description="Time granularity: month, quarter, year"
    ),
    metric: str = Query(
        "total_spend", description="Metric to trend"
    ),
    metrics: Optional[str] = Query(
        None,
        description="Comma-separated list of metrics (overrides single metric param)",
    ),
    overlay: bool = Query(
        False,
        description="Include overlay dates (elections, budget events)",
    ),
):
    """Time-series trend data with optional multi-metric and overlays."""
    filtered = store.filter(filters)

    if metrics:
        metric_list = [m.strip() for m in metrics.split(",")]
        data = store.trend_multi_metric(
            granularity=granularity,
            contracts=filtered,
            metrics=metric_list,
        )
        result: Dict[str, Any] = {
            "granularity": granularity,
            "metrics": metric_list,
            "data": data,
        }
    else:
        result = {
            "granularity": granularity,
            "metric": metric,
            "data": store.trend(
                granularity=granularity,
                contracts=filtered,
                metric=metric,
            ),
        }

    if overlay:
        result["overlays"] = OVERLAY_DATES

    return result


# ── Endpoints — Rankings ────────────────────────────────────────────


@app.get("/api/rankings")
def get_rankings(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    entity: str = Query(
        "institutions",
        description="Entity type: institutions or vendors",
    ),
    metric: str = Query(
        "total_spend", description="Ranking metric"
    ),
):
    """Ranked list of institutions or vendors.

    Supports metrics: total_spend, contract_count, avg_value,
    max_value, direct_award_rate, vendor_concentration,
    fragmentation_score (institutions only).
    Accepts filters to restrict the contract set before ranking.
    """
    filtered = store.filter(filters)

    if entity == "vendors":
        rankings = _rank_vendors_from(store, filtered, metric)
    else:
        rankings = _rank_institutions_from(store, filtered, metric)

    return {
        "entity": entity,
        "metric": metric,
        "rankings": rankings,
    }


def _rank_institutions_from(
    store: DataStore,
    contracts: List,
    metric: str,
) -> List[Dict[str, Any]]:
    """Rank institutions computed from *contracts* (already filtered)."""
    # Group contracts by buyer
    groups = store.group_by("buyer", contracts)
    ranked: List[Dict[str, Any]] = []

    for name, group_contracts in groups.items():
        if name is None:
            continue
        stats = store.aggregate(group_contracts)

        if metric == "total_spend":
            value = stats["total_spend"]
        elif metric == "contract_count":
            value = float(stats["contract_count"])
        elif metric == "direct_award_rate":
            value = store.direct_award_rate(group_contracts)
        elif metric == "vendor_concentration":
            value = store.vendor_concentration_score(group_contracts)
        elif metric == "fragmentation_score":
            value = store.fragmentation_score(group_contracts)
        elif metric in ("avg_value", "max_value"):
            value = stats.get(metric, 0.0)
        else:
            value = stats["total_spend"]

        ranked.append({"institution": name, "value": value})

    ranked.sort(key=lambda r: r["value"], reverse=True)
    for i, item in enumerate(ranked, 1):
        item["rank"] = i
    return ranked


def _rank_vendors_from(
    store: DataStore,
    contracts: List,
    metric: str,
) -> List[Dict[str, Any]]:
    """Rank vendors computed from *contracts* (already filtered)."""
    groups = store.group_by("supplier", contracts)
    ranked: List[Dict[str, Any]] = []

    for name, group_contracts in groups.items():
        if name is None:
            continue
        stats = store.aggregate(group_contracts)

        if metric == "total_spend":
            value = stats["total_spend"]
        elif metric == "contract_count":
            value = float(stats["contract_count"])
        elif metric in ("avg_value", "max_value"):
            value = stats.get(metric, 0.0)
        else:
            value = stats["total_spend"]

        ranked.append({"vendor": name, "value": value})

    ranked.sort(key=lambda r: r["value"], reverse=True)
    for i, item in enumerate(ranked, 1):
        item["rank"] = i
    return ranked


# ── Endpoints — Institutions ────────────────────────────────────────


@app.get("/api/institutions")
def list_institutions(store: DataStore = Depends(get_store)):
    """List of all unique institutions (buyers) with stats."""
    return {
        "institutions": [i.model_dump() for i in store.institutions()],
    }


@app.get("/api/institutions/{identifier}")
def get_institution(
    identifier: str,
    store: DataStore = Depends(get_store),
):
    """Institution profile (by ICO or name).

    Includes stats, top vendors, monthly trend, and contracts.
    """
    # Try ICO first, then name
    contracts = [c for c in store.contracts if c.ico_buyer == identifier]
    if not contracts:
        contracts = [c for c in store.contracts if c.buyer == identifier]
    if not contracts:
        raise HTTPException(
            status_code=404,
            detail=f"Institution '{identifier}' not found",
        )

    name = contracts[0].buyer
    ico = next((c.ico_buyer for c in contracts if c.ico_buyer), None)
    stats = store.aggregate(contracts)

    # Top vendors for this institution
    vendor_groups = store.group_by("supplier", contracts)
    top_vendors: List[Dict[str, Any]] = []
    for vname, vcontracts in vendor_groups.items():
        if vname is None:
            continue
        vstats = store.aggregate(vcontracts)
        top_vendors.append(
            {
                "name": vname,
                "contract_count": vstats["contract_count"],
                "total_spend": vstats["total_spend"],
            }
        )
    top_vendors.sort(key=lambda x: x["total_spend"], reverse=True)

    trend = store.trend(granularity="month", contracts=contracts)

    return {
        "name": name,
        "ico": ico,
        "contract_count": stats["contract_count"],
        "total_spend": stats["total_spend"],
        "avg_value": stats["avg_value"],
        "max_value": stats["max_value"],
        "top_vendors": top_vendors[:10],
        "trend": trend,
        "contracts": [c.model_dump() for c in contracts],
    }


# ── Endpoints — Vendors ─────────────────────────────────────────────


@app.get("/api/vendors")
def list_vendors(store: DataStore = Depends(get_store)):
    """List of all unique vendors (suppliers) with stats."""
    return {
        "vendors": [v.model_dump() for v in store.vendors()],
    }


@app.get("/api/vendors/{identifier}")
def get_vendor(
    identifier: str,
    store: DataStore = Depends(get_store),
):
    """Vendor profile (by ICO or name).

    Includes stats, institutions served, monthly trend, and contracts.
    """
    contracts = [c for c in store.contracts if c.ico_supplier == identifier]
    if not contracts:
        contracts = [c for c in store.contracts if c.supplier == identifier]
    if not contracts:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor '{identifier}' not found",
        )

    name = contracts[0].supplier
    ico = next((c.ico_supplier for c in contracts if c.ico_supplier), None)
    stats = store.aggregate(contracts)

    # Institutions served
    buyer_groups = store.group_by("buyer", contracts)
    institutions_served: List[Dict[str, Any]] = []
    for iname, icontracts in buyer_groups.items():
        if iname is None:
            continue
        istats = store.aggregate(icontracts)
        institutions_served.append(
            {
                "name": iname,
                "contract_count": istats["contract_count"],
                "total_spend": istats["total_spend"],
            }
        )
    institutions_served.sort(
        key=lambda x: x["total_spend"], reverse=True
    )

    trend = store.trend(granularity="month", contracts=contracts)

    return {
        "name": name,
        "ico": ico,
        "contract_count": stats["contract_count"],
        "total_spend": stats["total_spend"],
        "avg_value": stats["avg_value"],
        "max_value": stats["max_value"],
        "institutions_served": institutions_served,
        "trend": trend,
        "contracts": [c.model_dump() for c in contracts],
    }


# ── Endpoints — Export ───────────────────────────────────────────────

CSV_FIELDS = [
    "contract_id",
    "contract_title",
    "buyer",
    "supplier",
    "price_numeric_eur",
    "published_date",
    "category",
    "award_type",
    "contract_url",
]


@app.get("/api/export/csv")
def export_csv(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    sort_spec: List[Tuple[str, str]] = Depends(parse_sort),
):
    """Export filtered contracts as CSV, respecting sort order."""
    filtered = store.filter(filters)
    if sort_spec:
        filtered = store.sort_contracts(filtered, sort_spec)

    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=CSV_FIELDS, extrasaction="ignore"
    )
    writer.writeheader()
    for c in filtered:
        d = c.model_dump()
        row = {k: (d.get(k) if d.get(k) is not None else "") for k in CSV_FIELDS}
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=contracts.csv"
        },
    )


@app.get("/api/export/pdf")
def export_pdf(
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
    sort_spec: List[Tuple[str, str]] = Depends(parse_sort),
):
    """Export filtered contracts as a formatted PDF report.

    Generates a PDF with summary statistics and a contract table
    using ReportLab.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )

    filtered = store.filter(filters)
    if sort_spec:
        filtered = store.sort_contracts(filtered, sort_spec)

    stats = store.aggregate(filtered)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    elements: list = []

    # Title
    elements.append(Paragraph("GovLens — Contract Report", styles["Title"]))
    elements.append(Spacer(1, 6 * mm))

    # Summary
    summary_text = (
        f"Contracts: <b>{stats['contract_count']}</b> &nbsp;&nbsp; "
        f"Total spend: <b>{stats['total_spend']:,.2f} €</b> &nbsp;&nbsp; "
        f"Avg value: <b>{stats['avg_value']:,.2f} €</b> &nbsp;&nbsp; "
        f"Max value: <b>{stats['max_value']:,.2f} €</b>"
    )
    elements.append(Paragraph(summary_text, styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Generated timestamp
    elements.append(
        Paragraph(
            f"Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Italic"],
        )
    )
    elements.append(Spacer(1, 6 * mm))

    # Table header
    header = ["#", "Title", "Buyer", "Supplier", "Value (€)", "Date", "Category"]
    data_rows = [header]

    for idx, c in enumerate(filtered[:500], 1):  # cap at 500 rows for PDF
        d = c.model_dump()
        price = d.get("price_numeric_eur")
        price_str = f"{price:,.2f}" if price is not None else "—"
        data_rows.append([
            str(idx),
            Paragraph(str(d.get("contract_title") or "—")[:80], styles["Normal"]),
            Paragraph(str(d.get("buyer") or "—")[:40], styles["Normal"]),
            Paragraph(str(d.get("supplier") or "—")[:40], styles["Normal"]),
            price_str,
            str(d.get("published_date") or "—"),
            str(d.get("category") or "—"),
        ])

    col_widths = [25, 180, 100, 100, 70, 65, 60]
    table = Table(data_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=contracts_report.pdf"
        },
    )


# ── Endpoints — Workspace (Phase 7) ─────────────────────────────────


@app.post("/api/workspace/save")
def save_workspace(body: Dict[str, Any]):
    """Save current workspace state as a portable snapshot.

    Request body::

        {
            "filters": { ... },
            "groupBy": "category",
            "sort": [["price_numeric_eur", "desc"]],
            "page": 1,
            "mode": "dashboard",
            "chartState": { ... },
            "session_id": "optional-chat-session-id"
        }

    Returns a JSON object with a base64-encoded token that can be
    used to restore the workspace.
    """
    session_id = body.get("session_id", "")
    chat_messages = _chat_history.get(session_id) if session_id else []

    snapshot: Dict[str, Any] = {
        "version": 1,
        "filters": body.get("filters", {}),
        "groupBy": body.get("groupBy", "category"),
        "sort": body.get("sort", []),
        "page": body.get("page", 1),
        "mode": body.get("mode", "dashboard"),
        "chartState": body.get("chartState", {}),
        "chat_history": chat_messages,
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    token = base64.urlsafe_b64encode(
        json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    return {
        "token": token,
        "snapshot": snapshot,
    }


@app.get("/api/workspace/load")
def load_workspace(token: str = Query(..., description="Base64-encoded workspace token")):
    """Restore a workspace from a previously saved token.

    Returns the decoded snapshot so the frontend can restore state.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        snapshot = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace token")

    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=400, detail="Invalid workspace token")

    return {"snapshot": snapshot}


# ── Endpoints — Rules (Phase 4) ──────────────────────────────────────


@app.get("/api/rules/presets")
def get_rule_presets():
    """Return the list of available preset rules with default parameters."""
    return {"presets": _rule_engine.preset_rules()}


@app.post("/api/rules/evaluate")
def evaluate_rules(
    body: Dict[str, Any],
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
):
    """Evaluate rules against filtered contracts.

    Request body::

        {
            "rules": [
                {"id": "threshold_proximity", "params": {"threshold_eur": 50000}},
                ...
            ]
        }

    If ``rules`` is omitted or empty, all preset rules with defaults are used.
    Query-string filters restrict the contract set before evaluation.
    """
    filtered = store.filter(filters)
    rules_cfg = body.get("rules") or None
    result = _rule_engine.evaluate(filtered, rules=rules_cfg)

    # Build per-contract severity map
    contract_severities: Dict[str, float] = {}
    for c in filtered:
        if c.contract_id:
            sev = result.severity_for_contract(c.contract_id)
            if sev > 0:
                contract_severities[c.contract_id] = sev

    return {
        "total_flags": len(result.flags),
        "contract_severities": contract_severities,
        "flags": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "description": f.description,
                "contract_id": f.contract_id,
                "vendor": f.vendor,
                "institution": f.institution,
                "details": f.details,
            }
            for f in result.flags
        ],
    }


@app.post("/api/rules/custom")
def evaluate_custom_conditions(
    body: Dict[str, Any],
    store: DataStore = Depends(get_store),
    filters: FilterState = Depends(parse_filters),
):
    """Evaluate a custom condition group against filtered contracts.

    Request body::

        {
            "logic": "AND",
            "conditions": [
                {"field": "price_numeric_eur", "operator": "gt", "value": 100000},
                {"field": "award_type", "operator": "eq", "value": "direct_award"}
            ]
        }
    """
    try:
        group = ConditionGroup.from_dict(body)
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid condition: {exc}")

    filtered = store.filter(filters)
    matched = group.filter_contracts(filtered)

    return {
        "total_matched": len(matched),
        "total_evaluated": len(filtered),
        "contracts": [c.model_dump() for c in matched],
    }


# ── Endpoints — Chatbot (Phase 5) ───────────────────────────────────

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitise_message(text: str) -> str:
    """Strip control characters and enforce max length."""
    text = _CONTROL_CHAR_RE.sub("", text)
    max_len = settings.chat_max_message_length
    if len(text) > max_len:
        text = text[:max_len]
    return text.strip()


def _parse_filters_from_dict(d: Dict[str, Any]) -> FilterState:
    """Build a FilterState from a plain dict (e.g. from JSON body)."""
    return FilterState(**{
        k: v
        for k, v in d.items()
        if k in FilterState.model_fields and v is not None
    })


@app.get("/api/chat/status")
def chat_status():
    """Report chatbot provider, degraded status, and active features.

    Never exposes API key values.
    """
    provider, degraded = _runtime_chat_state()
    return {
        "provider": provider,
        "degraded": degraded,
        "features": settings.active_features,
    }


@app.post("/api/chat/save")
def save_chat(body: Dict[str, Any]):
    """Serialise a conversation for download.

    Request body::

        {
            "session_id": "abc123",
            "filters": { ... },      // optional
        }

    Returns the chat history with filter snapshot.
    """
    session_id = body.get("session_id", "")
    messages = _chat_history.get(session_id)
    filters_raw = body.get("filters", {})

    result: Dict[str, Any] = {
        "session_id": session_id,
        "messages": messages,
        "filters": filters_raw,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    if _usage_tracker.enabled:
        result["usage"] = _usage_tracker.get_session_usage(session_id)

    return result


@app.websocket("/api/chat")
async def chat_websocket(websocket: WebSocket):
    """Streaming chat over WebSocket.

    Client sends JSON frames::

        {
            "message": "What are the top vendors?",
            "filters": { "institutions": ["Mesto Bratislava"] },
            "session_id": "optional-uuid"
        }

    Server responds with envelope frames: start, token*, done | error.
    Client can send ``{"type": "cancel"}`` to abort mid-generation.
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    ErrorFrame(message="Invalid JSON").model_dump_json()
                )
                continue

            # Handle cancel frame
            if data.get("type") == "cancel":
                # Nothing actively generating in this simple approach
                continue

            message = data.get("message", "")
            session_id = data.get("session_id") or str(uuid.uuid4())
            filters_raw = data.get("filters") or {}

            # Sanitise input (security)
            message = _sanitise_message(message)
            if not message:
                await websocket.send_text(
                    ErrorFrame(message="Empty message").model_dump_json()
                )
                continue

            # Enforce max length
            if len(message) > settings.chat_max_message_length:
                await websocket.send_text(
                    ErrorFrame(message="Message too long").model_dump_json()
                )
                continue

            # Build filter state
            try:
                filters = _parse_filters_from_dict(filters_raw)
            except Exception:
                filters = FilterState()

            # Send start frame
            provider, degraded = _runtime_chat_state()
            start = StartFrame(
                session_id=session_id,
                degraded=degraded,
                provider=provider,
            )
            await websocket.send_text(start.model_dump_json())

            # Get the store
            store: DataStore = app.state.store

            # Check scope
            refusal = check_scope(message, filters, store)
            if refusal:
                done = DoneFrame(
                    content=refusal.reason,
                    scope_refusal=ScopeRefusalData(
                        reason=refusal.reason,
                        suggestions=refusal.suggestions,
                        hint_endpoint=refusal.hint_endpoint,
                    ),
                )
                _chat_history.append(session_id, "user", message)
                _chat_history.append(session_id, "assistant", refusal.reason)
                await websocket.send_text(done.model_dump_json())
                continue

            # Build scoped context
            context_str, provenance_docs = build_scoped_context(
                filters, store
            )

            # Build messages for LLM
            system_prompt = (
                "You are GovLens Assistant. Follow the RULES in the context "
                "strictly and answer only from the provided contracts. "
                "If data is missing, state it explicitly. Keep answers useful, "
                "analytical, and concise.\n\n"
                f"{context_str}"
            )

            history = _chat_history.get(session_id)
            llm_messages = [{"role": "system", "content": system_prompt}]
            for msg in history[-10:]:  # last 10 messages for context
                llm_messages.append(msg)
            llm_messages.append({"role": "user", "content": message})

            # Store user message
            _chat_history.append(session_id, "user", message)

            # Stream response
            collected_tokens: List[str] = []
            cancelled = False

            async def on_token(token: str):
                nonlocal cancelled
                if cancelled:
                    return
                collected_tokens.append(token)
                try:
                    await websocket.send_text(
                        TokenFrame(content=token).model_dump_json()
                    )
                except Exception:
                    cancelled = True

            try:
                usage_meta = await _llm_client.stream_chat(
                    llm_messages,
                    on_token=on_token,
                    session_id=session_id,
                )
            except Exception as exc:
                logger.error("LLM error: %s", exc)
                await websocket.send_text(
                    ErrorFrame(message=f"LLM error: {str(exc)}").model_dump_json()
                )
                continue

            full_response = "".join(collected_tokens)
            _chat_history.append(session_id, "assistant", full_response)

            # Record usage
            if _usage_tracker.enabled and usage_meta:
                token_usage = _llm_client.get_token_usage(usage_meta)
                _usage_tracker.record(
                    session_id,
                    prompt_tokens=token_usage.get("prompt_tokens", 0),
                    completion_tokens=token_usage.get("completion_tokens", 0),
                    total_cost_usd=token_usage.get("total_cost_usd", 0.0),
                )

            # Build provenance for done frame
            prov_items = []
            if settings.chat_provenance:
                prov_items = [
                    ProvenanceItem(
                        id=p.get("id", ""),
                        title=p.get("title", ""),
                        excerpt=p.get("source", ""),
                    )
                    for p in provenance_docs[:10]
                ]

            done = DoneFrame(
                content=full_response,
                cancelled=cancelled,
                provenance=prov_items,
                usage=_llm_client.get_token_usage(usage_meta) if usage_meta else None,
            )
            await websocket.send_text(done.model_dump_json())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await websocket.send_text(
                ErrorFrame(message="Internal server error").model_dump_json()
            )
        except Exception:
            pass


# ── Endpoints — Filter-state debug ──────────────────────────────────


@app.get("/api/filter-state")
def get_filter_state(
    filters: FilterState = Depends(parse_filters),
):
    """Debug: shows how filter state is parsed and re-encoded."""
    return {
        "parsed": filters.model_dump(),
        "encoded": encode_filter_state(filters),
    }

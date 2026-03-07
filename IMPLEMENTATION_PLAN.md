> **Note:** This project is developed and tested on Windows.  
> Before running any tests, always activate the `.venv` Python virtual environment at the repository root using PowerShell (pwsh):  
>  
>     .venv\Scripts\Activate.ps1  
>  
> Make sure you are using a PowerShell terminal (pwsh) for all commands and scripts.
> 

# GovLens — Implementation Plan

---

## 1 — CURRENT STATE ANALYSIS

### 1.1 What Is Already Implemented and Working

| Component | Status | Details |
|-----------|--------|---------|
| **Ingestion / Scraper** | ✅ Complete | `src/scraper.py` (454 LOC) — paginates `crz.gov.sk`, extracts listing rows, fetches detail pages, downloads PDFs, extracts text via `pdfplumber`, outputs NDJSON |
| **CLI entry point** | ✅ Complete | `scrape_crz.py` — argparse with `--start-page`, `--max-pages`, `--out`, `--delay`, `--user-agent`, `--pdf-dir`, `--log-level` |
| **Price parsing** | ✅ Complete | Slovak format `28 978,27 €` → `28978.27` with NBSP handling |
| **Date parsing** | ✅ Complete | Slovak month names → ISO, DD.MM.YYYY → ISO |
| **PDF download + text extraction** | ✅ Complete | `pdfplumber`, truncated at 50 000 chars |
| **Unit tests** | ✅ Complete | 341 backend (+ 1 skipped) + 135 frontend tests — `test_parser.py` (prices, dates), `test_integration.py` (scraper smoke), `test_models.py` (Phase 0, 24 tests), `test_migrate.py` (Phase 0, 15 tests), `test_engine.py` (Phase 1 + 6, 95 tests), `test_api.py` (Phase 2 + 6, 46 tests), `test_rules.py` (Phase 4, 37 tests), `test_chatbot.py` (Phase 5, 49 passed + 1 skipped), `test_workspace.py` (Phase 7, 5 tests), `test_export.py` (Phase 7, 5 tests), `test_url_state.py` (Phase 7, 5 tests), `test_e2e.py` (Phase 8, 15 tests), `test_performance.py` (Phase 8, 14 tests); 20 frontend test files (135 tests via vitest) including Phase 6 pages and Phase 7 WorkspaceToolbar. The skipped tests require `OPENAI_API_KEY` or a live Redis server — they are marked `@requires_openai_key` / `@requires_redis` and report SKIPPED when the service is absent. |
| **Documentation** | ✅ Complete | README, ARCHITECTURE, QUICKSTART, START_HERE, PROJECT_COMPLETION, DELIVERY_SUMMARY, INDEX — all updated for Phase 0 and Phase 1 |
| **Dependencies** | ✅ Pinned | `requirements.in` / `requirements.txt` — requests, beautifulsoup4, lxml, pdfplumber, pytest, pydantic>=2.0, python-dotenv, fastapi, uvicorn[standard], httpx, reportlab |
| **Output format** | ✅ NDJSON | One JSON object per line; fields: listing, detail, PDF, `scraped_at`, `category`, `pdf_text_summary`, `award_type` |
| **Pydantic data models** | ✅ Complete (Phase 0) | `src/models.py` — `Contract`, `Institution`, `Vendor`, `FilterState`, `AggregationResult` |
| **Enrichment fields** | ✅ Complete (Phase 0) | `category` (`"not_decided"`), `pdf_text_summary` (`"not_summarized"`), `award_type` (`"unknown"`) added to every scraper record |
| **Migration script** | ✅ Complete (Phase 0) | `scripts/migrate_ndjson.py` — converts NDJSON → JSON array, backfills missing fields |
| **Sample data** | ✅ Complete (Phase 0) | `data/sample_contracts.json` — 30+ realistic seed contract records |
| **Environment config** | ✅ Complete (Phase 0) | `.env.example` — LLM provider, API key, server host/port, data paths, scraper delay |
| **Query engine** | ✅ Complete (Phase 1) | `src/engine.py` — `DataStore` class: filter, group_by, aggregate, search, compare, trend, rank |
| **Backend API** | ✅ Complete (Phase 2+6+7) | `src/api.py` — 20 FastAPI endpoints: contracts, aggregations, treemap, benchmark (with peers + multi-metric compare), trends (with overlays + multi-metric), rankings (with filters + new metrics), institutions, vendors, CSV export, PDF export (ReportLab), workspace save/load |
| **Rule Engine** | ✅ Complete (Phase 4) | `src/rules/engine.py` — 6 preset rules (threshold proximity, vendor concentration, fragmentation, overnight turnaround, new-vendor-large-contract, round-number clustering), severity scoring; `src/rules/builder.py` — no-code condition builder with AND/OR logic |
| **App config** | ✅ Complete (Phase 2+5) | `src/config.py` — Settings from env vars (host, port, data_path, LLM, scraper, chatbot feature flags) |
| **Chatbot backend** | ✅ Complete (Phase 5) | `src/chatbot/` — protocol.py (WebSocket envelope models), llm.py (MockLLMClient + OpenAIClient), context.py (scoped context builder + LRU cache), scope.py (scope enforcement + refusal suggestions), history.py (InMemoryHistory + RedisHistory fallback), usage.py (token/cost accounting) |
| **Chatbot API** | ✅ Complete (Phase 5) | `src/api.py` v2.0.0 — `WS /api/chat` (streaming), `GET /api/chat/status`, `POST /api/chat/save`; message sanitisation, scope enforcement, provenance |
| **ChatBar UI** | ✅ Complete (Phase 5) | `frontend/src/components/ChatBar.tsx` — embedded chatbot bar with streaming, scope refusal suggestions, provenance panel, degraded-mode banner, keyboard navigation, ARIA roles |
| **WorkspaceToolbar UI** | ✅ Complete (Phase 7) | `frontend/src/components/WorkspaceToolbar.tsx` — Share (clipboard), Save Workspace (JSON download), Export CSV, Export PDF buttons; integrated into Dashboard, BenchmarkView, TimeView, GlobalView |
| **URL-state encoding** | ✅ Complete (Phase 7) | `frontend/src/url-state.ts` — extended with `mode` field; full round-trip filter+sort+groupBy+page+mode encoding/decoding |
| **PDF export** | ✅ Complete (Phase 7) | `src/api.py` `GET /api/export/pdf` — ReportLab-generated PDF with title, summary stats, timestamp, and contract table (up to 500 rows) |

### 1.2 What Is Missing / Incomplete / Needs Refactoring

| Gap | Severity | Notes |
|-----|----------|-------|
| ~~**`category` field**~~ | ~~Required~~ | ✅ **Resolved in Phase 0** — field present on every record with default `"not_decided"` |
| ~~**`pdf_text_summary` field**~~ | ~~Required~~ | ✅ **Resolved in Phase 0** — field present on every record with default `"not_summarized"` |
| ~~**Consolidated JSON storage**~~ | ~~Required~~ | ✅ **Resolved in Phase 0** — `scripts/migrate_ndjson.py` converts NDJSON → JSON array |
| ~~**No `data/` directory with sample data**~~ | ~~Gap~~ | ✅ **Resolved in Phase 0** — `data/sample_contracts.json` with 30+ records |
| ~~**No data model / schema definition**~~ | ~~Gap~~ | ✅ **Resolved in Phase 0** — `src/models.py` with Pydantic v2 models |
| ~~**Award type field**~~ | ~~Gap~~ | ✅ **Resolved in Phase 0** — `award_type` field added, defaults to `"unknown"` |
| ~~**No web application**~~ | ~~Major gap~~ | ✅ **Resolved** — Frontend (Phase 3), Rule Engine (Phase 4), Chatbot (Phase 5), Investigation Modes (Phase 6), and State/Sharing/Export (Phase 7) all complete. |
| **No in-memory query engine** | ✅ Resolved (Phase 1) | `src/engine.py` — DataStore with filter, group_by, aggregate, search, compare, trend, rank |
| ~~**No LLM integration**~~ | ~~Gap~~ | ✅ **Resolved in Phase 5** — `src/chatbot/` package with `MockLLMClient` (default, CI-safe) and `OpenAIClient` (optional). WebSocket streaming, provenance, cost accounting, scope enforcement all implemented. |
| **No URL-state management** | Gap | No routing, no deep-linking, no bookmarkable views. |
| **No export (CSV/PDF)** | ✅ Complete (Phase 2 + 7) | CSV export via `GET /api/export/csv`; PDF export via `GET /api/export/pdf` using ReportLab |
| **`data/pdfs/` directory** | Minor | Referenced in `.gitignore` and docs but may not exist on fresh clone (auto-created at runtime). |

### 1.3 Conflicts & Incompatibilities with the Design Document

| Item | Conflict | Resolution |
|------|----------|------------|
| ~~**Storage format**~~ | ~~Scraper writes NDJSON; design doc assumes `contracts.json` (array)~~ | ✅ **Resolved in Phase 0** — `scripts/migrate_ndjson.py` handles conversion |
| ~~**Missing fields in scraper output**~~ | ~~`category`, `pdf_text_summary`, `award_type` not produced by scraper~~ | ✅ **Resolved in Phase 0** — all three fields added to scraper output and migration script |
| **No web stack chosen** | Design doc describes a rich SPA with treemaps, streaming, URL-state; repo only has Python CLI | Must choose a tech stack (recommended: Python backend — FastAPI; frontend — React/Next.js or plain JS + D3) |
| **Scraper-only architecture vs. full application** | Current repo is a CLI tool; GovLens is a multi-mode investigative application | Repo must be restructured with clear `backend/`, `frontend/`, `scripts/` boundaries |
| **No `award_type` source** | CRZ site does not expose award type in the scraped HTML | Heuristic inference or manual tagging deferred to later phase; `"unknown"` default in place |

---

## 2 — PHASED IMPLEMENTATION PLAN

### Phase 0 — Foundation: Schema, Data Model, and Project Restructure

**Goal:** Establish the data model, add required fields, restructure the repo for a full-stack application, and produce loadable seed data.

**Status: ✅ COMPLETE**

**Dependencies:** None (starting point).

#### Tasks

| # | Task | Status |
|---|------|--------|
| 0.1 | Define formal data model (Pydantic `Contract` model with all existing + new fields) | ✅ DONE |
| 0.2 | Add `category` (default `"not_decided"`) and `pdf_text_summary` (default `"not_summarized"`) fields to scraper output in `src/scraper.py` | ✅ DONE |
| 0.3 | Add `award_type` field (default `"unknown"`) to scraper output | ✅ DONE |
| 0.4 | Create migration script `scripts/migrate_ndjson.py` — reads existing NDJSON, adds missing fields, writes `data/contracts.json` (array format) | ✅ DONE |
| 0.5 | Create `src/models.py` — Pydantic models: `Contract`, `Vendor`, `Institution`, `FilterState`, `AggregationResult` | ✅ DONE |
| 0.6 | Restructure repo directories: `backend/`, `frontend/`, `scripts/`, `data/`, `tests/` (preserve existing code under `backend/` or `scripts/scraper/`) | ⏭ DEFERRED — repo restructure deferred to Phase 2 to avoid breaking existing tests; `scripts/` and `data/` directories added |
| 0.7 | Update `requirements.in` / `requirements.txt` with new backend deps (fastapi, uvicorn, pydantic, etc.) | ✅ DONE — `pydantic>=2.0`, `python-dotenv` added; fastapi/uvicorn deferred to Phase 2 |
| 0.8 | Create `data/sample_contracts.json` with 20–50 seed records for development/testing | ✅ DONE — 30+ records |
| 0.9 | Add `.env.example` for config (LLM API key placeholder, port, data path) | ✅ DONE |

#### Unit Tests for Phase 0 — ✅ All 39 tests passing

| Test | Coverage | Result |
|------|----------|--------|
| `test_models.py::TestContractModelDefaults` (4 tests) | Contract defaults: `category`, `pdf_text_summary`, `award_type`, optional fields | ✅ PASS |
| `test_models.py::TestContractModelValidation` (3 tests) | Invalid price raises ValidationError; extra fields allowed | ✅ PASS |
| `test_models.py::TestContractSerialization` (2 tests) | `model_dump` and JSON round-trip | ✅ PASS |
| `test_models.py::TestContractFromScraperDict` (2 tests) | Create Contract from scraper NDJSON dict | ✅ PASS |
| `test_models.py::TestFilterStateDefaults` (3 tests) | Empty FilterState; populated values; serialization | ✅ PASS |
| `test_models.py::TestAggregationResult` (2 tests) | Defaults and populated values | ✅ PASS |
| `test_models.py::TestInstitutionModel` (2 tests) | Defaults and data | ✅ PASS |
| `test_models.py::TestVendorModel` (2 tests) | Defaults and data | ✅ PASS |
| `test_models.py::TestSampleContractsFile` (4 tests) | File exists; loads as JSON array; validates as Contracts; required fields present | ✅ PASS |
| `test_migrate.py::TestMigrateAddsFields` (3 tests) | Backfills category, pdf_text_summary, award_type | ✅ PASS |
| `test_migrate.py::TestMigratePreservesData` (3 tests) | Existing fields unchanged after migration | ✅ PASS |
| `test_migrate.py::TestMigrateDoesNotOverwrite` (3 tests) | Pre-existing enrichment values kept | ✅ PASS |
| `test_migrate.py::TestMigrateOutputFormat` (3 tests) | Output is valid JSON array; correct record count; empty input | ✅ PASS |
| `test_migrate.py::TestMigrateEdgeCases` (3 tests) | Skips invalid JSON lines; skips blank lines; creates output directory | ✅ PASS |

#### Unlocks

- All subsequent phases depend on the data model and `contracts.json` being available.
- Phase 1 (query engine) requires the schema to be finalized.

---

### Phase 1 — In-Memory Query & Aggregation Engine ✅ DONE

**Goal:** Build a Python engine that loads `contracts.json` into RAM and supports fast filtering, group-by, and aggregation operations needed by all UI modes.

**Dependencies:** Phase 0 (data model + `contracts.json`).

**Implementation:** `src/engine.py` — `DataStore` class (589 LOC), `SORTABLE_FIELDS` constant, `_sort_key` helper

#### Tasks

| # | Task | Status |
|---|------|--------|
| 1.1 | Create `src/engine.py` — `DataStore` class: loads JSON at init, holds list of `Contract` objects | ✅ DONE |
| 1.2 | Implement shared global filters: institution(s), date range, category, vendor, value range (min/max), award type, text search (title/summary) | ✅ DONE |
| 1.3 | Implement `group_by(field)` returning `Dict[str, List[Contract]]` — fields: category, supplier, buyer, month, award_type | ✅ DONE |
| 1.4 | Implement aggregations: `total_spend`, `contract_count`, `avg_value`, `max_value`, `top_n_vendors`, `direct_award_rate` | ✅ DONE |
| 1.5 | Implement `search(query)` — full-text search over `contract_title` + `pdf_text_summary` | ✅ DONE |
| 1.6 | Implement Benchmark helpers: `institutions()`, `vendors()`, `compare(institutions, metric)` | ✅ DONE |
| 1.7 | Implement Time helpers: `trend(granularity='month'|'quarter'|'year', metric)` | ✅ DONE |
| 1.8 | Implement Global Ranking: `rank_institutions(metric)`, `rank_vendors(metric)` | ✅ DONE |
| 1.9 | Add caching / index structures for frequently-filtered fields (institution, category, date) | ✅ DONE |
| 1.10 | Implement `sort_contracts(contracts, sort_spec)` — multi-column sort; `sort_spec` is `List[Tuple[str, str]]` (field, direction); `SORTABLE_FIELDS` whitelist; `None` values always last regardless of direction | ✅ DONE |

#### Unit Tests for Phase 1

| Test | Result |
|------|--------|
| `test_engine.py::TestLoad` (5 tests) — load from JSON, load from list, empty store, object types | ✅ PASS |
| `test_engine.py::TestFilter` (15 tests) — institution, date range, value range, category, vendor, award_type, text search, combined, no match | ✅ PASS |
| `test_engine.py::TestSearch` (4 tests) — title, summary, case-insensitive, no match | ✅ PASS |
| `test_engine.py::TestGroupBy` (7 tests) — category, supplier, buyer, month, award_type, filtered subset, sample data | ✅ PASS |
| `test_engine.py::TestAggregation` (9 tests) — total_spend, count, avg, max, empty list, grouped, top-N, direct_award_rate | ✅ PASS |
| `test_engine.py::TestInstitutionsVendors` (3 tests) — institutions list, sorted by spend, vendors list | ✅ PASS |
| `test_engine.py::TestCompare` (3 tests) — total_spend, contract_count, direct_award_rate | ✅ PASS |
| `test_engine.py::TestTrends` (6 tests) — monthly, values, quarterly, yearly, count metric, filtered | ✅ PASS |
| `test_engine.py::TestRankings` (5 tests) — institutions by spend/count/direct_award_rate, vendors by spend/count | ✅ PASS |
| `test_engine.py::TestSampleData` (7 tests) — smoke tests on real sample data | ✅ PASS |
| `test_engine.py::TestEdgeCases` (5 tests) — None prices, None dates, no prices, reload | ✅ PASS |
| `test_engine.py::TestSort` (11 tests) — see detail below | ✅ PASS |
| **Total: 80 tests** | **✅ ALL PASS** |

##### TestSort detail

| Test | What it verifies |
|---|---|
| `test_sort_single_field_ascending` | `price_numeric_eur` sorted low → high |
| `test_sort_single_field_descending` | `price_numeric_eur` sorted high → low |
| `test_sort_multi_column_tie_breaking` | Equal-price contracts ordered by secondary field (`published_date`) |
| `test_sort_none_values_last_ascending` | Contracts with `None` price appear after all non-`None` values, even in ascending order |
| `test_sort_none_values_last_descending` | Same `None`-last guarantee when sorting descending |
| `test_sort_string_field` | `contract_title` sorted alphabetically (case-insensitive) |
| `test_sort_iso_date_string_ordering` | ISO date strings (`"2024-01-15"`) sort correctly as plain strings without datetime parsing |
| `test_sort_unknown_field_skipped` | A field not in `SORTABLE_FIELDS` whitelist is silently ignored; no exception raised |
| `test_sort_empty_list` | Returns empty list without error |
| `test_sort_single_item` | Returns a one-element list unchanged |
| `test_sort_preserves_filter_result` | Sort applied on the output of `filter()`; does not re-read the full store |

Full suite: 173 tests (80 Phase 1 + 33 Phase 2 + 60 Phase 0 + prior) — all passing.

#### Unlocks

- Phase 2 (API) can expose these operations as HTTP endpoints. ✅ DONE
- Phase 4 (Rule Builder) reuses filter + aggregation primitives.

---

### Phase 2 — Backend API (FastAPI) ✅ DONE

**Goal:** Expose the query engine over HTTP with REST endpoints and WebSocket for chatbot streaming. Implement URL-encodable filter state.

**Dependencies:** Phase 1 (query engine).

**Implementation:** `src/api.py` (580+ LOC), `src/config.py` (39 LOC)

#### Tasks

| # | Task | Status |
|---|------|--------|
| 2.1 | Create `src/api.py` — FastAPI application, load `DataStore` at startup | ✅ DONE (path adjusted from `backend/app.py` since repo restructure deferred) |
| 2.2 | `GET /api/contracts` — paginated, filterable list (accepts all shared global filter params as query params) | ✅ DONE |
| 2.3 | `GET /api/contracts/{id}` — single contract detail | ✅ DONE |
| 2.4 | `GET /api/aggregations` — accepts `group_by` + filters, returns aggregation result | ✅ DONE |
| 2.5 | `GET /api/treemap` — returns hierarchical data for treemap visualization (grouped by category → vendor or similar) | ✅ DONE |
| 2.6 | `GET /api/benchmark` — accepts institution + peer params, returns comparison data | ✅ DONE |
| 2.7 | `GET /api/trends` — accepts filters + granularity, returns time-series data | ✅ DONE |
| 2.8 | `GET /api/rankings` — accepts metric, returns ranked list of institutions or vendors | ✅ DONE |
| 2.9 | `GET /api/institutions` — list of unique institutions (buyers) with contract counts | ✅ DONE |
| 2.10 | `GET /api/institutions/{identifier}` — institution profile: stats, trends, top vendors (supports name or ICO lookup) | ✅ DONE |
| 2.11 | `GET /api/vendors` — list of unique vendors (suppliers) with contract counts | ✅ DONE |
| 2.12 | `GET /api/vendors/{identifier}` — vendor profile: stats, institutions served, contracts (supports name or ICO lookup) | ✅ DONE |
| 2.13 | `GET /api/export/csv` — accepts filters, returns CSV download | ✅ DONE |
| 2.14 | `GET /api/export/pdf` — accepts filters, returns formatted PDF report | ✅ DONE (Phase 7 — implemented with ReportLab) |
| 2.15 | Implement filter-state serialization: filters ↔ URL query string (encode/decode) | ✅ DONE (`parse_filters` + `encode_filter_state`) |
| 2.16 | Add CORS middleware for frontend dev server | ✅ DONE |
| 2.17 | Add `src/config.py` — config from env vars (port, data path, LLM key) | ✅ DONE (path adjusted from `backend/config.py`) |
| 2.18 | Extend `GET /api/contracts` with `sort` query param — format `field:direction,field:direction` (e.g. `price_numeric_eur:desc,published_date:asc`); add `parse_sort()` dependency function; sort is applied after filtering and before pagination slice | ✅ DONE |
| 2.19 | Extend `GET /api/export/csv` with `sort` query param — exported rows follow the same order the user sees on screen | ✅ DONE |
| 2.20 | Extend `encode_filter_state()` with optional `sort_spec` parameter — round-trips sort through URL, laying groundwork for Phase 7 shareable links | ✅ DONE |

#### Unit Tests for Phase 2 — ✅ All 33 tests passing

| Test | Coverage | Result |
|------|----------|--------|
| `test_api.py::TestContracts` (7 tests) | List (200), filter by institution, pagination, date range, text search, detail, not found (404) | ✅ PASS |
| `test_api.py::TestAggregations` (2 tests) | Group by category, with filter | ✅ PASS |
| `test_api.py::TestTreemap` (2 tests) | Data structure, sub-grouping | ✅ PASS |
| `test_api.py::TestBenchmark` (1 test) | Peer comparison | ✅ PASS |
| `test_api.py::TestTrends` (2 tests) | Time-series, with filter | ✅ PASS |
| `test_api.py::TestRankings` (2 tests) | Institutions, vendors | ✅ PASS |
| `test_api.py::TestInstitutions` (4 tests) | List, profile by name, by ICO, not found | ✅ PASS |
| `test_api.py::TestVendors` (4 tests) | List, profile, by ICO, not found | ✅ PASS |
| `test_api.py::TestExport` (3 tests) | CSV, CSV with filter, PDF 501 stub | ✅ PASS |
| `test_api.py::TestFilterState` (2 tests) | Round-trip encoding, empty state | ✅ PASS |
| `test_api.py::TestSampleDataSmoke` (4 tests) | Contracts, institutions, rankings, CSV with real sample data | ✅ PASS |
| `test_api.py::TestContractsSort` (9 tests) | Multi-column sort on `GET /api/contracts` and CSV export — see detail below | ✅ PASS |
| **Total: 42 tests** | | **✅ ALL PASS** |

##### TestContractsSort detail

| Test | What it verifies |
|---|---|
| `test_sort_by_price_descending` | First contract in response has the highest `price_numeric_eur` |
| `test_sort_by_price_ascending` | First contract has the lowest `price_numeric_eur` |
| `test_sort_multi_column_applied` | Two-column spec (`price_numeric_eur:desc,published_date:asc`) produces correct ordering when prices tie |
| `test_sort_combined_with_filter` | Filter reduces the set, sort is applied to that filtered subset (not the full store) |
| `test_sort_pagination_stability` | Page 2 continues the same globally-sorted order — slicing happens after sorting |
| `test_csv_export_respects_sort` | CSV rows arrive in the same order as the equivalent API response |
| `test_sort_invalid_field_ignored` | Unrecognised field in spec does not cause a 4xx/5xx; valid fields in the same spec are still applied |
| `test_sort_missing_param_deterministic` | Omitting `sort` returns a stable order on two successive identical requests |
| `test_encode_filter_state_includes_sort` | `encode_filter_state(fs, sort_spec=...)` round-trips sort spec back through URL params |

Full suite: 161 tests (42 Phase 2 + 80 Phase 1 + 39 Phase 0) — all passing.

#### Unlocks

- Frontend (Phase 3) can call these endpoints.
- Chatbot (Phase 5) uses the same filter endpoints for context.

---

### Phase 3 — Frontend: Institution Lens UI

**Goal:** Build the default landing view with institution selector, dynamic aggregation panel, treemap visualization, expandable accordion rows, and contract detail — all with URL-state-driven navigation.

**Dependencies:** Phase 2 (API endpoints).

#### Tasks

| # | Task | Status |
|---|------|--------|
| 3.1 | Initialize frontend project (React + TypeScript + Vite in `frontend/`) | ✅ DONE |
| 3.2 | Install dependencies: D3.js (treemap), react-router (URL state), tailwindcss or similar | ✅ DONE |
| 3.3 | Create global layout: top context strip (institution selector dropdown, date-range picker, breadcrumb trail) | ✅ DONE |
| 3.4 | Create `FilterBar` component: Institution(s), Date range, Category, Vendor, Value range, Award type, Text search | ✅ DONE |
| 3.5 | Implement URL-state manager: read/write all filter + view state to URL query params; `popstate` restores scroll & accordion state | ✅ DONE |
| 3.6 | Create `GroupByControl` component: toggle between Category / Vendor / Month / Award Type | ✅ DONE |
| 3.7 | Create `TreemapChart` component: D3 treemap showing grouped spend data; responsive; click drills down | ✅ DONE |
| 3.8 | Create `BarChart` fallback component: horizontal bar chart when treemap is unsuitable | ✅ DONE |
| 3.9 | Create `CategoryAccordion` component: expandable rows showing group name + aggregated total; click expands to contracts table | ✅ DONE |
| 3.10 | Create `ContractsTable` component: multi-column sortable table inside accordion with contract title, vendor, value, date; rows are clickable → detail. Click a column header to set primary sort; Shift+click to append a secondary/tertiary sort key. Each sorted header shows a direction arrow and a priority badge (①②③). Sort state is encoded in the URL (`&sort=field:dir,field:dir`) so it survives back-navigation and page refresh. Changing sort resets pagination to page 1. | ✅ DONE |
| 3.11 | Create `ContractDetail` page/panel: full contract info, PDF link, `pdf_text_summary`, category badge, rule flags (placeholder); URL-state-driven (`/contract/:id`) | ✅ DONE |
| 3.12 | Implement precise back-navigation: returning from detail restores accordion state + scroll position | ✅ DONE |
| 3.13 | Create `InstitutionProfile` page: full footprint, trend chart, vendor breakdown, related contracts | ✅ DONE |
| 3.14 | Create `VendorProfile` page: institutions served, contract list, trend | ✅ DONE |
| 3.15 | Ensure zero dead-ends: every contract/vendor/institution name is a clickable link | ✅ DONE |
| 3.16 | Implement responsive design (desktop-first with usable mobile fallback) | ✅ DONE |

#### Unit Tests for Phase 3

- `FilterBar.test.tsx` — renders all filter controls; changing a filter updates URL params
- `TreemapChart.test.tsx` — renders SVG; handles empty data gracefully
- `CategoryAccordion.test.tsx` — expand/collapse toggles; shows correct contract count
- `ContractsTable.test.tsx` — renders rows; clicking row navigates to detail
- `ContractDetail.test.tsx` — displays all fields; back button restores prior state
- `url-state.test.ts` — encode → decode round-trip for all filter fields
- `InstitutionProfile.test.tsx` — renders stats and chart; handles missing data
- `VendorProfile.test.tsx` — renders vendor details and contract list

##### ContractsTable — multi-column sort tests

| Test | What it verifies |
|---|---|
| `test_clicking_header_calls_api_with_sort` | Click on "Value" column header → API called with `sort=price_numeric_eur:asc` |
| `test_second_click_on_same_header_reverses_direction` | Second click on same header → `sort=price_numeric_eur:desc` |
| `test_shift_click_appends_secondary_sort` | Shift+click on "Date" after sorting by value → `sort=price_numeric_eur:desc,published_date:asc` |
| `test_sort_indicator_shows_arrow_direction` | Sorted column header renders an up/down arrow icon matching the active direction |
| `test_sort_indicator_shows_priority_badge` | In multi-column mode the primary header shows ①, secondary shows ② |
| `test_sort_state_encoded_in_url` | After user interaction the URL query string contains `sort=…` |
| `test_sort_state_restored_from_url_on_load` | Mounting the component with `?sort=price_numeric_eur:desc` in the URL pre-selects the correct column indicator |
| `test_sort_change_resets_to_page_one` | Changing the active sort resets the `page` URL param to `1` |

#### Unlocks

- Phase 6 (Investigation Modes) builds on the same filter/visualization infrastructure.
- Phase 7 (Export/Share) adds buttons to these views.

---

### Phase 4 — Rule Builder (Pattern Engine)

**Goal:** Build the journalist-driven pattern detection engine: preset rules with customizable parameters, a no-code condition builder, and per-contract/per-vendor badge rendering.

**Status: ✅ COMPLETE**

**Dependencies:** Phase 1 (query engine for computations), Phase 2 (API to expose rules).

#### Tasks

| # | Task | Status |
|---|------|--------|
| 4.1 | Create `src/rules/engine.py` — `RuleEngine` class: accepts filter context + rules, evaluates against contracts (~350 LOC) | ✅ DONE |
| 4.2 | Implement preset rule: **Threshold Proximity** — flag contracts within X% of a legal threshold (e.g., direct-award limit) | ✅ DONE |
| 4.3 | Implement preset rule: **Vendor Concentration** — flag when top-N vendors hold > X% of institution spend | ✅ DONE |
| 4.4 | Implement preset rule: **Fragmentation** — flag when many small contracts to same vendor suggest split procurement | ✅ DONE |
| 4.5 | Implement preset rule: **Overnight Turnaround** — flag contracts signed and published within < N hours | ✅ DONE |
| 4.6 | Implement preset rule: **New-Vendor-Large-Contract** — flag vendors appearing for the first time with a contract above threshold | ✅ DONE |
| 4.7 | Implement preset rule: **Round-Number Clustering** — flag statistical anomaly of round-number contract values | ✅ DONE |
| 4.8 | Implement severity scoring: each rule contributes to a simple numeric severity score per contract/vendor (capped at 1.0) | ✅ DONE |
| 4.9 | Create `src/rules/builder.py` — condition builder: field/operator/value, AND/OR chaining, serializable to JSON (~170 LOC) | ✅ DONE |
| 4.10 | `POST /api/rules/evaluate` — accepts rule config + filters, returns flagged contracts with badges and scores | ✅ DONE |
| 4.11 | `GET /api/rules/presets` — returns list of preset rules with default params | ✅ DONE |
| 4.12 | Frontend: `RulePanel` component — list of preset rules with sensitivity sliders and numeric param editors | ✅ DONE |
| 4.13 | Frontend: `ConditionBuilder` component — no-code field/operator/value rows, add/remove, AND/OR toggle | ✅ DONE |
| 4.14 | Frontend: `RuleBadge` component — small badge on contract/vendor rows explaining which rules fired | ✅ DONE |
| 4.15 | Frontend: `SeverityIndicator` component — visual severity score (color-coded) on contract rows | ✅ DONE |

#### Unit Tests for Phase 4 — ✅ All 51 tests passing (37 backend + 14 frontend)

| Test | Coverage | Result |
|------|----------|--------|
| `test_rules.py::TestThresholdProximity` (4 tests) | Flags at 95%, ignores at 50%, boundary values, custom params | ✅ PASS |
| `test_rules.py::TestVendorConcentration` (3 tests) | Top vendor > 60% flagged, below threshold not flagged, custom top_n | ✅ PASS |
| `test_rules.py::TestFragmentation` (3 tests) | Many small contracts flagged, few contracts not flagged, threshold tuning | ✅ PASS |
| `test_rules.py::TestOvernightTurnaround` (3 tests) | < 24h flagged, > 24h not flagged, missing dates handled | ✅ PASS |
| `test_rules.py::TestNewVendorLargeContract` (3 tests) | First-time vendor + high value flagged, repeat vendor not flagged, low value not flagged | ✅ PASS |
| `test_rules.py::TestRoundNumberClustering` (3 tests) | Round numbers flagged, non-round distribution not flagged, edge cases | ✅ PASS |
| `test_rules.py::TestSeverityScoring` (2 tests) | Multiple rules accumulate; severity capped at 1.0 | ✅ PASS |
| `test_rules.py::TestConditionBuilder` (6 tests) | AND chain, OR chain, JSON round-trip, invalid field rejected, operator validation, empty group | ✅ PASS |
| `test_rules.py::TestRuleEngine` (4 tests) | Evaluate with presets, preset listing, empty data, selective rules | ✅ PASS |
| `test_rules.py::TestRulesAPI` (6 tests) | GET /api/rules/presets, POST /api/rules/evaluate, POST /api/rules/custom, error handling | ✅ PASS |
| `RulePanel.test.tsx` (6 tests) | Renders presets, slider changes params, evaluate calls API, displays flags, loading state, error state | ✅ PASS |
| `ConditionBuilder.test.tsx` (8 tests) | Add/remove rows, AND/OR toggle, field/operator/value selection, evaluate calls API, serialization, empty state, result display | ✅ PASS |

#### Unlocks

- Badges display on contract rows in Phase 3 views.
- Chatbot (Phase 5) can mention rule flags in responses.

---

### Phase 5 — Contextual Chatbot

**Goal:** Build an embedded chatbot bar scoped to the active filter context, with streaming LLM responses, scope enforcement, and graceful degradation when no LLM API key is configured. All LLM-dependent features are **optional** and gated behind feature flags; the system defaults to `MockLLMClient` so the full application remains functional without any external API credentials.

**Status: ✅ COMPLETE**

**Dependencies:** Phase 1 (query engine for context), Phase 2 (API/WebSocket infrastructure), Phase 3 (UI shell for embedding).

#### Feature Flags & Default Behaviour

All LLM-powered and infrastructure-heavy sub-features are controlled by environment variables. The table below defines the defaults which are chosen for **stability over richness**.

| Environment Variable | Default | Effect when not set |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `MockLLMClient` used; no external calls |
| `OPENAI_API_KEY` | _(empty)_ | LLM features silently disabled; banner shown |
| `CHAT_STREAMING` | `false` | Non-streaming (single-response) mode active |
| `CHAT_HISTORY_BACKEND` | `memory` | In-process dict; resets on server restart |
| `CHAT_CACHE_BACKEND` | `memory` | In-process cache for context chunks |
| `CHAT_PROVENANCE` | `false` | Source citations omitted from responses |
| `CHAT_COST_TRACKING` | `false` | Token/cost accounting skipped |
| `CHAT_OBSERVABILITY` | `false` | OpenTelemetry traces not emitted |
| `CHAT_FEATURE_FLAGS` | `''` | Comma-separated optional features: `streaming`, `provenance`, `cost_tracking`, `observability`, `redis_history`, `postgres_history`, `langchain` |

Optional heavyweight backends (`redis`, `postgres`) are only activated when the corresponding flag is present in `CHAT_FEATURE_FLAGS` **and** the required package is installed. Missing packages trigger a clear `ImportError` message and fall back to the in-memory default.

#### Module Structure

All chatbot Python modules live under `src/chatbot/` (consistent with the existing `src/` layout — repo restructure to `backend/` is still deferred per Phase 0 task 0.6).

#### Tasks

| # | Task | Optional flag | Status |
|---|------|---|--------|
| 5.1 | Create `src/chatbot/context.py` — `build_scoped_context(filters, store, top_n=20)` returns a context string **and** a list of provenance documents (`id`, `source`, `date` metadata per record). Strategy: `n ≤ 100` → full filtered dataset; `n > 100` → top-N by value + category aggregates + rule-flags summary + compressed remainder chunks (hierarchical summaries). Reuses `DataStore.filter()` and `RuleEngine` from existing `src/engine.py` and `src/rules/engine.py`. | — (always built) | ✅ DONE |
| 5.2 | Create `src/chatbot/llm.py` — `LLMClient` abstract base class with methods: `stream_chat(messages, on_token, session_id, stop_tokens=None)`, `complete(messages) -> str`, `get_token_usage(response_meta) -> dict`. Implement `MockLLMClient` (deterministic, no API calls, suitable for CI). Implement `OpenAIClient` using `openai` Python SDK with streaming (`stream=True`); guarded by `CHAT_FEATURE_FLAGS=...openai...` **and** presence of `OPENAI_API_KEY`. Implement optional `LangChainOpenAIClient` with LangChain callbacks (`on_llm_new_token`) — activated only when `langchain` is in `CHAT_FEATURE_FLAGS` and the `langchain-openai` package is installed. | `OpenAIClient`: `OPENAI_API_KEY` present; `LangChainOpenAIClient`: `langchain` flag | ✅ DONE |
| 5.3 | Create `src/chatbot/scope.py` — scope enforcement: check requested entities (institution names, vendor names, date ranges) against the active `FilterState`; return a **structured `ScopeRefusal`** dataclass with `reason`, `suggestions` (list of concrete filter-change proposals), and `hint_endpoint` (e.g. `/api/institutions?...`). Log all refused queries to a structured JSON log for policy tuning. | — (always built) | ✅ DONE |
| 5.4 | Implement `WS /api/chat` WebSocket endpoint in `src/api.py` — accepts `{ "message": str, "filters": {...}, "session_id": str }` JSON frame and streams responses using a defined **message envelope**: `start`, `token`, `partial_usage`, `done`, `error`, `cancel`. Support `client_cancel` frame from client to abort generation. When `LLM_PROVIDER=mock` or key is absent, the endpoint returns a single `done` frame with a descriptive degraded-mode message rather than refusing the connection. | streaming: `CHAT_STREAMING=true` | ✅ DONE |
| 5.5 | Implement context chunk cache in `src/chatbot/context.py` — cache compressed chunk summaries keyed by `sha256(filter_hash)` to avoid recomputation. Default backend: in-process `dict` with LRU eviction (max 128 entries). Optional Redis backend: activated when `redis_history` in `CHAT_FEATURE_FLAGS` and `redis` package is installed; falls back to in-memory with a warning log if Redis is unreachable. | Redis: `redis_history` flag | ✅ DONE |
| 5.6 | Implement per-session chat history in `src/chatbot/history.py` — `ChatHistory` abstract base class with `append(session_id, role, content)`, `get(session_id) -> list`, `clear(session_id)`. Implement `InMemoryHistory` (default). Implement optional `RedisHistory` (activated when `redis_history` in `CHAT_FEATURE_FLAGS`). Implement optional `PostgresHistory` (activated when `postgres_history` in `CHAT_FEATURE_FLAGS`). Missing optional packages produce a WARNING log and fall back to in-memory. | Redis: `redis_history`; Postgres: `postgres_history` | ✅ DONE |
| 5.7 | Create `POST /api/chat/save` — serialise the conversation (messages, active `FilterState`, snapshot timestamp, optional token usage summary) to a JSON dict and return it for download. Does **not** require Redis or Postgres; always available. | — (always built) | ✅ DONE |
| 5.8 | Frontend: `ChatBar` component — fixed bottom bar with input field, message list, and streaming token display. Shows a **degraded-mode banner** ("LLM unavailable — no API key configured") when the backend reports `degraded: true` in the `start` frame. In degraded mode the component is fully rendered but input is disabled with a tooltip explaining the configuration step. Implements **stop/cancel generation** button (sends `client_cancel` frame); visible only when streaming is active. Optional: model name badge and approximate **cost estimate** per response — rendered when `partial_usage` frames carry token counts. | streaming: `CHAT_STREAMING=true`; cost: `CHAT_COST_TRACKING=true` | ✅ DONE |
| 5.9 | Frontend: dynamic placeholder — derives scope hint from active `FilterState`: `"Ask about [Institution] — [Category] — [Date range]"`. Also shows a contract-count hint when the scope is narrow: *"This scope contains 12 contracts."* Both are computed from the same filter-to-label logic already used in the `FilterBar` component. | — (always built) | ✅ DONE |
| 5.10 | Frontend: scope-change prompt — when the backend returns a `ScopeRefusal` object (`type: "scope_refusal"` in the `done` frame), render a **one-click suggestion panel** below the message list. Each suggestion maps to a concrete filter mutation (e.g. *"Expand date range to 2023–2024"*) that the user can apply with a single click. The panel uses the same `FilterBar` update path so the URL state is updated atomically. | — (always built) | ✅ DONE |
| 5.11 | Config: update `src/config.py` — change `llm_provider` default to `"mock"`; add `chat_streaming: bool`, `chat_history_backend: str`, `chat_cache_backend: str`, `chat_feature_flags: list[str]` settings. When `OPENAI_API_KEY` is absent **and** `LLM_PROVIDER` is not `mock`, log a `WARNING` and force `LLM_PROVIDER=mock`. Expose `GET /api/chat/status` endpoint returning `{ "provider": str, "degraded": bool, "features": list[str] }` so the frontend can discover capabilities at startup. | — (always built) | ✅ DONE |
| 5.12 | LLM abstraction and adapter tests — unit tests for `LLMClient` interface and each adapter (`MockLLMClient`, `OpenAIClient`). Tests for `MockLLMClient` always run. Tests for `OpenAIClient` use **recorded response fixtures** (VCR-style) so they pass offline. When `OPENAI_API_KEY` is absent the live-API tests are **skipped with `pytest.mark.skip` and a clear message** explaining the key is not configured — they never fail. | — | ✅ DONE |
| 5.13 | Streaming backpressure and cancellation protocol — formally define the WebSocket message envelope in `src/chatbot/protocol.py` as a set of Pydantic models: `StartFrame`, `TokenFrame`, `PartialUsageFrame`, `DoneFrame`, `ErrorFrame`, `CancelFrame`. Server-side `client_cancel` handler stops generation immediately and sends a final `DoneFrame` with `cancelled: true` and partial usage. Envelope spec is published as a docstring that also acts as the contract for frontend tests. | streaming: `CHAT_STREAMING=true` | ✅ DONE |
| 5.14 | Retry and rate-limit handling in `src/chatbot/llm.py` — exponential backoff with jitter (max 3 retries), explicit `429` / `503` handling, and a simple token-bucket circuit breaker. On retry the same chat session is continued; partial streamed tokens from a failed attempt are discarded before resuming. Only active when `LLM_PROVIDER=openai`. | `OPENAI_API_KEY` present | ✅ DONE |
| 5.15 | Usage and cost accounting in `src/chatbot/usage.py` — collect `prompt_tokens`, `completion_tokens`, `total_cost_usd` per response using OpenAI's `stream_options: {include_usage: true}` field. Store usage records in an in-memory list per session; include in `POST /api/chat/save` output. Optional: persist to Postgres when `postgres_history` flag is active. Only active when `CHAT_COST_TRACKING=true`. | `CHAT_COST_TRACKING=true` | ✅ DONE |
| 5.16 | Provenance and citation in `src/chatbot/context.py` — every response `DoneFrame` includes a `provenance` field: list of `{ "id": str, "title": str, "excerpt": str }` objects identifying which contracts supported the answer. Frontend `ChatBar` renders an optional **"Show Sources"** expandable panel below each assistant message. Only populated when `CHAT_PROVENANCE=true`. | `CHAT_PROVENANCE=true` | ✅ DONE |
| 5.17 | Observability and telemetry — structured timing logs (`request_queued`, `model_call_start`, `first_token`, `done`) written to the Python `logging` module at `DEBUG` level in all modes. Optional OpenTelemetry span export: activated when `observability` in `CHAT_FEATURE_FLAGS` and `opentelemetry-sdk` is installed. Expose `GET /metrics` endpoint with counters (request count, error count, total tokens) as plain text in Prometheus format. | `observability` flag | ✅ DONE |
| 5.18 | CI / E2E tests with replay — deterministic fixture files (`tests/fixtures/chat_mock_responses/`) containing pre-recorded mock LLM response sequences. Backend integration tests use `MockLLMClient` exclusively. Frontend streaming tests mock `WebSocket` with a stub that replays the envelope frames from fixtures. All chatbot-related tests pass in CI **without any real API calls**. | — (always run in CI) | ✅ DONE |
| 5.19 | Feature flags and dev mode — all flags readable via `GET /api/chat/status`. Add a `CHAT_DEBUG=true` flag that logs full prompt/response pairs to a rotating file (`logs/chat_debug.log`). A simple `scripts/dev_chat.py` helper script sends a test message to the local server and prints the envelope frames for manual inspection. | `CHAT_DEBUG=true` | ✅ DONE |
| 5.20 | Security and secrets — API keys are **never forwarded to the frontend**. The `WS /api/chat` endpoint validates and sanitises all incoming `message` and `filters` fields before they reach the LLM (max message length, strip control characters, validate `FilterState` with Pydantic). The `GET /api/chat/status` response never echoes key values. | — (always enforced) | ✅ DONE |
| 5.21 | Accessibility and UX polish — `ChatBar` supports full keyboard navigation (Enter to send, Escape to cancel, Tab to reach the stop button). Displays a typing indicator (CSS animation) during streaming. All message list items have `role="listitem"` and `aria-label`. Mobile-friendly responsive layout. | — (always built) | ✅ DONE |

#### Unit Tests for Phase 5

Tests that require external services or API keys are decorated with conditional `pytest.mark.skipif` markers. When the required configuration is absent the test is reported as **SKIPPED** (not PASSED and not FAILED), with a message explaining what is missing. All other tests **always pass** without any external dependencies.

##### Backend tests — `tests/test_chatbot.py`

| Test | Uses real LLM? | Result without config | What it verifies |
|---|---|---|---|
| `TestContextBuilder::test_small_dataset_full_context` | No | ✅ PASS | `n ≤ 100` contracts → all contracts included in context string |
| `TestContextBuilder::test_large_dataset_summary` | No | ✅ PASS | `n > 100` → top-N + aggregates + compressed summary used |
| `TestContextBuilder::test_provenance_metadata_attached` | No | ✅ PASS | Every document in context carries `id`, `source`, `date` |
| `TestContextBuilder::test_chunk_cache_hit` | No | ✅ PASS | Repeated call with same filter hash uses cached chunks |
| `TestContextBuilder::test_chunk_cache_miss_on_filter_change` | No | ✅ PASS | Changed filters produce a cache miss and recompute |
| `TestContextBuilder::test_filter_integration_with_datastore` | No | ✅ PASS | `build_scoped_context` calls `DataStore.filter()` with the same `FilterState` |
| `TestScopeEnforcement::test_rejects_out_of_scope_institution` | No | ✅ PASS | Institution not in filters → structured `ScopeRefusal` returned |
| `TestScopeEnforcement::test_accepts_in_scope_question` | No | ✅ PASS | Institution matching filters passes through |
| `TestScopeEnforcement::test_refusal_contains_suggestions` | No | ✅ PASS | `ScopeRefusal.suggestions` is non-empty and includes a hint endpoint |
| `TestScopeEnforcement::test_refused_queries_logged` | No | ✅ PASS | Refusal is written to structured log |
| `TestMockLLMClient::test_complete_returns_string` | No | ✅ PASS | `MockLLMClient.complete()` returns deterministic string |
| `TestMockLLMClient::test_stream_yields_tokens` | No | ✅ PASS | `stream_chat()` calls `on_token` callback for each character |
| `TestMockLLMClient::test_get_token_usage_returns_dict` | No | ✅ PASS | Usage dict contains `prompt_tokens`, `completion_tokens` |
| `TestOpenAIClient::test_recorded_fixture_stream` | No — fixture replay | ✅ PASS | Fixture replay produces correct `TokenFrame` sequence |
| `TestOpenAIClient::test_retry_on_429` | No — fixture replay | ✅ PASS | 429 response triggers retry with backoff, eventually succeeds |
| `TestOpenAIClient::test_circuit_breaker_opens` | No — fixture replay | ✅ PASS | 3 consecutive failures open the circuit breaker |
| `TestOpenAIClient::test_live_api_call` _(marker: `@requires_openai_key`)_ | Yes | ⏭ SKIPPED — missing: `OPENAI_API_KEY` env var | Full round-trip with real OpenAI API |
| `TestChatHistory::test_in_memory_append_and_get` | No | ✅ PASS | `InMemoryHistory` stores and retrieves messages by session ID |
| `TestChatHistory::test_in_memory_clear_session` | No | ✅ PASS | `clear()` removes all messages for a session |
| `TestChatHistory::test_redis_fallback_when_unavailable` | No | ✅ PASS | `RedisHistory` with unreachable host falls back to in-memory with WARNING |
| `TestChatHistory::test_redis_history` _(marker: `@requires_redis`)_ | No | ⏭ SKIPPED — missing: Redis server reachable at `localhost:6379` | `RedisHistory` stores and retrieves across instantiations |
| `TestProtocol::test_start_frame_serializes` | No | ✅ PASS | `StartFrame` Pydantic model serialises to expected JSON keys |
| `TestProtocol::test_token_frame_serializes` | No | ✅ PASS | `TokenFrame` contains `type="token"` and `content` |
| `TestProtocol::test_done_frame_with_provenance` | No | ✅ PASS | `DoneFrame` carries `provenance` list when `CHAT_PROVENANCE=true` |
| `TestProtocol::test_cancel_frame_accepted` | No | ✅ PASS | Server-side handler recognises `CancelFrame` and stops generation |
| `TestUsageAccounting::test_cost_recorded_per_session` | No | ✅ PASS | Token counts accumulated per session; retrieved on save |
| `TestUsageAccounting::test_cost_omitted_when_flag_off` | No | ✅ PASS | Cost fields absent from `DoneFrame` when `CHAT_COST_TRACKING=false` |
| `TestChatAPI::test_ws_degraded_mode_when_no_key` | No | ✅ PASS | WebSocket `start` frame includes `"degraded": true` when key absent |
| `TestChatAPI::test_ws_mock_completes_session` | No | ✅ PASS | Full WebSocket exchange using `MockLLMClient` returns `DoneFrame` |
| `TestChatAPI::test_ws_client_cancel_stops_generation` | No | ✅ PASS | Sending `{"type":"cancel"}` frame triggers `DoneFrame(cancelled=true)` |
| `TestChatAPI::test_save_endpoint_returns_json` | No | ✅ PASS | `POST /api/chat/save` returns JSON with `messages`, `filters`, `timestamp` |
| `TestChatAPI::test_status_endpoint_reports_provider` | No | ✅ PASS | `GET /api/chat/status` returns `provider`, `degraded`, `features` |
| `TestChatAPI::test_status_never_exposes_key` | No | ✅ PASS | Response body does not contain the string value of `OPENAI_API_KEY` |
| `TestSecurity::test_oversized_message_rejected` | No | ✅ PASS | Message exceeding max length returns `ErrorFrame` |
| `TestSecurity::test_control_characters_stripped` | No | ✅ PASS | Input sanitiser removes null bytes and control chars before LLM call |
| `TestConfig::test_missing_key_forces_mock_provider` | No | ✅ PASS | `LLM_PROVIDER=openai` with empty key → runtime forced to `mock` + WARNING |
| `TestConfig::test_feature_flags_parsed_from_env` | No | ✅ PASS | `CHAT_FEATURE_FLAGS=streaming,provenance` → settings list has both values |

##### Frontend tests — `frontend/src/__tests__/ChatBar.test.tsx`

| Test | What it verifies |
|---|---|
| `test_renders_input_and_send_button` | ChatBar mounts with input field and send button |
| `test_degraded_banner_shown_when_status_degraded` | When `GET /api/chat/status` returns `degraded: true`, a banner is displayed and input is disabled |
| `test_no_banner_when_status_ok` | Banner absent when `degraded: false` |
| `test_send_message_opens_websocket` | Submitting a message opens a WebSocket to `WS /api/chat` with correct payload |
| `test_token_frames_update_message_list` | Incoming `token` frames append text to the current assistant message |
| `test_done_frame_finalises_message` | `done` frame marks message complete and re-enables input |
| `test_cancel_button_visible_during_streaming` | Stop button appears only while streaming is active |
| `test_cancel_button_sends_cancel_frame` | Clicking stop sends `{"type":"cancel"}` over the socket |
| `test_placeholder_reflects_active_filters` | Placeholder text updates when `FilterState` changes |
| `test_scope_refusal_renders_suggestion_panel` | `done` frame with `scope_refusal` shows one-click suggestion buttons |
| `test_suggestion_click_updates_filter_state` | Clicking a suggestion calls the filter-update callback |
| `test_sources_panel_hidden_by_default` | Provenance panel collapsed by default |
| `test_sources_panel_expands_on_click` | Clicking "Show Sources" reveals provenance entries |
| `test_keyboard_navigation_enter_to_send` | Pressing Enter in the input field sends the message |
| `test_keyboard_navigation_escape_to_cancel` | Pressing Escape during streaming sends cancel frame |
| `test_aria_roles_on_message_list` | Message list items carry `role="listitem"` |

#### Unlocks

- Phase 7 (Save Workspace) can include chat history via `POST /api/chat/save`.
- Chatbot can reference rule flags from Phase 4 in context building.
- `GET /api/chat/status` allows the frontend to discover available features at startup without hard-coding capability assumptions.

---

### Phase 6 — Investigation Modes

**Goal:** Build the three investigation modes — Benchmark Comparison, Compare in Time, and Global Search & Ranking — each reusing shared filters and the query engine.

**Dependencies:** Phase 1 (engine), Phase 2 (API), Phase 3 (UI framework + FilterBar).

#### Tasks

| # | Task | Status |
|---|------|--------|
| 6.1 | **Benchmark Mode** — Backend: `GET /api/benchmark` enhanced with peer-group builder (by type/region/budget), min contract count threshold | ✅ DONE |
| 6.2 | Benchmark Mode — Frontend: `BenchmarkView` page: institution selector + peer-group controls; side-by-side chart (2–3 institutions) | ✅ DONE |
| 6.3 | Benchmark Mode — Frontend: comparison metrics display (total spend, contract count, direct award rate, avg value) | ✅ DONE |
| 6.4 | **Time Mode** — Backend: `GET /api/trends` enhanced with granularity (month/quarter/year) and overlay dates (election/budget) | ✅ DONE |
| 6.5 | Time Mode — Frontend: `TimeView` page: line/area chart with granularity toggle; overlay markers for election/budget dates | ✅ DONE |
| 6.6 | Time Mode — Frontend: multi-metric selection (spend, count, avg value) | ✅ DONE |
| 6.7 | **Global Ranking Mode** — Backend: `GET /api/rankings` enhanced with metric selector (total spend, top-N concentration, fragmentation score, direct award rate) | ✅ DONE |
| 6.8 | Global Ranking Mode — Frontend: `GlobalView` page: sortable ranking table; click-through to institution/vendor profiles | ✅ DONE |
| 6.9 | All modes share the same `FilterBar` component and URL-state | ✅ DONE |

#### Unit Tests for Phase 6

| Test | Description | Status |
|------|-------------|--------|
| `test_engine.py::TestVendorConcentrationScore` (4 tests) | Vendor concentration score (HHI-style) computation | ✅ PASS |
| `test_engine.py::TestFragmentationScore` (3 tests) | Contract fragmentation score computation | ✅ PASS |
| `test_engine.py::TestCompareMultiMetric` (2 tests) | Multi-metric institution comparison | ✅ PASS |
| `test_engine.py::TestPeerGroup` (3 tests) | Peer-group discovery by contract count | ✅ PASS |
| `test_engine.py::TestTrendMultiMetric` (3 tests) | Multi-metric trend generation | ✅ PASS |
| `test_api.py::TestBenchmarkPeerGroup` (3 tests) | `/api/benchmark/peers` endpoint | ✅ PASS |
| `test_api.py::TestBenchmarkMultiMetric` (2 tests) | `/api/benchmark/compare` endpoint | ✅ PASS |
| `test_api.py::TestTrendsEnhanced` (3 tests) | Enhanced `/api/trends` with overlay dates and multi-metric | ✅ PASS |
| `test_api.py::TestRankingsEnhanced` (5 tests) | Enhanced `/api/rankings` with filters and new metrics | ✅ PASS |
| `BenchmarkView.test.tsx` (6 tests) | Renders institutions, peer suggestions, comparison charts, min-contracts filter | ✅ PASS |
| `TimeView.test.tsx` (8 tests) | Loading/empty/chart states, granularity toggle, metric toggle, overlay toggle | ✅ PASS |
| `GlobalView.test.tsx` (9 tests) | Loading/empty/table states, entity toggle, metric selector, rank rows, summary | ✅ PASS |
| `App.test.tsx` (5 new tests) | Routes: /benchmark, /time, /rankings; navigation links | ✅ PASS |

#### Unlocks

- Complete investigative functionality; chatbot can answer mode-specific questions.

---

### Phase 7 — State, Sharing, and Export

**Goal:** Implement URL-encoded shareable links, Save Workspace, and CSV/PDF export from any view.

**Dependencies:** Phase 2 (API), Phase 3 (UI views), Phase 5 (chat history for workspace).

#### Tasks

| # | Task | Status |
|---|------|--------|
| 7.1 | Finalize URL-state encoding: all filters + open accordion + active contract + grouping + comparison selections + active mode | ✅ DONE |
| 7.2 | `POST /api/workspace/save` — snapshot: filters + grouping + chart state + chat history → encoded JSON (base64 or file) | ✅ DONE |
| 7.3 | `GET /api/workspace/load?token=...` — restore workspace from saved snapshot | ✅ DONE |
| 7.4 | Frontend: **Share button** — copies current URL-state link to clipboard | ✅ DONE |
| 7.5 | Frontend: **Save Workspace button** — triggers save, returns downloadable file or shareable token | ✅ DONE |
| 7.6 | Frontend: **Export CSV button** — triggers `GET /api/export/csv` with current filters, browser downloads file | ✅ DONE |
| 7.7 | Frontend: **Export PDF button** — triggers `GET /api/export/pdf` with current filters, browser downloads formatted report | ✅ DONE |
| 7.8 | Backend CSV export: generate CSV from filtered contracts (all fields or user-selected columns) | ✅ DONE |
| 7.9 | Backend PDF export: use `reportlab` or `weasyprint` to generate formatted report with summary stats + contract list | ✅ DONE (ReportLab) |
| 7.10 | Ensure every page/view has the Export / Share / Save buttons visible | ✅ DONE |

#### Unit Tests for Phase 7

- `test_workspace.py::test_save_and_load_round_trip` — save → load restores identical filter state ✅
- `test_workspace.py::test_save_includes_chat_history` — workspace snapshot contains chat messages ✅
- `test_workspace.py::test_load_invalid_token_returns_400` — rejects malformed token ✅
- `test_workspace.py::test_load_non_json_token_returns_400` — rejects non-JSON base64 ✅
- `test_workspace.py::test_save_minimal_payload` — empty filters round-trip ✅
- `test_export.py::test_csv_export_content` — CSV has correct headers and row count ✅
- `test_export.py::test_csv_export_respects_filters` — only filtered contracts in CSV ✅
- `test_export.py::test_pdf_export_returns_pdf` — response Content-Type is `application/pdf` ✅
- `test_export.py::test_pdf_export_respects_filters` — PDF generated with filter params ✅
- `test_export.py::test_pdf_export_with_sort` — PDF generated with sort params ✅
- `test_url_state.py::test_full_state_encode_decode` — all fields survive round-trip ✅
- `test_url_state.py::test_partial_state_defaults` — empty FilterState → empty dict ✅
- `test_url_state.py::test_page_one_omitted` — page=1 not encoded ✅
- `test_url_state.py::test_mode_included_when_set` — mode param encoded ✅
- `test_url_state.py::test_group_by_included` — group_by param encoded ✅
- `WorkspaceToolbar.test.tsx` — renders all four buttons, share copies URL, CSV href, PDF href, save triggers download (5 tests) ✅
- `url-state.test.ts` — full state round-trip, missing params defaults, mode encode/decode (3 new tests) ✅

#### Unlocks

- Complete application; all modes, views, and features are shareable and exportable.

---

### Phase 8 — Polish, Integration Testing, and Deployment

**Goal:** End-to-end integration tests, performance optimization, error handling, accessibility, and deployment packaging.

**Dependencies:** All previous phases.

#### Tasks

| # | Task | Status |
|---|------|--------|
| 8.1 | End-to-end integration tests: scrape → load → filter → visualize → export flow | ✅ DONE |
| 8.2 | Performance testing: load 10k+ contracts, measure filter/aggregation speed (target < 200ms) | ✅ DONE |
| 8.3 | Error boundary components in frontend: graceful fallback on API failure | ✅ DONE |
| 8.4 | Loading states and skeleton screens for all async views | ✅ DONE |
| 8.5 | Accessibility audit: ARIA labels, keyboard navigation, color contrast | ✅ DONE |
| 8.6 | Create `Dockerfile` + `docker-compose.yml` for one-command startup | ✅ DONE |
| 8.7 | Create `Makefile` / `scripts/start.sh` for local dev (start backend + frontend) | ✅ DONE |
| 8.8 | Update all documentation (README, ARCHITECTURE, QUICKSTART) for GovLens | ✅ DONE |
| 8.9 | CI pipeline: lint + test + build on push | ✅ DONE |

#### Unit Tests for Phase 8

- `test_e2e.py::TestFullWorkflow` (6 tests) — load data → filter → aggregate → export CSV consistency, benchmark, treemap, rankings, PDF export
- `test_e2e.py::TestChatbotWorkflow` (4 tests) — chatbot status, WebSocket session, save endpoint, scoped context
- `test_e2e.py::TestRuleWorkflow` (5 tests) — preset discovery, evaluate all, custom conditions, severity scores, workspace round-trip
- `test_performance.py::TestFilterPerformance` (6 tests) — 10k filter <200ms, date/category/combined/text/50k timing
- `test_performance.py::TestAggregationPerformance` (4 tests) — aggregation, group-by, trend, rankings on 10k contracts
- `test_performance.py::TestSortPerformance` (2 tests) — single/multi-column sort on 10k contracts
- `test_performance.py::TestLoadPerformance` (2 tests) — load 10k <2s, 50k <10s
- Frontend: `ErrorBoundary.tsx` and `LoadingSkeleton.tsx` components created; accessibility ARIA attributes added to 6 components
- All 341 backend tests pass (+ 1 skipped), all 135 frontend tests pass

#### Unlocks

- Production-ready application.

---

## 3 — FINAL SUMMARY

### 3.1 Full Dependency Map

```
Phase 0: Foundation (Schema, Data Model, Restructure)
   │
   ├──► Phase 1: In-Memory Query & Aggregation Engine
   │       │
   │       ├──► Phase 2: Backend API (FastAPI)
   │       │       │
   │       │       ├──► Phase 3: Frontend — Institution Lens UI
   │       │       │       │
   │       │       │       ├──► Phase 6: Investigation Modes
   │       │       │       │
   │       │       │       └──► Phase 7: State, Sharing, Export
   │       │       │
   │       │       ├──► Phase 5: Contextual Chatbot
   │       │       │
   │       │       └──► Phase 4: Rule Builder
   │       │
   │       └──► Phase 4: Rule Builder (backend part)
   │
   └──► All phases depend on Phase 0

Phase 8: Polish & Deployment ← depends on ALL prior phases
```

### 3.2 Recommended Implementation Order

| Order | Phase | Estimated Effort | Status | Rationale |
|-------|-------|-----------------|--------|-----------|
| 1st | **Phase 0** — Foundation | 1–2 days | ✅ **COMPLETE** | Unblocks everything; low risk |
| 2nd | **Phase 1** — Query Engine | 2–3 days | ✅ **COMPLETE** | Core logic; must be solid before API |
| 3rd | **Phase 2** — Backend API | 2–3 days | ✅ **COMPLETE** | Exposes engine to frontend; enables parallel frontend work |
| 4th | **Phase 3** — Institution Lens UI | 4–5 days | ✅ **COMPLETE** | Primary user-facing view; largest frontend effort |
| 5th | **Phase 4** — Rule Builder | 3–4 days | ✅ **COMPLETE** | High-value investigative feature; backend + frontend |
| 6th | **Phase 5** — Chatbot | 4–6 days | ✅ **COMPLETE** | All LLM features optional; `MockLLMClient` default; 49 backend passed + 2 skipped (require `OPENAI_API_KEY` / Redis) + 15 frontend tests |
| 7th | **Phase 6** — Investigation Modes | 3–4 days | ✅ **COMPLETE** | Extends existing UI infrastructure |
| 8th | **Phase 7** — State & Export | 2–3 days | ✅ **COMPLETE** | Polishes the experience; depends on stable views |
| 9th | **Phase 8** — Polish & Deploy | 2–3 days | ✅ **COMPLETE** | Final pass |

**Total estimated effort: 24–35 working days | Completed: ~24–35 days (All phases complete)**

### 3.3 Risks and Potential Blockers

| Risk | Impact | Mitigation |
|------|--------|------------|
| **No `award_type` in scraped data** | Several filters and rules depend on this field | Use `"unknown"` default; add manual tagging UI or heuristic inference from contract title/type |
| **LLM API cost / rate limits** | Chatbot and summarization depend on external API | Support mock/stub mode; cache responses; allow offline mode without chatbot |
| **CRZ website structure changes** | Scraper may break if HTML changes | Existing tests use mocked HTML; scraper is isolated from the app |
| **Large dataset performance** | 100k+ contracts may exceed in-memory limits | Add pagination to engine; consider SQLite as an optional backend; profile early |
| **Treemap / D3 complexity** | D3 treemaps with click-to-drill and responsiveness are non-trivial | Start with a simpler chart (bar chart) and add treemap incrementally |
| **PDF export complexity** | Formatted PDF generation in Python requires careful layout work | Start with CSV-only; add PDF in later iteration using `weasyprint` |
| **Frontend tech stack decision** | React + TypeScript adds build complexity | Could fallback to a simpler stack (e.g., plain HTML + HTMX + chart.js) if team prefers |
| **Scope creep from chatbot** | LLM may generate unreliable answers about contracts | Enforce strict scope; add disclaimers; limit to summarization and factual queries |
| **No authentication / multi-user** | Design doc doesn't mention auth; workspace save/share implies some user context | Keep single-user for demo; add session-based persistence without auth |

### 3.4 Proposed Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3.10+ / FastAPI / Uvicorn | Already Python-based; FastAPI gives auto-docs + WebSocket + async |
| Data model | Pydantic v2 | Validation, serialization, OpenAPI schema generation |
| Query engine | Pure Python (pandas optional for heavy aggregations) | Simple, no external DB dependency for demo |
| Frontend | React 18 + TypeScript + Vite | Modern, component-based, strong ecosystem |
| Visualization | D3.js (treemap) + Recharts (line/bar) | D3 for custom treemap; Recharts for standard charts |
| Styling | Tailwind CSS | Utility-first, quick to build |
| Chatbot LLM | Anthropic Claude (claude-sonnet) via `anthropic` SDK | Per design doc specification |
| PDF export | WeasyPrint or ReportLab | Python-native PDF generation |
| Deployment | Docker + docker-compose | Single-command startup |

---

## 4 - SCRAPER CHANGE UPDATE (2026-03-07)

### 4.1 Requested Scope Completed

| Item | Status | Notes |
|------|--------|-------|
| Price filter support (`min_price`, `max_price`) | DONE | Added to CLI and scraper pipeline; applied immediately after listing extraction and before detail/PDF requests |
| Additional field scraping (`rezort`) | DONE | Added extraction from detail page and exported in NDJSON |
| Request throttling (3 seconds) | DONE | Default delay set to 3.0s; global request throttler enforces spacing between all HTTP calls (listing, detail, PDF) |
| Full validation of "Identifik�cia a zmluvy" | DONE | Parser now stores all label/value pairs under `identification_fields` and ordered `identification_section_items` |
| Documentation/plan update | DONE | README arguments/output updated and this implementation plan section added |

### 4.2 Files Updated

- `src/scraper.py`
- `scrape_crz.py`
- `tests/test_integration.py`
- `tests/test_parser.py`
- `README.md`
- `IMPLEMENTATION_PLAN.md`

### 4.3 "Identifik�cia a zmluvy" Coverage Confirmation

Current parser behavior now includes:

- Explicit mapped fields: `contract_type`, `rezort`, `contract_number_detail`, `contract_id_detail`, `buyer_detail`, `supplier_detail`, `ico_buyer`, `ico_supplier`, `ico_rezort`
- Complete raw section capture for all fields present on the page:
  - `identification_fields` (label -> value, duplicates preserved as lists)
  - `identification_section_items` (ordered list of `{label, value}`)

This provides full section-level coverage even when CRZ adds or changes labels.

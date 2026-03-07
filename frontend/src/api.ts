/**
 * GovLens API Client
 *
 * Thin wrapper around fetch() for calling the backend REST API.
 * All functions return parsed JSON. The base URL can be empty when
 * Vite's proxy forwards `/api` to the backend.
 */

import type {
  AggregationsResponse,
  BenchmarkResponse,
  BenchmarkPeersResponse,
  BenchmarkMultiMetricResponse,
  ConditionGroupData,
  CustomRuleResponse,
  FilterState,
  InstitutionProfile,
  InstitutionSummary,
  PaginatedContracts,
  RankingsResponse,
  RuleConfig,
  RuleEvaluationResponse,
  RulePreset,
  Contract,
  TreemapNode,
  TrendsResponseWithOverlays,
  VendorProfile,
  VendorSummary,
  SortSpec,
  GroupByField,
} from './types';

const BASE = '';
const API_URL = (import.meta.env.VITE_API_URL || '').trim();

function filterParams(filters: FilterState): Record<string, string> {
  const p: Record<string, string> = {};
  if (filters.institutions?.length) p.institutions = filters.institutions.join(',');
  if (filters.date_from) p.date_from = filters.date_from;
  if (filters.date_to) p.date_to = filters.date_to;
  if (filters.categories?.length) p.categories = filters.categories.join(',');
  if (filters.vendors?.length) p.vendors = filters.vendors.join(',');
  if (filters.value_min !== undefined) p.value_min = String(filters.value_min);
  if (filters.value_max !== undefined) p.value_max = String(filters.value_max);
  if (filters.award_types?.length) p.award_types = filters.award_types.join(',');
  if (filters.text_search) p.text_search = filters.text_search;
  return p;
}

function sortParam(sort: SortSpec): string {
  return sort.map(([f, d]) => `${f}:${d}`).join(',');
}

function qs(params: Record<string, string>): string {
  const s = new URLSearchParams(params).toString();
  return s ? `?${s}` : '';
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

// ── Contracts ───────────────────────────────────────────────────────

export async function fetchContracts(
  filters: FilterState = {},
  page = 1,
  pageSize = 20,
  sort: SortSpec = [],
): Promise<PaginatedContracts> {
  const p: Record<string, string> = {
    ...filterParams(filters),
    page: String(page),
    page_size: String(pageSize),
  };
  if (sort.length) p.sort = sortParam(sort);
  return get<PaginatedContracts>(`/api/contracts${qs(p)}`);
}

export async function fetchContract(id: string): Promise<Contract> {
  return get<Contract>(`/api/contracts/${encodeURIComponent(id)}`);
}

// ── Aggregations ────────────────────────────────────────────────────

export async function fetchAggregations(
  filters: FilterState = {},
  groupBy: GroupByField = 'category',
): Promise<AggregationsResponse> {
  const p = { ...filterParams(filters), group_by: groupBy };
  return get<AggregationsResponse>(`/api/aggregations${qs(p)}`);
}

// ── Treemap ─────────────────────────────────────────────────────────

export async function fetchTreemap(
  filters: FilterState = {},
  groupBy: GroupByField = 'category',
  subGroupBy?: string,
): Promise<TreemapNode> {
  const p: Record<string, string> = { ...filterParams(filters), group_by: groupBy };
  if (subGroupBy) p.sub_group_by = subGroupBy;
  return get<TreemapNode>(`/api/treemap${qs(p)}`);
}

// ── Benchmark ───────────────────────────────────────────────────────

export async function fetchBenchmark(
  institutions: string[],
  metric = 'total_spend',
  minContracts?: number,
): Promise<BenchmarkResponse> {
  const p: Record<string, string> = { institutions: institutions.join(','), metric };
  if (minContracts !== undefined) p.min_contracts = String(minContracts);
  return get<BenchmarkResponse>(`/api/benchmark${qs(p)}`);
}

export async function fetchBenchmarkPeers(
  institution: string,
  minContracts = 1,
): Promise<BenchmarkPeersResponse> {
  const p = { institution, min_contracts: String(minContracts) };
  return get<BenchmarkPeersResponse>(`/api/benchmark/peers${qs(p)}`);
}

export async function fetchBenchmarkMultiMetric(
  institutions: string[],
  metrics: string[],
): Promise<BenchmarkMultiMetricResponse> {
  const p = { institutions: institutions.join(','), metrics: metrics.join(',') };
  return get<BenchmarkMultiMetricResponse>(`/api/benchmark/compare${qs(p)}`);
}

// ── Trends ──────────────────────────────────────────────────────────

export async function fetchTrends(
  filters: FilterState = {},
  granularity = 'month',
  metric = 'total_spend',
  overlay = false,
): Promise<TrendsResponseWithOverlays> {
  const p: Record<string, string> = { ...filterParams(filters), granularity, metric };
  if (overlay) p.overlay = 'true';
  return get<TrendsResponseWithOverlays>(`/api/trends${qs(p)}`);
}

export async function fetchTrendsMultiMetric(
  filters: FilterState = {},
  granularity = 'month',
  metrics: string[] = ['total_spend'],
  overlay = false,
): Promise<TrendsResponseWithOverlays> {
  const p: Record<string, string> = {
    ...filterParams(filters),
    granularity,
    metrics: metrics.join(','),
  };
  if (overlay) p.overlay = 'true';
  return get<TrendsResponseWithOverlays>(`/api/trends${qs(p)}`);
}

// ── Rankings ────────────────────────────────────────────────────────

export async function fetchRankings(
  entity: 'institutions' | 'vendors' = 'institutions',
  metric = 'total_spend',
  filters: FilterState = {},
): Promise<RankingsResponse> {
  const p = { ...filterParams(filters), entity, metric };
  return get<RankingsResponse>(`/api/rankings${qs(p)}`);
}

// ── Institutions ────────────────────────────────────────────────────

export async function fetchInstitutions(): Promise<{ institutions: InstitutionSummary[] }> {
  return get<{ institutions: InstitutionSummary[] }>('/api/institutions');
}

export async function fetchInstitutionProfile(id: string): Promise<InstitutionProfile> {
  return get<InstitutionProfile>(`/api/institutions/${encodeURIComponent(id)}`);
}

// ── Vendors ─────────────────────────────────────────────────────────

export async function fetchVendors(): Promise<{ vendors: VendorSummary[] }> {
  return get<{ vendors: VendorSummary[] }>('/api/vendors');
}

export async function fetchVendorProfile(id: string): Promise<VendorProfile> {
  return get<VendorProfile>(`/api/vendors/${encodeURIComponent(id)}`);
}

// ── Export ───────────────────────────────────────────────────────────

export function csvExportUrl(
  filters: FilterState = {},
  sort: SortSpec = [],
): string {
  const p = filterParams(filters);
  if (sort.length) p.sort = sortParam(sort);
  return `/api/export/csv${qs(p)}`;
}

export function pdfExportUrl(
  filters: FilterState = {},
  sort: SortSpec = [],
): string {
  const p = filterParams(filters);
  if (sort.length) p.sort = sortParam(sort);
  return `/api/export/pdf${qs(p)}`;
}

// ── Rules (Phase 4) ─────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export async function fetchRulePresets(): Promise<{ presets: RulePreset[] }> {
  return get<{ presets: RulePreset[] }>('/api/rules/presets');
}

export async function evaluateRules(
  rules: RuleConfig[] | null = null,
  filters: FilterState = {},
): Promise<RuleEvaluationResponse> {
  const p = filterParams(filters);
  return post<RuleEvaluationResponse>(
    `/api/rules/evaluate${qs(p)}`,
    { rules },
  );
}

export async function evaluateCustomConditions(
  group: ConditionGroupData,
  filters: FilterState = {},
): Promise<CustomRuleResponse> {
  const p = filterParams(filters);
  return post<CustomRuleResponse>(
    `/api/rules/custom${qs(p)}`,
    group,
  );
}

// ── Chatbot (Phase 5) ───────────────────────────────────────────────

import type { ChatStatusResponse, ChatSaveResponse, WorkspaceSaveResponse, WorkspaceLoadResponse } from './types';

export async function fetchChatStatus(): Promise<ChatStatusResponse> {
  return get<ChatStatusResponse>('/api/chat/status');
}

export async function saveChat(
  sessionId: string,
  filters: FilterState = {},
): Promise<ChatSaveResponse> {
  return post<ChatSaveResponse>('/api/chat/save', {
    session_id: sessionId,
    filters,
  });
}

/**
 * Build the WebSocket URL for the chat endpoint.
 * Auto-detects protocol (ws/wss) from the current page.
 */
export function chatWebSocketUrl(): string {
  // Prefer explicit backend URL when provided (e.g. docker dev profile).
  // Otherwise, use same-origin so Vite proxy can route /api requests.
  if (API_URL) {
    const url = new URL(API_URL);
    const wsProto = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProto}//${url.host}/api/chat`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/api/chat`;
}

// ── Workspace (Phase 7) ─────────────────────────────────────────────

export async function saveWorkspace(
  state: Record<string, unknown>,
): Promise<WorkspaceSaveResponse> {
  return post<WorkspaceSaveResponse>('/api/workspace/save', state);
}

export async function loadWorkspace(token: string): Promise<WorkspaceLoadResponse> {
  return get<WorkspaceLoadResponse>(`/api/workspace/load?token=${encodeURIComponent(token)}`);
}

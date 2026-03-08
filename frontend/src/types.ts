/**
 * GovLens Frontend Type Definitions
 *
 * Mirrors the backend Pydantic models and API response shapes.
 */

export interface Contract {
  contract_id: string | null;
  contract_title: string | null;
  contract_number: string | null;
  buyer: string | null;
  supplier: string | null;
  price_numeric_eur: number | null;
  price_raw: string | null;
  published_date: string | null;
  category: string;
  award_type: string;
  pdf_text_summary: string;
  contract_url: string | null;
  ico_buyer: string | null;
  ico_supplier: string | null;
  date_published: string | null;
  date_concluded: string | null;
  date_effective: string | null;
  date_valid_until: string | null;
  pdf_url: string | null;
  pdf_text: string | null;
  scraped_at: string | null;
}

export interface FilterState {
  institutions?: string[];
  date_from?: string;
  date_to?: string;
  categories?: string[];
  vendors?: string[];
  value_min?: number;
  value_max?: number;
  award_types?: string[];
  text_search?: string;
}

export interface PaginatedContracts {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  contracts: Contract[];
}

export interface AggregationResult {
  group_key: string;
  group_value: string;
  contract_count: number;
  total_spend: number;
  avg_value: number;
  max_value: number;
}

export interface AggregationsResponse {
  group_by: string;
  results: AggregationResult[];
  summary: {
    total_spend: number;
    contract_count: number;
    avg_value: number;
    max_value: number;
  };
}

export interface TreemapNode {
  name: string;
  value: number;
  contract_count?: number;
  children?: TreemapNode[];
}

export interface TrendPoint {
  period: string;
  value: number;
  count?: number;
}

export interface TrendsResponse {
  granularity: string;
  metric: string;
  data: TrendPoint[];
}

export interface RankingItem {
  rank: number;
  institution?: string;
  vendor?: string;
  value: number;
}

export interface RankingsResponse {
  entity: string;
  metric: string;
  rankings: RankingItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface InstitutionSummary {
  name: string;
  ico: string | null;
  contract_count: number;
  total_spend: number;
}

export interface VendorSummary {
  name: string;
  ico: string | null;
  contract_count: number;
  total_spend: number;
}

export interface InstitutionProfile {
  name: string;
  ico: string | null;
  contract_count: number;
  total_spend: number;
  avg_value: number;
  max_value: number;
  top_vendors: { name: string; contract_count: number; total_spend: number }[];
  trend: TrendPoint[];
  contracts: Contract[];
}

export interface VendorProfile {
  name: string;
  ico: string | null;
  contract_count: number;
  total_spend: number;
  avg_value: number;
  max_value: number;
  institutions_served: { name: string; contract_count: number; total_spend: number }[];
  trend: TrendPoint[];
  contracts: Contract[];
}

export interface BenchmarkResult {
  institution: string;
  value: number;
}

export interface BenchmarkResponse {
  metric: string;
  results: BenchmarkResult[];
}

// ── Phase 6: Investigation Modes types ──────────────────────────────

export interface BenchmarkPeersResponse {
  institution: string;
  min_contracts: number;
  peers: string[];
}

export interface BenchmarkMultiMetricResult {
  institution: string;
  [metric: string]: string | number;
}

export interface BenchmarkMultiMetricResponse {
  metrics: string[];
  results: BenchmarkMultiMetricResult[];
}

export interface OverlayDate {
  date: string;
  label: string;
}

export interface TrendsMultiMetricResponse {
  granularity: string;
  metrics: string[];
  data: Record<string, unknown>[];
  overlays?: OverlayDate[];
}

export interface TrendsResponseWithOverlays extends TrendsResponse {
  overlays?: OverlayDate[];
}

export type SortSpec = [string, string][];

export type GroupByField = 'category' | 'supplier' | 'buyer' | 'month' | 'award_type';

// ── Phase 9: Compare (Contracts vs Subcontractors) types ────────────

export interface CompareAggregationRow {
  group_value: string;
  contracts_total_spend: number;
  contracts_contract_count: number;
  contracts_avg_value: number;
  subcontractors_total_spend: number;
  subcontractors_contract_count: number;
  subcontractors_avg_value: number;
}

export interface CompareAggregationsResponse {
  group_by: string;
  data: CompareAggregationRow[];
  contracts_summary: {
    total_spend: number;
    contract_count: number;
    avg_value: number;
    max_value: number;
  };
  subcontractors_summary: {
    total_spend: number;
    contract_count: number;
    avg_value: number;
    max_value: number;
  };
  has_subcontractors: boolean;
}

// ── Phase 4: Rule Builder types ─────────────────────────────────────

export interface RulePreset {
  id: string;
  name: string;
  description: string;
  params: Record<string, number>;
}

export interface RuleConfig {
  id: string;
  params: Record<string, number>;
}

export interface RuleFlagItem {
  rule_id: string;
  rule_name: string;
  severity: number;
  description: string;
  contract_id: string | null;
  vendor: string | null;
  institution: string | null;
  details: Record<string, unknown>;
}

export interface RuleEvaluationResponse {
  total_flags: number;
  contract_severities: Record<string, number>;
  flags: RuleFlagItem[];
}

export interface ConditionItem {
  field: string;
  operator: string;
  value: string | number;
}

export interface ConditionGroupData {
  logic: 'AND' | 'OR';
  conditions: ConditionItem[];
}

export interface CustomRuleResponse {
  total_matched: number;
  total_evaluated: number;
  contracts: Contract[];
}

// ── Phase 5: Chatbot types ──────────────────────────────────────────

export interface ChatStatusResponse {
  provider: string;
  degraded: boolean;
  features: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ProvenanceItem {
  id: string;
  title: string;
  excerpt: string;
}

export interface ScopeRefusalData {
  reason: string;
  suggestions: ScopeSuggestion[];
  hint_endpoint: string;
}

export interface ScopeSuggestion {
  label: string;
  action: string;
  value: string;
}

export interface ChatStartFrame {
  type: 'start';
  session_id: string;
  degraded: boolean;
  provider: string;
}

export interface ChatTokenFrame {
  type: 'token';
  content: string;
}

export interface ChatDoneFrame {
  type: 'done';
  content: string;
  cancelled: boolean;
  provenance: ProvenanceItem[];
  scope_refusal: ScopeRefusalData | null;
  usage: Record<string, number> | null;
}

export interface ChatErrorFrame {
  type: 'error';
  message: string;
}

export type ChatFrame = ChatStartFrame | ChatTokenFrame | ChatDoneFrame | ChatErrorFrame;

export interface ChatSaveResponse {
  session_id: string;
  messages: ChatMessage[];
  filters: FilterState;
  timestamp: string;
  usage?: Record<string, number>;
}

// ── Phase 7: Workspace types ────────────────────────────────────────

export interface WorkspaceSnapshot {
  version: number;
  filters: FilterState;
  groupBy: string;
  sort: SortSpec;
  page: number;
  mode: string;
  chartState: Record<string, unknown>;
  chat_history: ChatMessage[];
  saved_at: string;
}

export interface WorkspaceSaveResponse {
  token: string;
  snapshot: WorkspaceSnapshot;
}

export interface WorkspaceLoadResponse {
  snapshot: WorkspaceSnapshot;
}

/**
 * GovLens Frontend Type Definitions
 *
 * Mirrors the backend Pydantic models and API response shapes.
 */

export interface Subcontractor {
  name: string;
  ico?: string | null;
}

export interface TenderDocument {
  document_name: string;
  document_title: string;
  document_type: string;
  file_size: string | null;
  uploaded_at: string;
  link: string;
  is_external_link: boolean;
}

export interface TenderParticipant {
  ico: string | null;
  name: string;
  proposed_sum: string | null;
  proposed_sum_eur: number | null;
}

export interface TenderPart {
  part_number: number | null;
  document: TenderDocument | null;
  participants: TenderParticipant[] | null;
  notes: string | null;
}

export interface Tender {
  tender_id: string;
  tender_url: string | null;
  page_title: string | null;
  notice_id: string | null;
  subject_name: string | null;
  file_reference: string | null;
  procedure_type: string | null;
  template_type: string | null;
  procurement_type: string | null;
  procurement_result: string | null;
  estimated_value: string | null;
  main_cpv: string | null;
  is_divided_into_parts: string | null;
  electronic_auction: string | null;
  central_procurement: string | null;
  nuts: string | null;
  short_description: string | null;
  evaluation_criterion: string | null;
  evaluation_price_basis: string | null;
  offer_submission_deadline: string | null;
  planned_opening_time: string | null;
  result_document_count: number | null;
  documents: TenderDocument[];
  parts: TenderPart[];
}

export interface Contract {
  contract_id: string | null;
  contract_title: string | null;
  contract_number: string | null;
  contract_number_detail: string | null;
  contract_type: string | null;
  buyer: string | null;
  buyer_detail: string | null;
  supplier: string | null;
  supplier_detail: string | null;
  price_numeric_eur: number | null;
  price_raw: string | null;
  published_date: string | null;
  published_day: string | null;
  published_month: string | null;
  published_year: string | null;
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
  pdf_urls: string[] | null;
  pdf_text: string | null;
  scraped_at: string | null;
  rezort: string | null;
  // Scanned / LLM-enriched fields
  scanned_suggested_title?: string | null;
  scanned_service_type?: string | null;
  scanned_service_subtype?: string | null;
  scanned_related_contract_number?: string | null;
  scanned_supplier_ico?: string | null;
  scanned_contract_value?: number | null;
  scanned_payment_reason?: string | null;
  scanned_contract_type?: string | null;
  scanned_summary?: string | null;
  scanned_subcontractors?: Subcontractor[] | null;
  // Subcontractor (expanded)
  subcontractor?: string | null;
  ico_subcontractor?: string | null;
  // Public procurement / tender linkage
  public_procurement_id?: string | number | null;
  public_procurement_portal?: string | null;
  public_procurement_url?: string | null;
  // Embedded tender (returned by /api/contracts/{id} when a match exists)
  _tender?: Tender | null;
  // Red flag fields (populated when contract has merged red flag data)
  red_flag_type?: string | null;
  red_flag_name?: string | null;
  red_flag_severity?: string | null;
  red_flag_description?: string | null;
  red_flag_dataset?: string | null;
}

export interface FilterState {
  institutions?: string[];
  date_from?: string;
  date_to?: string;
  categories?: string[];
  scanned_service_types?: string[];
  scanned_service_subtypes?: string[];
  vendors?: string[];
  institution_icos?: string[];
  vendor_icos?: string[];
  icos?: string[];
  value_min?: number;
  value_max?: number;
  award_types?: string[];
  text_search?: string;
  // Red flag filters
  red_flag_datasets?: string[];
  red_flag_types?: string[];
  institution_flag_count_min?: number;
  institution_flag_count_max?: number;
  vendor_flag_count_min?: number;
  vendor_flag_count_max?: number;
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

export type GroupByField = 'category' | 'supplier' | 'buyer' | 'month' | 'award_type' | 'red_flag_type';

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

export interface SlicerOption {
  value: string;
  count: number;
}

export interface FilterOptionsResponse {
  institutions: SlicerOption[];
  vendors: SlicerOption[];
  institution_icos: SlicerOption[];
  vendor_icos: SlicerOption[];
  categories: SlicerOption[];
  scanned_service_types: SlicerOption[];
  scanned_service_subtypes: SlicerOption[];
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

// ── Red Flag Dataset types ──────────────────────────────────────────

export type RedFlagSeverity = 'mild' | 'moderate' | 'severe';

export interface RedFlagOccurrence {
  contract_id: string;
  contract_title: string;
  institution: string;
  vendor: string;
  ico_buyer: string | null;
  ico_supplier: string | null;
  price_numeric_eur: number | null;
  date_published: string | null;
  category: string;
  award_type: string;
  red_flag_type: string;
  red_flag_name: string;
  severity: RedFlagSeverity;
  description: string;
}

export interface RedFlagRuleUsed {
  rule_id: string;
  rule_name: string;
  severity_label: RedFlagSeverity;
  params: Record<string, number>;
}

export interface RedFlagDataset {
  dataset_name: string;
  created_at: string;
  total_flags: number;
  total_contracts_evaluated: number;
  rules_used: RedFlagRuleUsed[];
  flags: RedFlagOccurrence[];
}

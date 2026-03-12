/**
 * URL-State Manager
 *
 * Reads and writes filter state, sort spec, group-by, page, mode, and
 * view state to/from URL search params so that every view is bookmarkable
 * and back-navigation restores the full UI state.
 */

import type { FilterState, SortSpec, GroupByField } from './types';

export type AppMode = 'dashboard' | 'benchmark' | 'time' | 'rankings' | 'contracts';

export interface UrlState {
  filters: FilterState;
  sort: SortSpec;
  groupBy: GroupByField;
  page: number;
  pageSize: number;
  mode: AppMode;
}

/** Parse the current URL search params into a UrlState. */
export function parseUrlState(search: string): UrlState {
  const p = new URLSearchParams(search);

  const filters: FilterState = {};
  if (p.get('institutions')) filters.institutions = p.get('institutions')!.split('|');
  if (p.get('date_from')) filters.date_from = p.get('date_from')!;
  if (p.get('date_to')) filters.date_to = p.get('date_to')!;
  if (p.get('categories')) filters.categories = p.get('categories')!.split('|');
  if (p.get('scanned_service_types')) filters.scanned_service_types = p.get('scanned_service_types')!.split('|');
  if (p.get('scanned_service_subtypes')) filters.scanned_service_subtypes = p.get('scanned_service_subtypes')!.split('|');
  if (p.get('vendors')) filters.vendors = p.get('vendors')!.split('|');
  if (p.get('institution_icos')) filters.institution_icos = p.get('institution_icos')!.split('|');
  if (p.get('vendor_icos')) filters.vendor_icos = p.get('vendor_icos')!.split('|');
  if (p.get('icos')) filters.icos = p.get('icos')!.split('|');
  if (p.get('value_min')) filters.value_min = Number(p.get('value_min'));
  if (p.get('value_max')) filters.value_max = Number(p.get('value_max'));
  if (p.get('award_types')) filters.award_types = p.get('award_types')!.split('|');
  if (p.get('text_search')) filters.text_search = p.get('text_search')!;
  if (p.get('red_flag_datasets')) filters.red_flag_datasets = p.get('red_flag_datasets')!.split('|');
  if (p.get('red_flag_types')) filters.red_flag_types = p.get('red_flag_types')!.split('|');
  if (p.get('institution_flag_count_min')) filters.institution_flag_count_min = Number(p.get('institution_flag_count_min'));
  if (p.get('institution_flag_count_max')) filters.institution_flag_count_max = Number(p.get('institution_flag_count_max'));
  if (p.get('vendor_flag_count_min')) filters.vendor_flag_count_min = Number(p.get('vendor_flag_count_min'));
  if (p.get('vendor_flag_count_max')) filters.vendor_flag_count_max = Number(p.get('vendor_flag_count_max'));

  const sort: SortSpec = [];
  const sortStr = p.get('sort');
  if (sortStr) {
    for (const token of sortStr.split(',')) {
      const [field, dir = 'asc'] = token.split(':');
      if (field) sort.push([field.trim(), dir.trim()]);
    }
  }

  const groupBy = (p.get('group_by') as GroupByField) || 'supplier';
  const page = Math.max(1, Number(p.get('page')) || 1);
  const pageSize = Math.max(1, Number(p.get('page_size')) || 20);
  const mode = (p.get('mode') as AppMode) || 'dashboard';

  return { filters, sort, groupBy, page, pageSize, mode };
}

/** Encode a UrlState back to a query string (without leading ?). */
export function encodeUrlState(state: UrlState): string {
  const p = new URLSearchParams();
  const f = state.filters;

  if (f.institutions?.length) p.set('institutions', f.institutions.join('|'));
  if (f.date_from) p.set('date_from', f.date_from);
  if (f.date_to) p.set('date_to', f.date_to);
  if (f.categories?.length) p.set('categories', f.categories.join('|'));
  if (f.scanned_service_types?.length) p.set('scanned_service_types', f.scanned_service_types.join('|'));
  if (f.scanned_service_subtypes?.length) p.set('scanned_service_subtypes', f.scanned_service_subtypes.join('|'));
  if (f.vendors?.length) p.set('vendors', f.vendors.join('|'));
  if (f.institution_icos?.length) p.set('institution_icos', f.institution_icos.join('|'));
  if (f.vendor_icos?.length) p.set('vendor_icos', f.vendor_icos.join('|'));
  if (f.icos?.length) p.set('icos', f.icos.join('|'));
  if (f.value_min !== undefined) p.set('value_min', String(f.value_min));
  if (f.value_max !== undefined) p.set('value_max', String(f.value_max));
  if (f.award_types?.length) p.set('award_types', f.award_types.join('|'));
  if (f.text_search) p.set('text_search', f.text_search);
  if (f.red_flag_datasets?.length) p.set('red_flag_datasets', f.red_flag_datasets.join('|'));
  if (f.red_flag_types?.length) p.set('red_flag_types', f.red_flag_types.join('|'));
  if (f.institution_flag_count_min !== undefined) p.set('institution_flag_count_min', String(f.institution_flag_count_min));
  if (f.institution_flag_count_max !== undefined) p.set('institution_flag_count_max', String(f.institution_flag_count_max));
  if (f.vendor_flag_count_min !== undefined) p.set('vendor_flag_count_min', String(f.vendor_flag_count_min));
  if (f.vendor_flag_count_max !== undefined) p.set('vendor_flag_count_max', String(f.vendor_flag_count_max));

  if (state.sort.length) {
    p.set('sort', state.sort.map(([field, dir]) => `${field}:${dir}`).join(','));
  }
  if (state.groupBy && state.groupBy !== 'supplier') {
    p.set('group_by', state.groupBy);
  }
  if (state.page > 1) p.set('page', String(state.page));
  if (state.pageSize !== 20) p.set('page_size', String(state.pageSize));
  if (state.mode && state.mode !== 'dashboard') p.set('mode', state.mode);

  return p.toString();
}

/** Build a default empty state. */
export function defaultUrlState(): UrlState {
  return {
    filters: {},
    sort: [],
    groupBy: 'supplier',
    page: 1,
    pageSize: 20,
    mode: 'dashboard',
  };
}

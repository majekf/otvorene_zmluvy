/**
 * AccordionContracts Component
 *
 * Lazily fetches and renders a contracts table for a single accordion
 * group.  Mounted only when the parent CategoryAccordion row is
 * expanded, so the API call fires on-demand.
 *
 * Props carry the parent page's filter state + the active group-by
 * field so the component can build a merged filter that narrows to
 * the specific group value.
 *
 * When groupBy is 'red_flag_type', contract data is sourced client-side
 * from the RedFlagStore because the backend has no red flag knowledge.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { FilterState, SortSpec, PaginatedContracts, GroupByField, Contract } from '../types';
import { fetchContracts } from '../api';
import { useRedFlagContext } from '../RedFlagStore';
import ContractsTable from './ContractsTable';
import Pagination from './Pagination';
import { TableSkeleton } from './LoadingSkeleton';

interface AccordionContractsProps {
  /** Parent page's active filters. */
  filters: FilterState;
  /** Which field the aggregation is grouped by. */
  groupBy: GroupByField | string;
  /** The specific group value to filter on (e.g. "construction"). */
  groupValue: string;
}

/**
 * Map a groupBy field + value to a merged FilterState that narrows to
 * that group.
 */
function mergeGroupFilter(
  base: FilterState,
  groupBy: GroupByField | string,
  value: string,
): FilterState {
  const merged = { ...base };
  switch (groupBy) {
    case 'category':
      merged.scanned_service_types = [value];
      merged.scanned_service_subtypes = undefined;
      break;
    case 'scanned_service_subtype':
      merged.scanned_service_subtypes = [value];
      break;
    case 'supplier':
      merged.vendors = [value];
      merged.vendor_icos = undefined;
      break;
    case 'buyer':
      merged.institutions = [value];
      merged.institution_icos = undefined;
      break;
    case 'award_type':
      merged.award_types = [value];
      break;
    case 'month': {
      // value is like "2024-03" — set date_from/date_to to span the month
      const [y, m] = value.split('-').map(Number);
      if (y && m) {
        const first = `${y}-${String(m).padStart(2, '0')}-01`;
        // Last day: month+1 day 0
        const last = new Date(y, m, 0);
        const lastStr = `${last.getFullYear()}-${String(last.getMonth() + 1).padStart(2, '0')}-${String(last.getDate()).padStart(2, '0')}`;
        merged.date_from = first;
        merged.date_to = lastStr;
      }
      break;
    }
    case 'red_flag_type':
      merged.red_flag_types = [value];
      break;
  }
  return merged;
}

export default function AccordionContracts({
  filters,
  groupBy,
  groupValue,
}: AccordionContractsProps) {
  const navigate = useNavigate();
  const { getFlagsForDatasets, datasetNames: rfDatasetNames } = useRedFlagContext();
  const [sort, setSort] = useState<SortSpec>([]);
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [data, setData] = useState<PaginatedContracts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mergedFilters = mergeGroupFilter(filters, groupBy, groupValue);

  // For red_flag_type grouping, build contract data client-side from RedFlagStore
  const redFlagContracts = useMemo<Contract[] | null>(() => {
    if (groupBy !== 'red_flag_type') return null;
    const selectedDatasets = filters.red_flag_datasets ?? rfDatasetNames;
    let flags = getFlagsForDatasets(selectedDatasets);
    // Filter to the specific red_flag_type (groupValue is the red_flag_name display label)
    flags = flags.filter((f) => f.red_flag_name === groupValue || f.red_flag_type === groupValue);
    // Convert flags to Contract objects for the table
    return flags.map((f) => ({
      contract_id: f.contract_id,
      contract_title: f.contract_title || null,
      contract_number: null,
      contract_number_detail: null,
      contract_type: null,
      buyer: f.institution || null,
      buyer_detail: null,
      supplier: f.vendor || null,
      supplier_detail: null,
      price_numeric_eur: f.price_numeric_eur,
      price_raw: null,
      published_date: f.date_published || null,
      published_day: null,
      published_month: null,
      published_year: null,
      category: f.category,
      award_type: f.award_type,
      pdf_text_summary: '',
      contract_url: null,
      ico_buyer: f.ico_buyer || null,
      ico_supplier: f.ico_supplier || null,
      date_published: f.date_published || null,
      date_concluded: null,
      date_effective: null,
      date_valid_until: null,
      pdf_url: null,
      pdf_urls: null,
      pdf_text: null,
      scraped_at: null,
      rezort: null,
      scanned_suggested_title: f.contract_title || null,
      // Attach red flag info for display
      _red_flag_type: f.red_flag_name || f.red_flag_type,
      _red_flag_description: f.description,
      _red_flag_severity: f.severity,
    } as Contract & { _red_flag_type?: string; _red_flag_description?: string; _red_flag_severity?: string }));
  }, [groupBy, groupValue, filters.red_flag_datasets, rfDatasetNames, getFlagsForDatasets]);

  useEffect(() => {
    // For red_flag_type, use client-side data
    if (groupBy === 'red_flag_type' && redFlagContracts !== null) {
      setData({
        total: redFlagContracts.length,
        page: 1,
        page_size: redFlagContracts.length,
        total_pages: 1,
        contracts: redFlagContracts,
      });
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    fetchContracts(mergedFilters, page, pageSize, sort)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load group contracts.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, sort, groupBy, groupValue, JSON.stringify(filters), redFlagContracts]);

  const handleSortChange = useCallback((s: SortSpec) => {
    setSort(s);
    setPage(1);
  }, []);

  const handleRowClick = useCallback(
    (id: string) => navigate(`/contract/${id}`),
    [navigate],
  );

  if (loading) {
    return <div data-testid={`accordion-loading-${groupValue}`}><TableSkeleton rows={3} /></div>;
  }

  if (error) {
    return (
      <div data-testid={`accordion-error-${groupValue}`} className="text-sm text-red-600 py-2">
        {error}
      </div>
    );
  }

  if (!data || data.contracts.length === 0) {
    return (
      <div data-testid={`accordion-empty-${groupValue}`} className="text-sm text-slate-400 py-2">
        No contracts in this group.
      </div>
    );
  }

  return (
    <div data-testid={`accordion-contracts-${groupValue}`}>
      <ContractsTable
        contracts={data.contracts}
        sort={sort}
        onSortChange={handleSortChange}
        onRowClick={handleRowClick}
        showRedFlagColumn={groupBy === 'red_flag_type'}
      />
      {data.total > pageSize && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}

export { mergeGroupFilter };

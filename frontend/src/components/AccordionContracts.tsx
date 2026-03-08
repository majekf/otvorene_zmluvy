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
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { FilterState, SortSpec, PaginatedContracts, GroupByField } from '../types';
import { fetchContracts } from '../api';
import ContractsTable from './ContractsTable';
import Pagination from './Pagination';
import { TableSkeleton } from './LoadingSkeleton';

interface AccordionContractsProps {
  /** Parent page's active filters. */
  filters: FilterState;
  /** Which field the aggregation is grouped by. */
  groupBy: GroupByField;
  /** The specific group value to filter on (e.g. "construction"). */
  groupValue: string;
}

/**
 * Map a groupBy field + value to a merged FilterState that narrows to
 * that group.
 */
function mergeGroupFilter(
  base: FilterState,
  groupBy: GroupByField,
  value: string,
): FilterState {
  const merged = { ...base };
  switch (groupBy) {
    case 'category':
      merged.scanned_service_types = [value];
      merged.scanned_service_subtypes = undefined;
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
  }
  return merged;
}

export default function AccordionContracts({
  filters,
  groupBy,
  groupValue,
}: AccordionContractsProps) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<SortSpec>([]);
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [data, setData] = useState<PaginatedContracts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mergedFilters = mergeGroupFilter(filters, groupBy, groupValue);

  useEffect(() => {
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
  }, [page, sort, groupBy, groupValue, JSON.stringify(filters)]);

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

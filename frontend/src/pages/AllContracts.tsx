/**
 * AllContracts Page
 *
 * Minimalistic contracts browser: FilterBar on top, then the full
 * ContractsTable with pagination underneath. All table features are
 * preserved (multi-column sort, clickable rows, severity badges,
 * URL-state sync, WorkspaceToolbar export/share).
 *
 * Deliberately omits the visualisation layer (treemap/bar chart),
 * summary strip, group-by control, accordion breakdown, and rule
 * builder present in the Dashboard page.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import type { SortSpec, PaginatedContracts } from '../types';
import { fetchContracts } from '../api';
import { parseUrlState, encodeUrlState } from '../url-state';
import { useFilterContext } from '../FilterContext';
import FilterBar from '../components/FilterBar';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import ContractsTable from '../components/ContractsTable';
import Pagination from '../components/Pagination';
import { TableSkeleton } from '../components/LoadingSkeleton';

export default function AllContracts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const urlState = useMemo(() => parseUrlState(searchParams.toString()), [searchParams]);

  const {
    filters,
    setFilters,
    institutions: distinctInstitutions,
    categories: distinctCategories,
    scannedServiceTypes,
    scannedServiceSubtypes,
    vendors: distinctVendors,
    institutionIcos,
    vendorIcos,
    institutionIcoMap,
    vendorIcoMap,
    institutionCounts,
    vendorCounts,
    institutionIcoCounts,
    vendorIcoCounts,
    categoryCounts,
    scannedServiceTypeCounts,
    scannedServiceSubtypeCounts,
    awardTypes: distinctAwardTypes,
    optionsLoaded,
  } = useFilterContext();

  const [sort, setSort] = useState<SortSpec>(urlState.sort);
  const [page, setPage] = useState(urlState.page);
  const [pageSize] = useState(urlState.pageSize);

  const [contracts, setContracts] = useState<PaginatedContracts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sync state → URL
  useEffect(() => {
    const params = encodeUrlState({
      filters,
      sort,
      groupBy: 'category',
      page,
      pageSize,
      mode: 'contracts',
    });
    setSearchParams(params, { replace: true });
  }, [filters, sort, page, pageSize, setSearchParams]);

  // Fetch contracts when filters / sort / page change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchContracts(filters, page, pageSize, sort)
      .then((res) => {
        if (!cancelled) {
          setContracts(res);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load contracts. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, sort, page, pageSize]);

  const handleFilterChange = useCallback(
    (newFilters: typeof filters) => {
      setFilters(newFilters);
      setPage(1);
    },
    [setFilters],
  );

  const handleSortChange = useCallback((newSort: SortSpec) => {
    setSort(newSort);
    setPage(1);
  }, []);

  const handleRowClick = useCallback(
    (contractId: string) => navigate(`/contract/${contractId}`),
    [navigate],
  );

  return (
    <div data-testid="all-contracts" className="space-y-6 animate-fade-in">
      {/* Filters */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        institutions={distinctInstitutions}
        categories={distinctCategories}
        vendors={distinctVendors}
        institutionIcos={institutionIcos}
        vendorIcos={vendorIcos}
        institutionIcoMap={institutionIcoMap}
        vendorIcoMap={vendorIcoMap}
        institutionCounts={institutionCounts}
        vendorCounts={vendorCounts}
        institutionIcoCounts={institutionIcoCounts}
        vendorIcoCounts={vendorIcoCounts}
        categoryCounts={categoryCounts}
        scannedServiceTypes={scannedServiceTypes}
        scannedServiceSubtypes={scannedServiceSubtypes}
        scannedServiceTypeCounts={scannedServiceTypeCounts}
        scannedServiceSubtypeCounts={scannedServiceSubtypeCounts}
        awardTypes={distinctAwardTypes}
        optionsLoaded={optionsLoaded}
      />

      {/* Workspace toolbar: Share, Save, Export CSV, Export PDF */}
      <WorkspaceToolbar
        filters={filters}
        sort={sort}
        mode="contracts"
        page={page}
      />

      {/* Contracts table */}
      {!loading && contracts && (
        <>
          <ContractsTable
            contracts={contracts.contracts}
            sort={sort}
            onSortChange={handleSortChange}
            onRowClick={handleRowClick}
            contractSeverities={{}}
            variant="all-contracts"
          />
          <Pagination
            page={contracts.page}
            pageSize={contracts.page_size}
            total={contracts.total}
            onPageChange={setPage}
          />
        </>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div data-testid="all-contracts-loading">
          <TableSkeleton rows={10} />
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div
          role="alert"
          data-testid="all-contracts-error"
          className="glass-card bg-red-50/80 border-red-200 p-5 text-sm text-red-700 flex items-center gap-3"
        >
          <svg
            className="w-5 h-5 text-red-500 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="2"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
          <span>{error}</span>
          <button
            className="ml-auto btn-secondary text-xs text-red-600 border-red-200 hover:bg-red-50"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      )}
    </div>
  );
}

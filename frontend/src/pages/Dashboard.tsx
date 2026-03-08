/**
 * Dashboard Page (Home)
 *
 * Landing page showing overview: filter bar, treemap/bar chart,
 * and accordion breakdown with inline contract drill-down.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { SortSpec, GroupByField, AggregationsResponse, TreemapNode } from '../types';
import { fetchAggregations, fetchTreemap } from '../api';
import { parseUrlState, encodeUrlState } from '../url-state';
import { useFilterContext } from '../FilterContext';
import FilterBar from '../components/FilterBar';
import GroupByControl from '../components/GroupByControl';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import TreemapChart from '../components/TreemapChart';
import BarChart from '../components/BarChart';
import CategoryAccordion from '../components/CategoryAccordion';
import AccordionContracts from '../components/AccordionContracts';
import RulePanel from '../components/RulePanel';
import ConditionBuilder from '../components/ConditionBuilder';
import { formatEur } from '../utils';
import { TableSkeleton, ChartSkeleton, SummarySkeleton } from '../components/LoadingSkeleton';

type VizMode = 'treemap' | 'bar';

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse URL state (for sort / groupBy / page only – filters come from context)
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
  const [sort] = useState<SortSpec>(urlState.sort);
  const [groupBy, setGroupBy] = useState<GroupByField>(urlState.groupBy);
  const [page] = useState(urlState.page);
  const [pageSize] = useState(urlState.pageSize);
  const [vizMode, setVizMode] = useState<VizMode>('treemap');

  // Data state
  const [aggregations, setAggregations] = useState<AggregationsResponse | null>(null);
  const [treemapData, setTreemapData] = useState<TreemapNode | null>(null);
  const [loading, setLoading] = useState(true);

  const [showRules, setShowRules] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state → URL
  useEffect(() => {
    const params = encodeUrlState({ filters, sort, groupBy, page, pageSize, mode: 'dashboard' });
    setSearchParams(params, { replace: true });
  }, [filters, sort, groupBy, page, pageSize, setSearchParams]);

  // Fetch data when filters / groupBy change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      fetchAggregations(filters, groupBy),
      fetchTreemap(filters, groupBy),
    ])
      .then(([aggRes, treemapRes]) => {
        if (cancelled) return;
        setAggregations(aggRes);
        setTreemapData(treemapRes);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load data. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, groupBy]);

  const handleFilterChange = useCallback((newFilters: typeof filters) => {
    setFilters(newFilters);
  }, [setFilters]);

  const applyGroupFilter = useCallback((groupValue: string) => {
    if (!groupValue) return;
    if (groupBy === 'buyer') {
      setFilters({ ...filters, institutions: [groupValue], institution_icos: undefined });
      return;
    }
    if (groupBy === 'supplier') {
      setFilters({ ...filters, vendors: [groupValue], vendor_icos: undefined });
      return;
    }
    if (groupBy === 'award_type') {
      setFilters({ ...filters, award_types: [groupValue] });
      return;
    }
    if (groupBy === 'category') {
      setFilters({
        ...filters,
        scanned_service_types: [groupValue],
        scanned_service_subtypes: undefined,
      });
      return;
    }
    if (groupBy === 'month' && /^\d{4}-\d{2}$/.test(groupValue)) {
      const [y, m] = groupValue.split('-').map(Number);
      const endDay = new Date(y, m, 0).getDate();
      setFilters({
        ...filters,
        date_from: `${groupValue}-01`,
        date_to: `${groupValue}-${String(endDay).padStart(2, '0')}`,
      });
    }
  }, [filters, groupBy, setFilters]);

  return (
    <div data-testid="dashboard" className="space-y-8 animate-fade-in">
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

      {/* Summary strip */}
      {aggregations && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4" data-testid="summary-strip">
          <div className="stat-card">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Contracts</div>
            <div className="text-2xl font-bold text-slate-800 mt-1 tabular-nums">{aggregations.summary.contract_count.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Total Spend</div>
            <div className="text-2xl font-bold text-slate-800 mt-1 tabular-nums">{formatEur(aggregations.summary.total_spend)}</div>
          </div>
          <div className="stat-card">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Avg Value</div>
            <div className="text-2xl font-bold text-slate-800 mt-1 tabular-nums">{formatEur(aggregations.summary.avg_value)}</div>
          </div>
        </div>
      )}

      {/* Workspace toolbar: Share, Save, Export CSV, Export PDF */}
      <WorkspaceToolbar
        filters={filters}
        sort={sort}
        mode="dashboard"
        groupBy={groupBy}
        page={page}
      />

      {/* Group-by + viz toggle */}
      <div className="flex flex-wrap items-center gap-4">
        <GroupByControl value={groupBy} onChange={setGroupBy} />
        <div className="toggle-group">
          <button
            className={vizMode === 'treemap' ? 'active' : ''}
            onClick={() => setVizMode('treemap')}
          >
            Treemap
          </button>
          <button
            className={vizMode === 'bar' ? 'active' : ''}
            onClick={() => setVizMode('bar')}
          >
            Bar
          </button>
        </div>
      </div>

      {/* Visualization */}
      <div className="chart-container">
      {vizMode === 'treemap' ? (
        <TreemapChart data={treemapData} width={900} height={400} onDrillDown={applyGroupFilter} />
      ) : aggregations ? (
        <BarChart data={aggregations.results} metric="total_spend" onSelectGroup={applyGroupFilter} />
      ) : null}
      </div>

      {/* Accordion breakdown */}
      {aggregations && (
        <CategoryAccordion
          groups={aggregations.results}
          renderExpanded={(groupValue) => (
            <AccordionContracts
              filters={filters}
              groupBy={groupBy}
              groupValue={groupValue}
            />
          )}
        />
      )}

      {/* Rule Builder (Phase 4) */}
      <div className="pt-6">
        <button
          className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-primary-600 transition-colors mb-4"
          onClick={() => setShowRules(!showRules)}
          data-testid="toggle-rules"
        >
          <svg className={`w-4 h-4 transition-transform duration-200 ${showRules ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
          {showRules ? 'Hide Pattern Detection' : 'Show Pattern Detection'}
        </button>
        {showRules && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in">
            <div className="glass-card p-5">
              <RulePanel filters={filters} />
            </div>
            <div className="glass-card p-5">
              <ConditionBuilder filters={filters} />
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div className="text-center text-slate-400 text-sm py-6" data-testid="loading-indicator">
          <SummarySkeleton />
          <div className="mt-4"><ChartSkeleton /></div>
          <div className="mt-4"><TableSkeleton rows={5} /></div>
        </div>
      )}

      {error && !loading && (
        <div role="alert" data-testid="dashboard-error" className="glass-card bg-red-50/80 border-red-200 p-5 text-sm text-red-700 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
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

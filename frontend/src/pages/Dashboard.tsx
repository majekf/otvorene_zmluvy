/**
 * Dashboard Page (Home)
 *
 * Landing page showing overview: filter bar, treemap/bar chart,
 * and accordion breakdown with inline contract drill-down.
 * Includes red flag integration for charts, grouping, and tables.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { SortSpec, GroupByField, AggregationsResponse, TreemapNode } from '../types';
import { fetchAggregations, fetchTreemap } from '../api';
import { parseUrlState, encodeUrlState } from '../url-state';
import { useFilterContext } from '../FilterContext';
import { useRedFlagContext, severityEmoji, severityBgColor } from '../RedFlagStore';
import FilterBar from '../components/FilterBar';
import GroupByControl from '../components/GroupByControl';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import TreemapChart from '../components/TreemapChart';
import BarChart from '../components/BarChart';
import CategoryAccordion from '../components/CategoryAccordion';
import AccordionContracts from '../components/AccordionContracts';
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
  const {
    datasetNames: rfDatasetNames,
    allFlagTypes: rfFlagTypes,
    contractFlagMap,
    getFlagsForDatasets,
    vendorFlagCounts: getVendorFlagCounts,
    institutionFlagCounts: getInstitutionFlagCounts,
  } = useRedFlagContext();

  // Red flag computed data for the selected datasets
  const selectedRfDatasets = filters.red_flag_datasets ?? rfDatasetNames;
  const rfContractMap = useMemo(
    () => contractFlagMap(selectedRfDatasets),
    [contractFlagMap, selectedRfDatasets],
  );
  const rfVendorCounts = useMemo(
    () => getVendorFlagCounts(selectedRfDatasets),
    [getVendorFlagCounts, selectedRfDatasets],
  );
  const rfInstitutionCounts = useMemo(
    () => getInstitutionFlagCounts(selectedRfDatasets),
    [getInstitutionFlagCounts, selectedRfDatasets],
  );

  const [sort] = useState<SortSpec>(urlState.sort);
  const [groupBy, setGroupBy] = useState<GroupByField>(urlState.groupBy);
  const [page] = useState(urlState.page);
  const [pageSize] = useState(urlState.pageSize);
  const [vizMode, setVizMode] = useState<VizMode>('treemap');

  // Data state
  const [aggregations, setAggregations] = useState<AggregationsResponse | null>(null);
  const [treemapData, setTreemapData] = useState<TreemapNode | null>(null);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  // When groupBy is "category" and exactly one category is selected,
  // drill into service subtypes for the treemap and accordion.
  // Note: the "Category" grouping maps to scanned_service_types in the filter model.
  const effectiveGroupBy = useMemo<string>(() => {
    if (
      groupBy === 'category' &&
      filters.scanned_service_types?.length === 1
    ) {
      return 'scanned_service_subtype';
    }
    return groupBy;
  }, [groupBy, filters.scanned_service_types]);

  // Build red flag info per aggregation group (for accordion badges)
  const redFlagGroupInfo = useMemo(() => {
    if (rfContractMap.size === 0 || !aggregations) return {};
    // We need to map group values to red flag counts and types
    // This is a client-side enrichment - we count flags for contracts under each group
    const info: Record<string, { count: number; types: { type: string; severity: string }[] }> = {};
    // For now, build from the flags directly
    const allFlags = Array.from(rfContractMap.values()).flat();
    for (const flag of allFlags) {
      // Determine which group this flag belongs to based on effectiveGroupBy
      let groupKey = '';
      if (effectiveGroupBy === 'supplier' || effectiveGroupBy === 'vendor') {
        groupKey = flag.vendor;
      } else if (effectiveGroupBy === 'buyer' || effectiveGroupBy === 'institution') {
        groupKey = flag.institution;
      } else if (effectiveGroupBy === 'category' || effectiveGroupBy === 'scanned_service_subtype') {
        groupKey = flag.category;
      } else if (effectiveGroupBy === 'award_type') {
        groupKey = flag.award_type;
      } else if (effectiveGroupBy === 'red_flag_type') {
        groupKey = flag.red_flag_type;
      }
      if (!groupKey) continue;
      if (!info[groupKey]) info[groupKey] = { count: 0, types: [] };
      info[groupKey].count++;
      if (!info[groupKey].types.find((t) => t.type === flag.red_flag_type)) {
        info[groupKey].types.push({ type: flag.red_flag_name, severity: flag.severity });
      }
    }
    return info;
  }, [rfContractMap, aggregations, effectiveGroupBy]);

  // Sync state → URL
  useEffect(() => {
    const params = encodeUrlState({ filters, sort, groupBy, page, pageSize, mode: 'dashboard' });
    setSearchParams(params, { replace: true });
  }, [filters, sort, groupBy, page, pageSize, setSearchParams]);

  // Fetch data when filters / groupBy change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // When groupBy is red_flag_type, build aggregation + treemap client-side
    // from the RedFlagStore data, because the backend doesn't know about red flags.
    if (effectiveGroupBy === 'red_flag_type') {
      const flags = getFlagsForDatasets(selectedRfDatasets);

      // Group flags by red_flag_type (use red_flag_name as display label)
      const groups = new Map<string, { name: string; spend: number; count: number; maxVal: number }>();
      for (const flag of flags) {
        const key = flag.red_flag_type;
        if (!groups.has(key)) {
          groups.set(key, { name: flag.red_flag_name || key, spend: 0, count: 0, maxVal: 0 });
        }
        const g = groups.get(key)!;
        const val = flag.price_numeric_eur ?? 0;
        g.spend += val;
        g.count += 1;
        if (val > g.maxVal) g.maxVal = val;
      }

      const results = Array.from(groups.entries()).map(([key, g]) => ({
        group_key: key,
        group_value: g.name,
        contract_count: g.count,
        total_spend: g.spend,
        avg_value: g.count > 0 ? g.spend / g.count : 0,
        max_value: g.maxVal,
      }));

      const totalSpend = results.reduce((s, r) => s + r.total_spend, 0);
      const totalCount = results.reduce((s, r) => s + r.contract_count, 0);

      const aggRes: AggregationsResponse = {
        group_by: 'red_flag_type',
        results,
        summary: {
          total_spend: totalSpend,
          contract_count: totalCount,
          avg_value: totalCount > 0 ? totalSpend / totalCount : 0,
          max_value: Math.max(0, ...results.map((r) => r.max_value)),
        },
      };

      const treemapRes: TreemapNode = {
        name: 'Red Flag Types',
        value: totalSpend,
        children: results.map((r) => ({
          name: r.group_value,
          value: r.total_spend,
          contract_count: r.contract_count,
        })),
      };

      if (!cancelled) {
        setAggregations(aggRes);
        setTreemapData(treemapRes);
        setError(flags.length === 0 ? null : null);
        setLoading(false);
      }
      return () => { cancelled = true; };
    }

    Promise.all([
      fetchAggregations(filters, effectiveGroupBy as GroupByField),
      fetchTreemap(filters, effectiveGroupBy as GroupByField),
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
  }, [filters, effectiveGroupBy, getFlagsForDatasets, selectedRfDatasets]);

  const handleFilterChange = useCallback((newFilters: typeof filters) => {
    setFilters(newFilters);
  }, [setFilters]);

  const applyGroupFilter = useCallback((groupValue: string) => {
    if (!groupValue) return;
    if (effectiveGroupBy === 'scanned_service_subtype') {
      setFilters({
        ...filters,
        scanned_service_subtypes: [groupValue],
      });
      return;
    }
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
      return;
    }
    if (groupBy === 'red_flag_type') {
      // groupValue is the red_flag_name (display label); find the matching red_flag_type id
      const flags = getFlagsForDatasets(selectedRfDatasets);
      const match = flags.find((f) => f.red_flag_name === groupValue || f.red_flag_type === groupValue);
      const flagType = match?.red_flag_type ?? groupValue;
      setFilters({ ...filters, red_flag_types: [flagType] });
    }
  }, [filters, groupBy, effectiveGroupBy, setFilters, getFlagsForDatasets, selectedRfDatasets]);

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
        redFlagDatasetNames={rfDatasetNames}
        redFlagTypes={rfFlagTypes}
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
          redFlagInfo={redFlagGroupInfo}
          renderExpanded={(groupValue) => (
            <AccordionContracts
              filters={filters}
              groupBy={effectiveGroupBy as GroupByField}
              groupValue={groupValue}
            />
          )}
        />
      )}

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

/**
 * TimeView Page (Phase 6)
 *
 * Compare in Time mode: line/area chart with granularity toggle,
 * multi-metric selection, and optional overlay markers for
 * election/budget dates.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { TrendPoint, OverlayDate } from '../types';
import { fetchTrends } from '../api';
import FilterBar from '../components/FilterBar';
import { useFilterContext } from '../FilterContext';
import { formatEur, formatCompact } from '../utils';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import { ChartSkeleton } from '../components/LoadingSkeleton';

type Granularity = 'month' | 'quarter' | 'year';
type ChartType = 'line' | 'area';

const METRIC_OPTIONS = [
  { id: 'total_spend', label: 'Total Spend' },
  { id: 'contract_count', label: 'Contract Count' },
  { id: 'avg_value', label: 'Avg Value' },
];

const METRIC_COLORS: Record<string, string> = {
  total_spend: '#2563eb',
  contract_count: '#16a34a',
  avg_value: '#f59e0b',
};

export default function TimeView() {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    filters,
    setFilters,
    institutions,
    categories,
    scannedServiceTypes,
    scannedServiceSubtypes,
    vendors,
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
    awardTypes,
    optionsLoaded,
  } = useFilterContext();
  const [granularity, setGranularity] = useState<Granularity>(
    (searchParams.get('granularity') as Granularity) || 'month',
  );
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(
    searchParams.get('metrics')?.split(',') || ['total_spend'],
  );
  const [chartType, setChartType] = useState<ChartType>('line');
  const [showOverlays, setShowOverlays] = useState(searchParams.get('overlay') === 'true');
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [overlays, setOverlays] = useState<OverlayDate[]>([]);
  const [loading, setLoading] = useState(true);

  // Sync state → URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (granularity !== 'month') params.set('granularity', granularity);
    if (selectedMetrics.length && selectedMetrics[0] !== 'total_spend') {
      params.set('metrics', selectedMetrics.join(','));
    }
    if (showOverlays) params.set('overlay', 'true');
    // Merge filters into URL
    if (filters.institutions?.length) params.set('institutions', filters.institutions.join('|'));
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    if (filters.categories?.length) params.set('categories', filters.categories.join('|'));
    if (filters.scanned_service_types?.length) params.set('scanned_service_types', filters.scanned_service_types.join('|'));
    if (filters.scanned_service_subtypes?.length) params.set('scanned_service_subtypes', filters.scanned_service_subtypes.join('|'));
    if (filters.vendors?.length) params.set('vendors', filters.vendors.join('|'));
    if (filters.institution_icos?.length) params.set('institution_icos', filters.institution_icos.join('|'));
    if (filters.vendor_icos?.length) params.set('vendor_icos', filters.vendor_icos.join('|'));
    setSearchParams(params, { replace: true });
  }, [granularity, selectedMetrics, showOverlays, filters, setSearchParams]);

  // Fetch trend data
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // Use the primary metric for the single-metric endpoint
    const primaryMetric = selectedMetrics[0] || 'total_spend';

    fetchTrends(filters, granularity, primaryMetric, showOverlays)
      .then((res) => {
        if (cancelled) return;
        setTrendData(res.data);
        setOverlays(res.overlays || []);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [filters, granularity, selectedMetrics, showOverlays]);

  const handleFilterChange = useCallback((f: Parameters<typeof setFilters>[0]) => setFilters(f), [setFilters]);

  const toggleMetric = useCallback(
    (metricId: string) => {
      setSelectedMetrics((prev) =>
        prev.includes(metricId)
          ? prev.filter((m) => m !== metricId) || ['total_spend']
          : [...prev, metricId],
      );
    },
    [],
  );

  // Convert overlays into period keys that match the chart X axis
  const overlayPeriods = useMemo(() => {
    return overlays.map((o) => {
      const date = o.date;
      let period = date;
      if (granularity === 'month') {
        period = date.slice(0, 7); // YYYY-MM
      } else if (granularity === 'quarter') {
        const month = parseInt(date.slice(5, 7), 10);
        const q = Math.ceil(month / 3);
        period = `${date.slice(0, 4)}-Q${q}`;
      } else if (granularity === 'year') {
        period = date.slice(0, 4);
      }
      return { ...o, period };
    });
  }, [overlays, granularity]);

  // Determine formatter based on metric
  const formatValue = (metricId: string) => {
    if (metricId === 'contract_count') return (v: number) => String(Math.round(v));
    return (v: number) => formatCompact(v);
  };

  const ChartComponent = chartType === 'area' ? AreaChart : LineChart;

  return (
    <div data-testid="time-view" className="space-y-6 animate-fade-in">
      <div>
        <h1 className="page-title">Compare in Time</h1>
        <p className="text-sm text-slate-500 mt-1">
          Explore spending trends over time with different granularities and overlay markers.
        </p>
      </div>

      <WorkspaceToolbar filters={filters} mode="time" />

      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        institutions={institutions}
        categories={categories}
        vendors={vendors}
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
        awardTypes={awardTypes}
        optionsLoaded={optionsLoaded}
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Granularity */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Granularity:</span>
          <div className="toggle-group">
            {(['month', 'quarter', 'year'] as Granularity[]).map((g) => (
              <button
                key={g}
                data-testid={`granularity-${g}`}
                className={granularity === g ? 'active' : ''}
                onClick={() => setGranularity(g)}
              >
                {g.charAt(0).toUpperCase() + g.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Chart type */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Chart:</span>
          <div className="toggle-group">
            <button
              className={chartType === 'line' ? 'active' : ''}
              onClick={() => setChartType('line')}
            >
              Line
            </button>
            <button
              className={chartType === 'area' ? 'active' : ''}
              onClick={() => setChartType('area')}
            >
              Area
            </button>
          </div>
        </div>

        {/* Metrics */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Metric:</span>
          {METRIC_OPTIONS.map((m) => (
            <button
              key={m.id}
              data-testid={`metric-${m.id}`}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-all font-medium ${
                selectedMetrics.includes(m.id)
                  ? 'bg-primary-50 border-primary-400 text-primary-700 shadow-sm'
                  : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300'
              }`}
              onClick={() => toggleMetric(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Overlay toggle */}
        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
          <input
            type="checkbox"
            data-testid="overlay-toggle"
            checked={showOverlays}
            onChange={(e) => setShowOverlays(e.target.checked)}
            className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
          />
          Show event overlays
        </label>
      </div>

      {/* Chart */}
      {loading ? (
        <div data-testid="time-loading"><ChartSkeleton /></div>
      ) : trendData.length === 0 ? (
        <p className="text-slate-400 text-sm" data-testid="time-empty">No trend data available for the current filters.</p>
      ) : (
        <div data-testid="time-chart" className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <ChartComponent data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis
                tickFormatter={(v: number) => formatValue(selectedMetrics[0])(v)}
                tick={{ fontSize: 11 }}
                stroke="#94a3b8"
              />
              <Tooltip
                formatter={(v: number | undefined, name?: string) => {
                  if (typeof v !== 'number') return '';
                  const isCount = name === 'contract_count' || name === 'count';
                  return isCount ? String(Math.round(v)) : formatEur(v);
                }}
                contentStyle={{ borderRadius: '0.75rem', border: '1px solid #e2e8f0' }}
              />
              <Legend />

              {/* Overlay reference lines */}
              {showOverlays &&
                overlayPeriods.map((o) => (
                  <ReferenceLine
                    key={o.date}
                    x={o.period}
                    stroke="#ef4444"
                    strokeDasharray="5 3"
                    label={{ value: o.label, position: 'top', fontSize: 10, fill: '#ef4444' }}
                  />
                ))}

              {/* Metric lines/areas */}
              {selectedMetrics.map((metricId) =>
                chartType === 'area' ? (
                  <Area
                    key={metricId}
                    type="monotone"
                    dataKey="value"
                    stroke={METRIC_COLORS[metricId] || '#2563eb'}
                    fill={`${METRIC_COLORS[metricId] || '#2563eb'}40`}
                    strokeWidth={2}
                    name={METRIC_OPTIONS.find((m) => m.id === metricId)?.label || metricId}
                  />
                ) : (
                  <Line
                    key={metricId}
                    type="monotone"
                    dataKey="value"
                    stroke={METRIC_COLORS[metricId] || '#2563eb'}
                    strokeWidth={2}
                    dot={trendData.length < 30}
                    name={METRIC_OPTIONS.find((m) => m.id === metricId)?.label || metricId}
                  />
                ),
              )}
            </ChartComponent>
          </ResponsiveContainer>
        </div>
      )}

      {/* Summary stats */}
      {trendData.length > 0 && (
        <div className="grid grid-cols-3 gap-4" data-testid="time-summary">
          <div className="stat-card">
            <div className="w-8 h-1 rounded-full bg-gradient-to-r from-primary-500 to-primary-600 mb-3" />
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Periods</div>
            <div className="text-xl font-bold text-slate-800 mt-1 tabular-nums">{trendData.length}</div>
          </div>
          <div className="stat-card">
            <div className="w-8 h-1 rounded-full bg-gradient-to-r from-green-500 to-green-600 mb-3" />
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Total</div>
            <div className="text-xl font-bold text-slate-800 mt-1 tabular-nums">
              {formatEur(trendData.reduce((s, d) => s + (d.value ?? 0), 0))}
            </div>
          </div>
          <div className="stat-card">
            <div className="w-8 h-1 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 mb-3" />
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Peak</div>
            <div className="text-xl font-bold text-slate-800 mt-1 tabular-nums">
              {formatEur(Math.max(...trendData.map((d) => d.value ?? 0)))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

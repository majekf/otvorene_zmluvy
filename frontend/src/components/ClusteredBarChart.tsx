/**
 * ClusteredBarChart Component (Phase 9)
 *
 * Vertical clustered bar chart using Recharts.
 * Shows two bars per group: Contracts vs Subcontractors.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import type { CompareAggregationRow } from '../types';
import { formatEur } from '../utils';

type CompareMetric =
  | 'total_spend'
  | 'contract_count'
  | 'avg_value';

interface ClusteredBarChartProps {
  data: CompareAggregationRow[];
  metric?: CompareMetric;
  labelA?: string;
  labelB?: string;
  onSelectGroup?: (groupValue: string) => void;
}

function contractsKey(metric: CompareMetric): keyof CompareAggregationRow {
  return `contracts_${metric}` as keyof CompareAggregationRow;
}

function subcontractorsKey(metric: CompareMetric): keyof CompareAggregationRow {
  return `subcontractors_${metric}` as keyof CompareAggregationRow;
}

export default function ClusteredBarChart({
  data,
  metric = 'total_spend',
  labelA = 'Contracts',
  labelB = 'Subcontractors',
  onSelectGroup,
}: ClusteredBarChartProps) {
  if (!data.length) {
    return (
      <div data-testid="clustered-bar-chart" className="text-gray-400 text-sm p-4">
        No data for chart
      </div>
    );
  }

  const cKey = contractsKey(metric);
  const sKey = subcontractorsKey(metric);

  const isCount = metric === 'contract_count';
  const formatter = (v: number | undefined) => {
    if (typeof v !== 'number') return '';
    return isCount ? String(v) : formatEur(v);
  };

  const chartData = data.slice(0, 15).map((d) => ({
    name: d.group_value,
    [labelA]: d[cKey] as number,
    [labelB]: d[sKey] as number,
  }));

  return (
    <div data-testid="clustered-bar-chart" className="w-full" style={{ height: Math.max(300, chartData.length * 40) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 140, right: 20, top: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
          <XAxis type="number" tickFormatter={formatter} tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <Tooltip formatter={(v: number | undefined) => formatter(v)} contentStyle={{ borderRadius: '0.75rem', border: '1px solid #e2e8f0' }} />
          <Legend />
          <Bar
            dataKey={labelA}
            fill="#3b82f6"
            radius={[0, 4, 4, 0]}
            cursor={onSelectGroup ? 'pointer' : 'default'}
            onClick={(entry) => {
              if (!onSelectGroup) return;
              const name = (entry as { name?: unknown }).name;
              if (typeof name === 'string' && name) onSelectGroup(name);
            }}
          />
          <Bar
            dataKey={labelB}
            fill="#f97316"
            radius={[0, 4, 4, 0]}
            cursor={onSelectGroup ? 'pointer' : 'default'}
            onClick={(entry) => {
              if (!onSelectGroup) return;
              const name = (entry as { name?: unknown }).name;
              if (typeof name === 'string' && name) onSelectGroup(name);
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

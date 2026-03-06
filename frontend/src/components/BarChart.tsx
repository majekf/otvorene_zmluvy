/**
 * BarChart Component
 *
 * Horizontal bar chart fallback using Recharts.
 * Shows grouped aggregation data when treemap is unsuitable.
 */

import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import type { AggregationResult } from '../types';
import { formatEur } from '../utils';

interface BarChartProps {
  data: AggregationResult[];
  metric?: 'total_spend' | 'contract_count' | 'avg_value';
}

export default function BarChart({ data, metric = 'total_spend' }: BarChartProps) {
  if (!data.length) {
    return <div data-testid="bar-chart" className="text-gray-400 text-sm p-4">No data for chart</div>;
  }

  const chartData = data
    .map((d) => ({
      name: d.group_value,
      value: d[metric],
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div data-testid="bar-chart" className="w-full" style={{ height: Math.max(200, chartData.length * 36) }}>
      <ResponsiveContainer width="100%" height="100%">
        <ReBarChart data={chartData} layout="vertical" margin={{ left: 120, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={(v: number) => formatEur(v)} />
          <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v: number | undefined) => formatEur(v ?? 0)} />
          <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  );
}

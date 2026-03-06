/**
 * Tests for BarChart component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import BarChart from '../components/BarChart';
import type { AggregationResult } from '../types';

const sampleData: AggregationResult[] = [
  { group_key: 'category', group_value: 'IT', contract_count: 10, total_spend: 50000, avg_value: 5000, max_value: 15000 },
  { group_key: 'category', group_value: 'Consulting', contract_count: 5, total_spend: 30000, avg_value: 6000, max_value: 12000 },
];

describe('BarChart', () => {
  it('renders without crashing', () => {
    render(<BarChart data={sampleData} metric="total_spend" />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<BarChart data={[]} metric="total_spend" />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });
});

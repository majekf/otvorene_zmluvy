/**
 * Tests for ClusteredBarChart component (Phase 9)
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ClusteredBarChart from '../components/ClusteredBarChart';
import type { CompareAggregationRow } from '../types';

const sampleData: CompareAggregationRow[] = [
  {
    group_value: 'construction',
    contracts_total_spend: 1200000,
    contracts_contract_count: 5,
    contracts_avg_value: 240000,
    subcontractors_total_spend: 600000,
    subcontractors_contract_count: 3,
    subcontractors_avg_value: 200000,
  },
  {
    group_value: 'IT',
    contracts_total_spend: 500000,
    contracts_contract_count: 3,
    contracts_avg_value: 166667,
    subcontractors_total_spend: 300000,
    subcontractors_contract_count: 2,
    subcontractors_avg_value: 150000,
  },
];

describe('ClusteredBarChart', () => {
  it('renders without crashing', () => {
    render(<ClusteredBarChart data={sampleData} metric="total_spend" />);
    expect(screen.getByTestId('clustered-bar-chart')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<ClusteredBarChart data={[]} metric="total_spend" />);
    expect(screen.getByTestId('clustered-bar-chart')).toBeInTheDocument();
    expect(screen.getByText('No data for chart')).toBeInTheDocument();
  });

  it('renders with contract_count metric', () => {
    render(<ClusteredBarChart data={sampleData} metric="contract_count" />);
    expect(screen.getByTestId('clustered-bar-chart')).toBeInTheDocument();
  });

  it('renders with avg_value metric', () => {
    render(<ClusteredBarChart data={sampleData} metric="avg_value" />);
    expect(screen.getByTestId('clustered-bar-chart')).toBeInTheDocument();
  });

  it('renders with custom labels', () => {
    render(<ClusteredBarChart data={sampleData} labelA="Primary" labelB="Secondary" />);
    expect(screen.getByTestId('clustered-bar-chart')).toBeInTheDocument();
  });
});

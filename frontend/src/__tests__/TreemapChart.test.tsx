/**
 * Tests for TreemapChart component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TreemapChart from '../components/TreemapChart';
import type { TreemapNode } from '../types';

const sampleData: TreemapNode = {
  name: 'root',
  value: 1000,
  children: [
    { name: 'Category A', value: 600, contract_count: 3 },
    { name: 'Category B', value: 400, contract_count: 2 },
  ],
};

describe('TreemapChart', () => {
  it('renders without crashing when data is null', () => {
    render(<TreemapChart data={null} width={400} height={300} />);
    expect(screen.getByTestId('treemap-chart')).toBeInTheDocument();
  });

  it('renders SVG when data is provided', () => {
    const { container } = render(<TreemapChart data={sampleData} width={400} height={300} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('shows empty message for null data', () => {
    render(<TreemapChart data={null} width={400} height={300} />);
    expect(screen.getByText(/no data/i)).toBeInTheDocument();
  });
});

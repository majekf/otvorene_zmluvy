/**
 * Tests for CategoryAccordion component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CategoryAccordion from '../components/CategoryAccordion';
import type { AggregationResult } from '../types';

const groups: AggregationResult[] = [
  { group_key: 'category', group_value: 'Category One', contract_count: 10, total_spend: 50000, avg_value: 5000, max_value: 15000 },
  { group_key: 'category', group_value: 'Category Two', contract_count: 5, total_spend: 30000, avg_value: 6000, max_value: 12000 },
];

describe('CategoryAccordion', () => {
  it('renders all groups', () => {
    render(
      <CategoryAccordion groups={groups} renderExpanded={(gv) => <div>Details for {gv}</div>} />,
    );
    expect(screen.getByTestId('category-accordion')).toBeInTheDocument();
    expect(screen.getByText('Category One')).toBeInTheDocument();
    expect(screen.getByText('Category Two')).toBeInTheDocument();
  });

  it('expands a group on click', () => {
    render(
      <CategoryAccordion groups={groups} renderExpanded={(gv) => <div>Details for {gv}</div>} />,
    );
    const header = screen.getByText('Category One');
    fireEvent.click(header);
    expect(screen.getByText('Details for Category One')).toBeInTheDocument();
  });

  it('collapses a group on second click', () => {
    render(
      <CategoryAccordion groups={groups} renderExpanded={(gv) => <div>Details for {gv}</div>} />,
    );
    const header = screen.getByText('Category One');
    fireEvent.click(header);
    expect(screen.getByText('Details for Category One')).toBeInTheDocument();
    fireEvent.click(header);
    expect(screen.queryByText('Details for Category One')).not.toBeInTheDocument();
  });

  it('supports controlled open state', () => {
    const onToggle = vi.fn();
    render(
      <CategoryAccordion
        groups={groups}
        renderExpanded={(gv) => <div>Details for {gv}</div>}
        openGroups={new Set(['Category One'])}
        onToggle={onToggle}
      />,
    );
    expect(screen.getByText('Details for Category One')).toBeInTheDocument();
    expect(screen.queryByText('Details for Category Two')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Category Two'));
    expect(onToggle).toHaveBeenCalledWith('Category Two');
  });
});

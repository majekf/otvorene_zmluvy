/**
 * Tests for FilterBar component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterBar from '../components/FilterBar';
import type { FilterState } from '../types';

const defaultProps = {
  filters: {} as FilterState,
  onChange: vi.fn(),
  institutions: ['Inst A', 'Inst B'],
  categories: ['cat1', 'cat2'],
  vendors: ['Vendor X'],
  awardTypes: ['direct_award', 'open_tender'],
};

describe('FilterBar', () => {
  it('renders without crashing', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
  });

  it('renders text search input', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-text-search')).toBeInTheDocument();
  });

  it('calls onChange when text search form is submitted', () => {
    const onChange = vi.fn();
    render(<FilterBar {...defaultProps} onChange={onChange} />);
    const input = screen.getByTestId('filter-text-search');
    fireEvent.change(input, { target: { value: 'hello' } });
    // Submit the form by pressing Enter / submitting
    fireEvent.submit(input.closest('form')!);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ text_search: 'hello' }));
  });

  it('renders date range inputs', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-date-from')).toBeInTheDocument();
    expect(screen.getByTestId('filter-date-to')).toBeInTheDocument();
  });

  it('renders institution select', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-institution')).toBeInTheDocument();
  });

  it('renders category select', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-category')).toBeInTheDocument();
  });
});

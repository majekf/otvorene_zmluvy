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
  vendors: ['Vendor X', 'Vendor Y'],
  institutionIcos: ['11111111', '22222222'],
  vendorIcos: ['11111111', '22222222'],
  institutionIcoMap: { 'Inst A': '11111111', 'Inst B': '22222222' },
  vendorIcoMap: { 'Vendor X': '11111111', 'Vendor Y': '22222222' },
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

  it('renders institution slicer', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-institution-trigger')).toBeInTheDocument();
    expect(screen.queryByTestId('filter-institution-dropdown')).not.toBeInTheDocument();
  });

  it('renders vendor and ICO slicers', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-vendor-trigger')).toBeInTheDocument();
    expect(screen.getByTestId('filter-institution-ico-trigger')).toBeInTheDocument();
    expect(screen.getByTestId('filter-vendor-ico-trigger')).toBeInTheDocument();
    expect(screen.getByTestId('filter-category-trigger')).toBeInTheDocument();
  });

  it('sorts institutions alphabetically by default', () => {
    render(<FilterBar {...defaultProps} institutions={['Zebra Office', 'Alpha Office', 'Beta Office']} />);
    fireEvent.click(screen.getByTestId('filter-institution-trigger'));
    const labels = Array.from(screen.getByTestId('filter-institution-list').querySelectorAll('label .flex-1')).map((n) =>
      n.textContent?.trim(),
    );
    expect(labels).toEqual(['Alpha Office', 'Beta Office', 'Zebra Office']);
  });

  it('filters institution list by search input', () => {
    render(<FilterBar {...defaultProps} institutions={['Inst A', 'Inst B', 'City Office']} />);
    fireEvent.click(screen.getByTestId('filter-institution-trigger'));
    const input = screen.getByTestId('filter-institution-search');
    fireEvent.change(input, { target: { value: 'city' } });
    const list = screen.getByTestId('filter-institution-list');

    expect(list).toHaveTextContent('City Office');
    expect(list).not.toHaveTextContent('Inst A');
    expect(list).not.toHaveTextContent('Inst B');
  });

  it('applies institution filter on multi-select checkbox', () => {
    const onChange = vi.fn();
    render(<FilterBar {...defaultProps} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('filter-institution-trigger'));
    const checkbox = screen.getByLabelText(/Inst A/);
    fireEvent.click(checkbox);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ institutions: ['Inst A'] }));
  });

  it('applies vendor filter on multi-select checkbox', () => {
    const onChange = vi.fn();
    render(<FilterBar {...defaultProps} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('filter-vendor-trigger'));
    fireEvent.click(screen.getByLabelText(/Vendor X/));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        vendors: ['Vendor X'],
      }),
    );
  });

  it('applies institution ICO filter on multi-select checkbox', () => {
    const onChange = vi.fn();
    render(<FilterBar {...defaultProps} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('filter-institution-ico-trigger'));
    fireEvent.click(screen.getByLabelText(/11111111/));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        institution_icos: ['11111111'],
      }),
    );
  });

  it('applies vendor ICO filter on multi-select checkbox', () => {
    const onChange = vi.fn();
    render(<FilterBar {...defaultProps} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('filter-vendor-ico-trigger'));
    fireEvent.click(screen.getByLabelText(/11111111/));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        vendor_icos: ['11111111'],
      }),
    );
  });

  it('clears institution ICO selection when deselected', () => {
    const onChange = vi.fn();
    render(
      <FilterBar
        {...defaultProps}
        onChange={onChange}
        filters={{ vendors: ['Vendor X'], institution_icos: ['11111111'] }}
      />,
    );
    fireEvent.click(screen.getByTestId('filter-institution-ico-trigger'));
    fireEvent.click(screen.getByLabelText(/11111111/));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        institution_icos: undefined,
      }),
    );
  });

  it('removes stale ICO when institution selection changes', () => {
    const onChange = vi.fn();
    render(
      <FilterBar
        {...defaultProps}
        onChange={onChange}
        institutions={['Inst A', 'Inst B', 'Inst C']}
        institutionIcoMap={{ 'Inst A': '11111111', 'Inst B': '22222222', 'Inst C': '33333333' }}
        filters={{
          institutions: ['Inst A', 'Inst B', 'Inst C'],
          institution_icos: ['11111111', '22222222', '33333333'],
        }}
      />,
    );
    fireEvent.click(screen.getByTestId('filter-institution-trigger'));
    fireEvent.click(screen.getByLabelText(/Inst C/));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        institutions: ['Inst A', 'Inst B'],
        institution_icos: ['11111111', '22222222', '33333333'],
      }),
    );
  });

  it('prioritizes more relevant search matches first', () => {
    render(
      <FilterBar
        {...defaultProps}
        institutions={['Gimnazium Armina', 'Ministerstvo financií', 'Urad pre administraciu']}
      />,
    );
    fireEvent.click(screen.getByTestId('filter-institution-trigger'));
    fireEvent.change(screen.getByTestId('filter-institution-search'), { target: { value: 'min' } });
    const labels = Array.from(screen.getByTestId('filter-institution-list').querySelectorAll('label .flex-1')).map((n) =>
      n.textContent?.trim(),
    );
    expect(labels[0]).toBe('Ministerstvo financií');
  });

  it('renders category slicer', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByTestId('filter-category-trigger')).toBeInTheDocument();
  });

  it('pins selected categories to top', () => {
    render(
      <FilterBar
        {...defaultProps}
        categories={['Alpha', 'Beta', 'Gamma']}
        filters={{ categories: ['Gamma'] }}
      />,
    );
    fireEvent.click(screen.getByTestId('filter-category-trigger'));
    const labels = Array.from(screen.getByTestId('filter-category-list').querySelectorAll('label .flex-1')).map((n) =>
      n.textContent?.trim(),
    );
    expect(labels[0]).toBe('Gamma');
  });
});

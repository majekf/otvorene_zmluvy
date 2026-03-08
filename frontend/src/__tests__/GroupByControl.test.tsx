/**
 * Tests for GroupByControl component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import GroupByControl from '../components/GroupByControl';

describe('GroupByControl', () => {
  it('renders all group-by options', () => {
    render(<GroupByControl value="category" onChange={vi.fn()} />);
    expect(screen.getByTestId('group-by-control')).toBeInTheDocument();
    expect(screen.getByText('Category')).toBeInTheDocument();
    expect(screen.getByText('Vendor')).toBeInTheDocument();
    expect(screen.getByText('Institution')).toBeInTheDocument();
  });

  it('highlights the active button', () => {
    render(<GroupByControl value="supplier" onChange={vi.fn()} />);
    const vendorBtn = screen.getByText('Vendor');
    // Active button should have the active class
    expect(vendorBtn.className).toContain('active');
  });

  it('calls onChange when a button is clicked', () => {
    const onChange = vi.fn();
    render(<GroupByControl value="category" onChange={onChange} />);
    fireEvent.click(screen.getByText('Institution'));
    expect(onChange).toHaveBeenCalledWith('buyer');
  });

  it('renders options in the correct order: Vendor, Institution, Category, Month, Award Type', () => {
    render(<GroupByControl value="category" onChange={vi.fn()} />);
    const buttons = screen.getAllByRole('button');
    const labels = buttons.map((btn) => btn.textContent);
    expect(labels).toEqual(['Vendor', 'Institution', 'Category', 'Month', 'Award Type']);
  });
});

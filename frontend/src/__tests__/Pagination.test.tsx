/**
 * Tests for Pagination component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from '../components/Pagination';

describe('Pagination', () => {
  it('does not render when only one page', () => {
    const { container } = render(
      <Pagination page={1} pageSize={20} total={15} onPageChange={vi.fn()} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders pagination for multiple pages', () => {
    render(<Pagination page={1} pageSize={20} total={100} onPageChange={vi.fn()} />);
    expect(screen.getByTestId('pagination')).toBeInTheDocument();
    expect(screen.getByTestId('pagination')).toHaveTextContent(/Page/);
  });

  it('disables prev/first on first page', () => {
    render(<Pagination page={1} pageSize={20} total={100} onPageChange={vi.fn()} />);
    expect(screen.getByTestId('page-first')).toBeDisabled();
    expect(screen.getByTestId('page-prev')).toBeDisabled();
  });

  it('disables next/last on last page', () => {
    render(<Pagination page={5} pageSize={20} total={100} onPageChange={vi.fn()} />);
    expect(screen.getByTestId('page-next')).toBeDisabled();
    expect(screen.getByTestId('page-last')).toBeDisabled();
  });

  it('calls onPageChange when next is clicked', () => {
    const onChange = vi.fn();
    render(<Pagination page={2} pageSize={20} total={100} onPageChange={onChange} />);
    fireEvent.click(screen.getByTestId('page-next'));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it('calls onPageChange when prev is clicked', () => {
    const onChange = vi.fn();
    render(<Pagination page={3} pageSize={20} total={100} onPageChange={onChange} />);
    fireEvent.click(screen.getByTestId('page-prev'));
    expect(onChange).toHaveBeenCalledWith(2);
  });

  it('calls onPageChange when a page number is clicked', () => {
    const onChange = vi.fn();
    render(<Pagination page={1} pageSize={20} total={100} onPageChange={onChange} />);
    fireEvent.click(screen.getByTestId('page-3'));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it('highlights current page', () => {
    render(<Pagination page={2} pageSize={20} total={100} onPageChange={vi.fn()} />);
    const btn = screen.getByTestId('page-2');
    expect(btn.className).toContain('bg-primary-600');
  });
});

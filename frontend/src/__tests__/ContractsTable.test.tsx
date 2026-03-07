/**
 * Tests for ContractsTable component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ContractsTable from '../components/ContractsTable';
import type { Contract, SortSpec } from '../types';

const makeContract = (overrides: Partial<Contract> = {}): Contract => ({
  contract_id: 'c1',
  contract_title: 'Test Contract',
  contract_number: null,
  buyer: 'Institution A',
  supplier: 'Vendor X',
  price_numeric_eur: 10000,
  price_raw: '10 000 €',
  published_date: '2024-01-15',
  category: 'IT',
  award_type: 'open_tender',
  pdf_text_summary: '',
  contract_url: null,
  ico_buyer: null,
  ico_supplier: null,
  date_published: null,
  date_concluded: null,
  date_effective: null,
  date_valid_until: null,
  pdf_url: null,
  pdf_text: null,
  scraped_at: null,
  ...overrides,
});

function renderTable(contracts: Contract[], sort: SortSpec = [], onSortChange = vi.fn(), onRowClick = vi.fn()) {
  return render(
    <MemoryRouter>
      <ContractsTable contracts={contracts} sort={sort} onSortChange={onSortChange} onRowClick={onRowClick} />
    </MemoryRouter>,
  );
}

describe('ContractsTable', () => {
  it('renders empty state when no contracts', () => {
    renderTable([]);
    expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    expect(screen.getByText('No contracts to display')).toBeInTheDocument();
  });

  it('renders contracts in a table', () => {
    renderTable([makeContract()]);
    expect(screen.getByText('Test Contract')).toBeInTheDocument();
    expect(screen.getByText('Vendor X')).toBeInTheDocument();
    expect(screen.getByText('Institution A')).toBeInTheDocument();
  });

  it('calls onSortChange on header click', () => {
    const onSortChange = vi.fn();
    renderTable([makeContract()], [], onSortChange);
    fireEvent.click(screen.getByTestId('th-contract_title'));
    expect(onSortChange).toHaveBeenCalledWith([['contract_title', 'asc']]);
  });

  it('toggles sort direction when clicking same column', () => {
    const onSortChange = vi.fn();
    renderTable([makeContract()], [['contract_title', 'asc']], onSortChange);
    fireEvent.click(screen.getByTestId('th-contract_title'));
    expect(onSortChange).toHaveBeenCalledWith([['contract_title', 'desc']]);
  });

  it('appends secondary sort on shift+click', () => {
    const onSortChange = vi.fn();
    renderTable([makeContract()], [['contract_title', 'asc']], onSortChange);
    fireEvent.click(screen.getByTestId('th-price_numeric_eur'), { shiftKey: true });
    expect(onSortChange).toHaveBeenCalledWith([
      ['contract_title', 'asc'],
      ['price_numeric_eur', 'asc'],
    ]);
  });

  it('shows direction arrow for sorted column', () => {
    renderTable([makeContract()], [['published_date', 'desc']]);
    const th = screen.getByTestId('th-published_date');
    expect(th.textContent).toContain('↓');
  });

  it('shows priority badge for multi-sort', () => {
    renderTable(
      [makeContract()],
      [
        ['buyer', 'asc'],
        ['price_numeric_eur', 'desc'],
      ],
    );
    const thBuyer = screen.getByTestId('th-buyer');
    const thPrice = screen.getByTestId('th-price_numeric_eur');
    expect(thBuyer.textContent).toContain('①');
    expect(thPrice.textContent).toContain('②');
  });

  it('calls onRowClick when row is clicked', () => {
    const onRowClick = vi.fn();
    renderTable([makeContract({ contract_id: 'abc123' })], [], vi.fn(), onRowClick);
    fireEvent.click(screen.getByTestId('row-abc123'));
    expect(onRowClick).toHaveBeenCalledWith('abc123');
  });

  it('clicking vendor link does not trigger row navigation', () => {
    const onRowClick = vi.fn();
    renderTable([makeContract({ contract_id: 'c1', supplier: 'Vendor X' })], [], vi.fn(), onRowClick);
    const vendorLink = screen.getByRole('link', { name: 'Vendor X' });
    fireEvent.click(vendorLink);
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it('clicking institution link does not trigger row navigation', () => {
    const onRowClick = vi.fn();
    renderTable([makeContract({ contract_id: 'c1', buyer: 'Institution A' })], [], vi.fn(), onRowClick);
    const institutionLink = screen.getByRole('link', { name: 'Institution A' });
    fireEvent.click(institutionLink);
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it('vendor link points to vendor profile page', () => {
    renderTable([makeContract({ supplier: 'Vendor X' })]);
    const vendorLink = screen.getByRole('link', { name: 'Vendor X' });
    expect(vendorLink).toHaveAttribute('href', '/vendor/Vendor%20X');
  });

  it('institution link points to institution profile page', () => {
    renderTable([makeContract({ buyer: 'Institution A' })]);
    const institutionLink = screen.getByRole('link', { name: 'Institution A' });
    expect(institutionLink).toHaveAttribute('href', '/institution/Institution%20A');
  });

  it('title link points to contract detail page', () => {
    renderTable([makeContract({ contract_id: 'c1', contract_title: 'Test Contract' })]);
    const titleLink = screen.getByRole('link', { name: 'Test Contract' });
    expect(titleLink).toHaveAttribute('href', '/contract/c1');
  });
});

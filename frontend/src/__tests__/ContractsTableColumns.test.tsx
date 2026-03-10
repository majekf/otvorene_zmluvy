/**
 * Tests for ContractsTable column order, column consistency across views,
 * and column width configuration.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ContractsTable, { TABLE_COLUMNS } from '../components/ContractsTable';
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
  scanned_suggested_title: 'Managed services',
  scanned_service_type: 'it_services',
  scanned_service_subtype: 'helpdesk',
  ...overrides,
});

function renderTable(
  contracts: Contract[],
  sort: SortSpec = [],
  onSortChange = vi.fn(),
  variant: 'default' | 'all-contracts' = 'default',
) {
  return render(
    <MemoryRouter>
      <ContractsTable
        contracts={contracts}
        sort={sort}
        onSortChange={onSortChange}
        variant={variant}
      />
    </MemoryRouter>,
  );
}

describe('ContractsTable – Column order and consistency', () => {
  const EXPECTED_ORDER = [
    'scanned_suggested_title',
    'supplier',
    'buyer',
    'price_numeric_eur',
    'published_date',
    'scanned_service_subtype',
  ];

  const EXPECTED_LABELS = [
    'Subject',
    'Vendor',
    'Institution',
    'Value',
    'Date',
    'Subtype',
  ];

  it('TABLE_COLUMNS has exactly 6 columns', () => {
    expect(TABLE_COLUMNS).toHaveLength(6);
  });

  it('TABLE_COLUMNS keys follow the required order: Subject, Vendor, Institution, Value, Date, Subtype', () => {
    const keys = TABLE_COLUMNS.map((col) => col.key);
    expect(keys).toEqual(EXPECTED_ORDER);
  });

  it('TABLE_COLUMNS labels follow the required order', () => {
    const labels = TABLE_COLUMNS.map((col) => col.label);
    expect(labels).toEqual(EXPECTED_LABELS);
  });

  it('default variant renders all 6 column headers in correct order', () => {
    renderTable([makeContract()]);
    const headers = screen.getAllByRole('columnheader');
    const headerKeys = headers.map((h) => h.getAttribute('data-testid')?.replace('th-', ''));
    expect(headerKeys).toEqual(EXPECTED_ORDER);
  });

  it('all-contracts variant renders the same 6 column headers in the same order', () => {
    renderTable([makeContract()], [], vi.fn(), 'all-contracts');
    const headers = screen.getAllByRole('columnheader');
    const headerKeys = headers.map((h) => h.getAttribute('data-testid')?.replace('th-', ''));
    expect(headerKeys).toEqual(EXPECTED_ORDER);
  });

  it('default and all-contracts variants produce identical columns', () => {
    const { unmount } = renderTable([makeContract()], [], vi.fn(), 'default');
    const defaultHeaders = screen.getAllByRole('columnheader').map((h) => h.textContent);
    unmount();

    renderTable([makeContract()], [], vi.fn(), 'all-contracts');
    const allContractsHeaders = screen.getAllByRole('columnheader').map((h) => h.textContent);
    expect(defaultHeaders).toEqual(allContractsHeaders);
  });

  it('does not include an Award column', () => {
    renderTable([makeContract()]);
    expect(screen.queryByTestId('th-award_type')).not.toBeInTheDocument();
  });

  it('does not include a Title column', () => {
    renderTable([makeContract()]);
    expect(screen.queryByTestId('th-contract_title')).not.toBeInTheDocument();
  });

  it('does not include a Type column', () => {
    renderTable([makeContract()]);
    expect(screen.queryByTestId('th-scanned_service_type')).not.toBeInTheDocument();
  });

  it('includes Subject and Subtype columns in default variant', () => {
    renderTable([makeContract()]);
    expect(screen.getByTestId('th-scanned_suggested_title')).toBeInTheDocument();
    expect(screen.getByTestId('th-scanned_service_subtype')).toBeInTheDocument();
  });

  it('Subject column links to contract detail page', () => {
    renderTable([makeContract({ contract_id: 'c1', scanned_suggested_title: 'Managed services' })]);
    const subjectLink = screen.getByRole('link', { name: 'Managed services' });
    expect(subjectLink).toHaveAttribute('href', '/contract/c1');
  });
});

describe('ContractsTable – Column width configuration', () => {
  it('Subject column has a wider width class (w-[24%])', () => {
    const subjectCol = TABLE_COLUMNS.find((col) => col.key === 'scanned_suggested_title');
    expect(subjectCol?.className).toContain('w-[24%]');
  });

  it('Subject column max-width is 300px', () => {
    const subjectCol = TABLE_COLUMNS.find((col) => col.key === 'scanned_suggested_title');
    expect(subjectCol?.className).toContain('max-w-[300px]');
  });

  it('all columns have explicit width classes', () => {
    for (const col of TABLE_COLUMNS) {
      expect(col.className).toBeDefined();
      expect(col.className).toMatch(/w-\[/);
    }
  });

  it('all text-heavy columns have truncate class for overflow', () => {
    const textCols = ['scanned_suggested_title', 'supplier', 'buyer', 'scanned_service_subtype'];
    for (const key of textCols) {
      const col = TABLE_COLUMNS.find((c) => c.key === key);
      expect(col?.className).toContain('truncate');
    }
  });

  it('Value column is right-aligned', () => {
    const valueCol = TABLE_COLUMNS.find((col) => col.key === 'price_numeric_eur');
    expect(valueCol?.className).toContain('text-right');
  });
});

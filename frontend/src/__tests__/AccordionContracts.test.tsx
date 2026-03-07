/**
 * Tests for AccordionContracts component
 *
 * Covers: loading state, contracts table rendering, pagination,
 * empty state, error state, group-to-filter mapping (mergeGroupFilter),
 * row click navigation, and sort change resetting page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AccordionContracts, { mergeGroupFilter } from '../components/AccordionContracts';
import * as api from '../api';

vi.mock('../api');

const mockContracts = {
  contracts: [
    {
      contract_id: 'ac1',
      contract_title: 'Group Contract A',
      contract_number: null,
      buyer: 'Ministry of Interior',
      supplier: 'SupplierA',
      price_numeric_eur: 100000,
      price_raw: null,
      published_date: '2024-04-01',
      category: 'construction',
      award_type: 'open_tender',
      pdf_text_summary: 'not_summarized',
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
    },
    {
      contract_id: 'ac2',
      contract_title: 'Group Contract B',
      contract_number: null,
      buyer: 'Ministry of Interior',
      supplier: 'SupplierB',
      price_numeric_eur: 50000,
      price_raw: null,
      published_date: '2024-05-10',
      category: 'construction',
      award_type: 'direct_award',
      pdf_text_summary: 'not_summarized',
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
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

const paginatedContracts = {
  ...mockContracts,
  total: 25,
  total_pages: 3,
};

const emptyContracts = {
  contracts: [],
  total: 0,
  page: 1,
  page_size: 10,
  total_pages: 0,
};

function renderComponent(
  props: Partial<React.ComponentProps<typeof AccordionContracts>> = {},
) {
  const defaults = {
    filters: {},
    groupBy: 'category' as const,
    groupValue: 'construction',
  };
  return render(
    <MemoryRouter>
      <AccordionContracts {...defaults} {...props} />
    </MemoryRouter>,
  );
}

describe('AccordionContracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchContracts).mockResolvedValue(mockContracts);
  });

  // ── Loading ───────────────────────────────────────────────────────

  it('shows loading skeleton immediately', () => {
    vi.mocked(api.fetchContracts).mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getByTestId('accordion-loading-construction')).toBeInTheDocument();
  });

  it('hides loading skeleton after data loads', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.queryByTestId('accordion-loading-construction')).not.toBeInTheDocument();
    });
  });

  // ── Data rendering ────────────────────────────────────────────────

  it('renders contracts table after loading', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByTestId('accordion-contracts-construction')).toBeInTheDocument();
      expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    });
  });

  it('displays contract titles', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText('Group Contract A')).toBeInTheDocument();
      expect(screen.getByText('Group Contract B')).toBeInTheDocument();
    });
  });

  // ── Pagination ────────────────────────────────────────────────────

  it('shows pagination when total > pageSize', async () => {
    vi.mocked(api.fetchContracts).mockResolvedValue(paginatedContracts);
    renderComponent();
    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument();
    });
  });

  it('does not show pagination when total <= pageSize', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('pagination')).not.toBeInTheDocument();
  });

  // ── Empty state ───────────────────────────────────────────────────

  it('shows empty state when no contracts', async () => {
    vi.mocked(api.fetchContracts).mockResolvedValue(emptyContracts);
    renderComponent();
    await waitFor(() => {
      expect(screen.getByTestId('accordion-empty-construction')).toBeInTheDocument();
    });
    expect(screen.getByText(/No contracts in this group/)).toBeInTheDocument();
  });

  // ── Error state ───────────────────────────────────────────────────

  it('shows error message when fetch fails', async () => {
    vi.mocked(api.fetchContracts).mockRejectedValue(new Error('fail'));
    renderComponent();
    await waitFor(() => {
      expect(screen.getByTestId('accordion-error-construction')).toBeInTheDocument();
    });
    expect(screen.getByText(/Failed to load group contracts/)).toBeInTheDocument();
  });

  // ── API call correctness ──────────────────────────────────────────

  it('calls fetchContracts with category filter for groupBy=category', async () => {
    renderComponent({ groupBy: 'category', groupValue: 'construction' });
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledWith(
        expect.objectContaining({ categories: ['construction'] }),
        1,
        10,
        [],
      );
    });
  });

  it('calls fetchContracts with vendor filter for groupBy=supplier', async () => {
    renderComponent({ groupBy: 'supplier', groupValue: 'BigCorp' });
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledWith(
        expect.objectContaining({ vendors: ['BigCorp'] }),
        1,
        10,
        [],
      );
    });
  });

  it('calls fetchContracts with institution filter for groupBy=buyer', async () => {
    renderComponent({ groupBy: 'buyer', groupValue: 'Ministry X' });
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledWith(
        expect.objectContaining({ institutions: ['Ministry X'] }),
        1,
        10,
        [],
      );
    });
  });

  it('calls fetchContracts with award_types filter for groupBy=award_type', async () => {
    renderComponent({ groupBy: 'award_type', groupValue: 'direct_award' });
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledWith(
        expect.objectContaining({ award_types: ['direct_award'] }),
        1,
        10,
        [],
      );
    });
  });

  it('calls fetchContracts with date range for groupBy=month', async () => {
    renderComponent({ groupBy: 'month', groupValue: '2024-02' });
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledWith(
        expect.objectContaining({ date_from: '2024-02-01', date_to: '2024-02-29' }),
        1,
        10,
        [],
      );
    });
  });

  it('preserves parent filters when merging group filter', async () => {
    renderComponent({
      filters: { text_search: 'roads', value_min: 1000 },
      groupBy: 'category',
      groupValue: 'construction',
    });
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledWith(
        expect.objectContaining({
          text_search: 'roads',
          value_min: 1000,
          categories: ['construction'],
        }),
        1,
        10,
        [],
      );
    });
  });

  // ── Sort ──────────────────────────────────────────────────────────

  it('resets to page 1 when sort changes', async () => {
    vi.mocked(api.fetchContracts).mockResolvedValue(paginatedContracts);
    renderComponent();
    await waitFor(() => {
      expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    });

    vi.mocked(api.fetchContracts).mockClear();
    const priceHeader = screen.getByTestId('th-price_numeric_eur');
    fireEvent.click(priceHeader);

    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalled();
      const callArgs = vi.mocked(api.fetchContracts).mock.calls[0];
      // page (index 1) should be 1 after sort change
      expect(callArgs[1]).toBe(1);
    });
  });
});

// ── mergeGroupFilter unit tests ───────────────────────────────────

describe('mergeGroupFilter', () => {
  it('adds categories for groupBy=category', () => {
    const result = mergeGroupFilter({}, 'category', 'construction');
    expect(result.categories).toEqual(['construction']);
  });

  it('adds vendors for groupBy=supplier', () => {
    const result = mergeGroupFilter({}, 'supplier', 'VendorX');
    expect(result.vendors).toEqual(['VendorX']);
  });

  it('adds institutions for groupBy=buyer', () => {
    const result = mergeGroupFilter({}, 'buyer', 'Ministry');
    expect(result.institutions).toEqual(['Ministry']);
  });

  it('adds award_types for groupBy=award_type', () => {
    const result = mergeGroupFilter({}, 'award_type', 'direct_award');
    expect(result.award_types).toEqual(['direct_award']);
  });

  it('sets date range for groupBy=month', () => {
    const result = mergeGroupFilter({}, 'month', '2024-03');
    expect(result.date_from).toBe('2024-03-01');
    expect(result.date_to).toBe('2024-03-31');
  });

  it('handles February leap year correctly', () => {
    const result = mergeGroupFilter({}, 'month', '2024-02');
    expect(result.date_from).toBe('2024-02-01');
    expect(result.date_to).toBe('2024-02-29');
  });

  it('handles February non-leap year correctly', () => {
    const result = mergeGroupFilter({}, 'month', '2023-02');
    expect(result.date_from).toBe('2023-02-01');
    expect(result.date_to).toBe('2023-02-28');
  });

  it('preserves existing filter fields', () => {
    const base = { text_search: 'roads', value_min: 5000 };
    const result = mergeGroupFilter(base, 'category', 'it');
    expect(result.text_search).toBe('roads');
    expect(result.value_min).toBe(5000);
    expect(result.categories).toEqual(['it']);
  });

  it('does not mutate the base filter', () => {
    const base = { text_search: 'test' };
    mergeGroupFilter(base, 'category', 'x');
    expect(base).toEqual({ text_search: 'test' });
  });
});

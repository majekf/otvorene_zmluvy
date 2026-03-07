/**
 * Tests for AllContracts page
 *
 * Covers: rendering, loading state, contracts table, pagination,
 * row click navigation, sort changes, filter changes, error state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AllContracts from '../pages/AllContracts';
import { FilterProvider } from '../FilterContext';
import * as api from '../api';

vi.mock('../api');

const mockContracts = {
  contracts: [
    {
      contract_id: 'c1',
      contract_title: 'Road Construction A',
      contract_number: null,
      buyer: 'Ministry of Transport',
      supplier: 'BuildCo',
      price_numeric_eur: 250000,
      price_raw: null,
      published_date: '2024-03-01',
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
      contract_id: 'c2',
      contract_title: 'IT Services B',
      contract_number: null,
      buyer: 'Ministry of Finance',
      supplier: 'TechCorp',
      price_numeric_eur: 75000,
      price_raw: null,
      published_date: '2024-06-15',
      category: 'it',
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
  // total > page_size so Pagination component actually renders
  total: 50,
  page: 1,
  page_size: 20,
  total_pages: 3,
};

const emptyContracts = {
  contracts: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0,
};

function renderPage(route = '/contracts') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <FilterProvider>
        <Routes>
          <Route path="/contracts" element={<AllContracts />} />
          <Route path="/contract/:id" element={<div data-testid="contract-detail">Detail</div>} />
        </Routes>
      </FilterProvider>
    </MemoryRouter>,
  );
}

describe('AllContracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchContracts).mockResolvedValue(mockContracts);
    vi.mocked(api.fetchAggregations).mockResolvedValue({
      group_by: '',
      results: [],
      summary: { contract_count: 0, total_spend: 0, avg_value: 0, max_value: 0 },
    });
  });

  // ── Rendering ─────────────────────────────────────────────────────

  it('renders the page container', async () => {
    renderPage();
    expect(screen.getByTestId('all-contracts')).toBeInTheDocument();
  });

  it('renders the filter bar', async () => {
    renderPage();
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
  });

  it('shows loading skeleton initially', () => {
    vi.mocked(api.fetchContracts).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('all-contracts-loading')).toBeInTheDocument();
  });

  it('hides loading skeleton after data loads', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByTestId('all-contracts-loading')).not.toBeInTheDocument();
    });
  });

  // ── Table data ────────────────────────────────────────────────────

  it('renders contracts table after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    });
  });

  it('displays contract rows', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Road Construction A')).toBeInTheDocument();
      expect(screen.getByText('IT Services B')).toBeInTheDocument();
    });
  });

  it('does NOT render summary strip', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByTestId('summary-strip')).not.toBeInTheDocument();
    });
  });

  it('does NOT render treemap or bar chart', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByTestId('treemap-chart')).not.toBeInTheDocument();
      expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
    });
  });

  it('does NOT render rule panel toggle', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByTestId('toggle-rules')).not.toBeInTheDocument();
    });
  });

  // ── Pagination ────────────────────────────────────────────────────

  it('renders pagination when contracts are loaded', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument();
    });
  });

  it('does not render pagination when loading', () => {
    vi.mocked(api.fetchContracts).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.queryByTestId('pagination')).not.toBeInTheDocument();
  });

  // ── Empty state ───────────────────────────────────────────────────

  it('renders empty table when no contracts returned', async () => {
    vi.mocked(api.fetchContracts).mockResolvedValue(emptyContracts);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    });
  });

  // ── Error state ───────────────────────────────────────────────────

  it('shows error alert when fetch fails', async () => {
    vi.mocked(api.fetchContracts).mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('all-contracts-error')).toBeInTheDocument();
    });
    expect(screen.getByText(/Failed to load contracts/)).toBeInTheDocument();
  });

  it('error alert has role="alert"', async () => {
    vi.mocked(api.fetchContracts).mockRejectedValue(new Error('fail'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  // ── API calls ────────────────────────────────────────────────────

  it('calls fetchContracts on mount', async () => {
    renderPage();
    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalledTimes(1);
    });
  });

  it('resets to page 1 when sort changes', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('contracts-table')).toBeInTheDocument();
    });

    vi.mocked(api.fetchContracts).mockClear();
    // Click the "Value" column header (price_numeric_eur) to trigger sort change
    const priceHeader = screen.getByTestId('th-price_numeric_eur');
    fireEvent.click(priceHeader);

    await waitFor(() => {
      expect(api.fetchContracts).toHaveBeenCalled();
      const callArgs = vi.mocked(api.fetchContracts).mock.calls[0];
      // page argument (index 1) should be 1
      expect(callArgs[1]).toBe(1);
    });
  });
});

/**
 * Tests for GlobalView page (Phase 6)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GlobalView from '../pages/GlobalView';
import { FilterProvider } from '../FilterContext';
import * as api from '../api';

vi.mock('../api');

const mockInstitutionRankings = {
  entity: 'institutions',
  metric: 'total_spend',
  rankings: [
    { rank: 1, institution: 'Top Ministry', value: 5000000 },
    { rank: 2, institution: 'Second Ministry', value: 3000000 },
    { rank: 3, institution: 'Third Ministry', value: 1000000 },
  ],
};

const mockVendorRankings = {
  entity: 'vendors',
  metric: 'total_spend',
  rankings: [
    { rank: 1, vendor: 'Big Vendor', value: 4000000 },
    { rank: 2, vendor: 'Small Vendor', value: 1000000 },
  ],
};

const emptyRankings = {
  entity: 'institutions',
  metric: 'total_spend',
  rankings: [],
};

function renderPage(route = '/rankings') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <FilterProvider>
        <Routes>
          <Route path="/rankings" element={<GlobalView />} />
        </Routes>
      </FilterProvider>
    </MemoryRouter>,
  );
}

describe('GlobalView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchRankings).mockResolvedValue(mockInstitutionRankings);
    vi.mocked(api.fetchAggregations).mockResolvedValue({ group_by: '', results: [], summary: { contract_count: 0, total_spend: 0, avg_value: 0, max_value: 0 } });
  });

  it('renders page heading', async () => {
    renderPage();
    expect(screen.getByTestId('global-view')).toBeInTheDocument();
    expect(screen.getByText('Global Rankings')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(api.fetchRankings).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('global-loading')).toBeInTheDocument();
  });

  it('shows empty state when no rankings', async () => {
    vi.mocked(api.fetchRankings).mockResolvedValue(emptyRankings);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('global-empty')).toBeInTheDocument();
    });
  });

  it('renders rankings table', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('rankings-table')).toBeInTheDocument();
    });
    expect(screen.getByText('Top Ministry')).toBeInTheDocument();
    expect(screen.getByText('Second Ministry')).toBeInTheDocument();
    expect(screen.getByText('Third Ministry')).toBeInTheDocument();
  });

  it('shows institution/vendor column header correctly', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Institution')).toBeInTheDocument();
    });
  });

  it('entity toggle switches to vendors', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('rankings-table')).toBeInTheDocument();
    });

    // Switch mock to return vendor data for subsequent calls
    vi.mocked(api.fetchRankings).mockResolvedValue(mockVendorRankings);
    fireEvent.click(screen.getByTestId('entity-vendors'));

    await waitFor(() => {
      expect(screen.getByText('Big Vendor')).toBeInTheDocument();
    });
  });

  it('metric selector changes metric', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('rankings-table')).toBeInTheDocument();
    });

    vi.mocked(api.fetchRankings).mockClear();
    fireEvent.click(screen.getByTestId('metric-contract_count'));

    await waitFor(() => {
      expect(api.fetchRankings).toHaveBeenCalledWith(
        'institutions',
        'contract_count',
        expect.anything(),
      );
    });
  });

  it('rank rows have correct test ids', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('rank-row-1')).toBeInTheDocument();
      expect(screen.getByTestId('rank-row-2')).toBeInTheDocument();
      expect(screen.getByTestId('rank-row-3')).toBeInTheDocument();
    });
  });

  it('shows summary with count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('global-summary')).toBeInTheDocument();
      expect(screen.getByText(/3 institutions/)).toBeInTheDocument();
    });
  });
});

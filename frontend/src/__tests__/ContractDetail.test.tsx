/**
 * Tests for ContractDetail page
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ContractDetail from '../pages/ContractDetail';
import type { Contract } from '../types';
import * as api from '../api';

vi.mock('../api');

// Isolate ContractDetail from ChatBar — ChatBar makes a real fetchChatStatus()
// call on mount which would throw when '../api' is auto-mocked.
vi.mock('../components/ChatBar', () => ({ default: () => null }));

const mockContract: Contract = {
  contract_id: 'c123',
  contract_title: 'Test Contract Title',
  contract_number: 'CN-001',
  buyer: 'Test Institution',
  supplier: 'Test Vendor',
  price_numeric_eur: 25000,
  price_raw: '25 000 EUR',
  published_date: '2024-06-01',
  category: 'IT',
  award_type: 'open_tender',
  pdf_text_summary: 'This is a summary of the PDF content.',
  contract_url: 'https://example.com/contract',
  ico_buyer: '123456',
  ico_supplier: '654321',
  date_published: '2024-06-01',
  date_concluded: '2024-05-15',
  date_effective: '2024-07-01',
  date_valid_until: '2025-06-30',
  pdf_url: 'https://example.com/contract.pdf',
  pdf_text: null,
  scraped_at: '2024-06-02T10:00:00',
};

function renderWithRouter(contractId: string) {
  return render(
    <MemoryRouter initialEntries={[`/contract/${contractId}`]}>
      <Routes>
        <Route path="/contract/:id" element={<ContractDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ContractDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    vi.mocked(api.fetchContract).mockReturnValue(new Promise(() => {})); // never resolves
    renderWithRouter('c123');
    expect(screen.getByTestId('contract-detail-loading')).toBeInTheDocument();
  });

  it('renders contract details on success', async () => {
    vi.mocked(api.fetchContract).mockResolvedValue(mockContract);
    renderWithRouter('c123');

    await waitFor(() => {
      expect(screen.getByTestId('contract-detail')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Contract Title')).toBeInTheDocument();
    expect(screen.getByText('Test Institution')).toBeInTheDocument();
    expect(screen.getByText('Test Vendor')).toBeInTheDocument();
    expect(screen.getByTestId('badge-category')).toHaveTextContent('IT');
    expect(screen.getByTestId('badge-award')).toHaveTextContent('open_tender');
  });

  it('shows PDF link when pdf_url is present', async () => {
    vi.mocked(api.fetchContract).mockResolvedValue(mockContract);
    renderWithRouter('c123');

    await waitFor(() => {
      expect(screen.getByTestId('pdf-link')).toBeInTheDocument();
    });
  });

  it('shows PDF summary when present', async () => {
    vi.mocked(api.fetchContract).mockResolvedValue(mockContract);
    renderWithRouter('c123');

    await waitFor(() => {
      expect(screen.getByTestId('pdf-summary')).toBeInTheDocument();
    });
    expect(screen.getByText('This is a summary of the PDF content.')).toBeInTheDocument();
  });

  it('shows error state on API failure', async () => {
    vi.mocked(api.fetchContract).mockRejectedValue(new Error('Not found'));
    renderWithRouter('c123');

    await waitFor(() => {
      expect(screen.getByTestId('contract-detail-error')).toBeInTheDocument();
    });
    expect(screen.getByText(/Not found/)).toBeInTheDocument();
  });
});

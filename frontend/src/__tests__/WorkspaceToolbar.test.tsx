/**
 * Tests for WorkspaceToolbar component (Phase 7)
 *
 * Covers: Share button, Save Workspace, Export CSV, Export PDF.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import type { FilterState } from '../types';

// Mock the api module
vi.mock('../api', () => ({
  csvExportUrl: () => `/api/export/csv?mock=true`,
  pdfExportUrl: () => `/api/export/pdf?mock=true`,
  saveWorkspace: vi.fn().mockResolvedValue({
    token: 'mock-token',
    snapshot: { version: 1, filters: {}, saved_at: '2026-01-01T00:00:00Z' },
  }),
}));

const defaultProps = {
  filters: {} as FilterState,
  sort: [] as [string, string][],
  mode: 'dashboard',
};

function renderToolbar(props = {}) {
  return render(
    <MemoryRouter>
      <WorkspaceToolbar {...defaultProps} {...props} />
    </MemoryRouter>,
  );
}

describe('WorkspaceToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all four buttons', () => {
    renderToolbar();
    expect(screen.getByTestId('share-button')).toBeInTheDocument();
    expect(screen.getByTestId('save-workspace-button')).toBeInTheDocument();
    expect(screen.getByTestId('export-csv-button')).toBeInTheDocument();
    expect(screen.getByTestId('export-pdf-button')).toBeInTheDocument();
  });

  it('share button copies URL to clipboard', async () => {
    // Mock clipboard API
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    renderToolbar();
    fireEvent.click(screen.getByTestId('share-button'));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(window.location.href);
    });
    // Button text changes to "Copied!"
    expect(screen.getByTestId('share-button')).toHaveTextContent('Copied!');
  });

  it('export CSV button has correct href', () => {
    renderToolbar();
    const link = screen.getByTestId('export-csv-button');
    expect(link).toHaveAttribute('href', '/api/export/csv?mock=true');
    expect(link).toHaveAttribute('download');
  });

  it('export PDF button has correct href', () => {
    renderToolbar();
    const link = screen.getByTestId('export-pdf-button');
    expect(link).toHaveAttribute('href', '/api/export/pdf?mock=true');
    expect(link).toHaveAttribute('download');
  });

  it('save workspace button triggers download', async () => {
    // Mock URL.createObjectURL and revokeObjectURL
    const createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });

    // Spy on <a> element click via prototype (avoids interfering with React DOM)
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    renderToolbar();
    fireEvent.click(screen.getByTestId('save-workspace-button'));

    await waitFor(() => {
      expect(clickSpy).toHaveBeenCalled();
    });

    clickSpy.mockRestore();
  });
});

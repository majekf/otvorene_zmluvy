/**
 * Tests for App routing and layout
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

// Mock all pages/heavy components to isolate routing tests
vi.mock('../pages/Dashboard', () => ({
  default: () => <div data-testid="dashboard-page">Dashboard</div>,
}));
vi.mock('../pages/ContractDetail', () => ({
  default: () => <div data-testid="contract-detail-page">ContractDetail</div>,
}));
vi.mock('../pages/InstitutionProfile', () => ({
  default: () => <div data-testid="institution-profile-page">InstitutionProfile</div>,
}));
vi.mock('../pages/VendorProfile', () => ({
  default: () => <div data-testid="vendor-profile-page">VendorProfile</div>,
}));
vi.mock('../pages/BenchmarkView', () => ({
  default: () => <div data-testid="benchmark-view-page">BenchmarkView</div>,
}));
vi.mock('../pages/TimeView', () => ({
  default: () => <div data-testid="time-view-page">TimeView</div>,
}));
vi.mock('../pages/GlobalView', () => ({
  default: () => <div data-testid="global-view-page">GlobalView</div>,
}));

function renderApp(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App routing', () => {
  it('renders header with GovLens branding', () => {
    renderApp('/');
    expect(screen.getAllByText('GovLens').length).toBeGreaterThanOrEqual(1);
  });

  it('routes / to Dashboard', () => {
    renderApp('/');
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
  });

  it('routes /contract/:id to ContractDetail', () => {
    renderApp('/contract/c123');
    expect(screen.getByTestId('contract-detail-page')).toBeInTheDocument();
  });

  it('routes /institution/:id to InstitutionProfile', () => {
    renderApp('/institution/Ministry');
    expect(screen.getByTestId('institution-profile-page')).toBeInTheDocument();
  });

  it('routes /vendor/:id to VendorProfile', () => {
    renderApp('/vendor/VendorX');
    expect(screen.getByTestId('vendor-profile-page')).toBeInTheDocument();
  });

  it('routes /benchmark to BenchmarkView', () => {
    renderApp('/benchmark');
    expect(screen.getByTestId('benchmark-view-page')).toBeInTheDocument();
  });

  it('routes /time to TimeView', () => {
    renderApp('/time');
    expect(screen.getByTestId('time-view-page')).toBeInTheDocument();
  });

  it('routes /rankings to GlobalView', () => {
    renderApp('/rankings');
    expect(screen.getByTestId('global-view-page')).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderApp('/');
    const nav = screen.getByTestId('main-nav');
    expect(nav).toBeInTheDocument();
    expect(within(nav).getByText('Dashboard')).toBeInTheDocument();
    expect(within(nav).getByText('Benchmark')).toBeInTheDocument();
    expect(within(nav).getByText('Trends')).toBeInTheDocument();
    expect(within(nav).getByText('Rankings')).toBeInTheDocument();
  });

  it('renders footer', () => {
    renderApp('/');
    expect(screen.getByText(/crz\.gov\.sk/)).toBeInTheDocument();
  });
});

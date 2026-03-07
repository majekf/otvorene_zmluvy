/**
 * App – root layout with react-router routes and chatbot.
 */

import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ContractDetail from './pages/ContractDetail';
import InstitutionProfile from './pages/InstitutionProfile';
import VendorProfile from './pages/VendorProfile';
import BenchmarkView from './pages/BenchmarkView';
import TimeView from './pages/TimeView';
import GlobalView from './pages/GlobalView';
import ChatBar from './components/ChatBar';
import ErrorBoundary from './components/ErrorBoundary';
import { FilterProvider, useFilterContext } from './FilterContext';

function NavLink({ to, label }: { to: string; label: string }) {
  const { pathname } = useLocation();
  const active = pathname === to;
  return (
    <Link
      to={to}
      className={`nav-link ${active ? 'active' : ''}`}
    >
      {label}
    </Link>
  );
}

function Breadcrumbs() {
  const { pathname } = useLocation();
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length === 0) return null;

  return (
    <nav className="text-sm text-slate-500 mb-6" aria-label="Breadcrumb">
      <ol className="flex items-center gap-1.5">
        <li>
          <Link to="/" className="hover:text-primary-600 transition-colors">
            Home
          </Link>
        </li>
        {parts.map((part, idx) => {
          const path = '/' + parts.slice(0, idx + 1).join('/');
          const label = decodeURIComponent(part);
          const isLast = idx === parts.length - 1;
          return (
            <li key={path} className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m9 18 6-6-6-6" /></svg>
              {isLast ? (
                <span className="text-slate-800 font-semibold truncate max-w-[220px]">{label}</span>
              ) : (
                <Link to={path} className="hover:text-primary-600 transition-colors truncate max-w-[220px]">
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Inner shell that can access FilterContext for ChatBar filters. */
function AppShell() {
  const { filters } = useFilterContext();
  const { pathname } = useLocation();
  const showChat = pathname === '/';

  return (
    <div className="min-h-screen text-slate-900">
      {/* Top bar */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-slate-200/60 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2.5 group">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-md shadow-primary-500/20 group-hover:shadow-lg group-hover:shadow-primary-500/30 transition-shadow">
                  <svg className="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.64 0 8.577 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.64 0-8.577-3.007-9.963-7.178Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>
                </div>
                <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-primary-700 to-primary-500 bg-clip-text text-transparent">
                  GovLens
                </span>
              </Link>
              <nav className="hidden sm:flex items-center gap-1" data-testid="main-nav">
                <NavLink to="/" label="Dashboard" />
                <NavLink to="/benchmark" label="Benchmark" />
                <NavLink to="/time" label="Trends" />
                <NavLink to="/rankings" label="Rankings" />
              </nav>
            </div>
            <span className="hidden md:inline text-xs font-medium text-slate-400 tracking-wide">
              Slovak Government Contract Explorer
            </span>
          </div>
        </div>
      </header>

      <main className="px-4 sm:px-6 lg:px-8 py-8 max-w-7xl mx-auto">
        <Breadcrumbs />
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/contract/:id" element={<ContractDetail />} />
            <Route path="/institution/:id" element={<InstitutionProfile />} />
            <Route path="/vendor/:id" element={<VendorProfile />} />
            <Route path="/benchmark" element={<BenchmarkView />} />
            <Route path="/time" element={<TimeView />} />
            <Route path="/rankings" element={<GlobalView />} />
          </Routes>
        </ErrorBoundary>
      </main>

      <footer className="text-center text-xs text-slate-400 py-6 border-t border-slate-100 bg-white/40">
        <span className="font-medium">GovLens</span> &middot; Data from{' '}
        <a href="https://crz.gov.sk" target="_blank" rel="noopener noreferrer" className="hover:text-primary-600 transition-colors">crz.gov.sk</a>
      </footer>

      {/* Chatbot shown only on dashboard */}
      {showChat && <ChatBar filters={filters} />}
    </div>
  );
}

export default function App() {
  return (
    <FilterProvider>
      <AppShell />
    </FilterProvider>
  );
}

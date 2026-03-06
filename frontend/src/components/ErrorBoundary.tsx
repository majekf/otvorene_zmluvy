/**
 * ErrorBoundary — catches uncaught React render errors and displays
 * a graceful fallback UI instead of a white screen.
 *
 * Phase 8 — Polish, Integration Testing, and Deployment
 */

import { Component, type ReactNode, type ErrorInfo } from 'react';

interface ErrorBoundaryProps {
  /** Optional fallback render when an error is caught. */
  fallback?: ReactNode;
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log to console in development; could be sent to a monitoring service
    console.error('[ErrorBoundary] Caught error:', error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          data-testid="error-boundary-fallback"
          className="flex flex-col items-center justify-center min-h-[300px] p-8 text-center glass-card mx-auto max-w-lg my-12"
        >
          <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Something went wrong</h2>
          <p className="text-sm text-slate-500 mb-4 max-w-md">
            An unexpected error occurred while rendering this section.
            You can try again or navigate to a different page.
          </p>
          {this.state.error && (
            <details className="text-xs text-slate-400 mb-4 max-w-lg">
              <summary className="cursor-pointer hover:text-slate-600 transition-colors">Error details</summary>
              <pre className="mt-2 text-left bg-slate-50 p-3 rounded-lg overflow-auto max-h-32 font-mono">
                {this.state.error.message}
              </pre>
            </details>
          )}
          <button
            onClick={this.handleRetry}
            className="btn-primary"
            data-testid="error-boundary-retry"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

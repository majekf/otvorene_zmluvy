/**
 * Pagination Component
 *
 * Simple page navigation with first/prev/next/last and page numbers.
 */

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  if (totalPages <= 1) return null;

  // Show a window of pages around the current page
  const windowSize = 2;
  const startPage = Math.max(1, page - windowSize);
  const endPage = Math.min(totalPages, page + windowSize);

  const pages: number[] = [];
  for (let i = startPage; i <= endPage; i++) pages.push(i);

  return (
    <nav data-testid="pagination" className="flex items-center gap-1.5 text-sm" aria-label="Pagination">
      <button
        data-testid="page-first"
        className="btn-ghost px-2 py-1.5 disabled:opacity-30 disabled:cursor-not-allowed"
        disabled={page <= 1}
        onClick={() => onPageChange(1)}
        aria-label="First page"
      >
        «
      </button>
      <button
        data-testid="page-prev"
        className="btn-ghost px-2 py-1.5 disabled:opacity-30 disabled:cursor-not-allowed"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
      >
        ‹
      </button>

      {startPage > 1 && <span className="px-1 text-slate-400">…</span>}

      {pages.map((p) => (
        <button
          key={p}
          data-testid={`page-${p}`}
          className={`w-8 h-8 rounded-lg text-sm font-medium transition-all ${
            p === page
              ? 'bg-primary-600 text-white shadow-sm shadow-primary-600/30'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
          onClick={() => onPageChange(p)}
          aria-current={p === page ? 'page' : undefined}
        >
          {p}
        </button>
      ))}

      {endPage < totalPages && <span className="px-1 text-slate-400">…</span>}

      <button
        data-testid="page-next"
        className="btn-ghost px-2 py-1.5 disabled:opacity-30 disabled:cursor-not-allowed"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
      >
        ›
      </button>
      <button
        data-testid="page-last"
        className="btn-ghost px-2 py-1.5 disabled:opacity-30 disabled:cursor-not-allowed"
        disabled={page >= totalPages}
        onClick={() => onPageChange(totalPages)}
        aria-label="Last page"
      >
        »
      </button>

      <span className="ml-3 text-slate-500">
        Page <span className="font-semibold text-slate-700">{page}</span> of{' '}
        <span className="font-semibold text-slate-700">{totalPages}</span>
        <span className="text-slate-400"> · {total.toLocaleString()} results</span>
      </span>
    </nav>
  );
}

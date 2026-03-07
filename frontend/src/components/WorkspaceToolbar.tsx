/**
 * WorkspaceToolbar (Phase 7)
 *
 * Unified toolbar providing Share, Save Workspace, Export CSV,
 * and Export PDF buttons. Rendered on every page/view.
 */

import { useState, useCallback } from 'react';
import type { FilterState, SortSpec } from '../types';
import { csvExportUrl, pdfExportUrl, saveWorkspace } from '../api';

export interface WorkspaceToolbarProps {
  /** Active filter state for export. */
  filters: FilterState;
  /** Current sort spec for export column ordering. */
  sort?: SortSpec;
  /** Current mode label (dashboard, contracts, benchmark, time, rankings). */
  mode?: string;
  /** Optional group-by for workspace snapshot. */
  groupBy?: string;
  /** Current page number. */
  page?: number;
  /** Optional chat session id to include history in workspace. */
  sessionId?: string;
}

export default function WorkspaceToolbar({
  filters,
  sort = [],
  mode = 'dashboard',
  groupBy = 'category',
  page = 1,
  sessionId,
}: WorkspaceToolbarProps) {
  const [shareStatus, setShareStatus] = useState<'idle' | 'copied'>('idle');
  const [saving, setSaving] = useState(false);

  // ── Share: copy current URL to clipboard ──────────────────────────
  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareStatus('copied');
      setTimeout(() => setShareStatus('idle'), 2000);
    } catch {
      // Fallback for environments without clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = window.location.href;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setShareStatus('copied');
      setTimeout(() => setShareStatus('idle'), 2000);
    }
  }, []);

  // ── Save Workspace ────────────────────────────────────────────────
  const handleSaveWorkspace = useCallback(async () => {
    setSaving(true);
    try {
      const result = await saveWorkspace({
        filters,
        sort,
        groupBy,
        page,
        mode,
        session_id: sessionId || '',
        chartState: {},
      });

      // Trigger download of the workspace snapshot as JSON
      const blob = new Blob(
        [JSON.stringify(result.snapshot, null, 2)],
        { type: 'application/json' },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `govlens-workspace-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // silently fail
    } finally {
      setSaving(false);
    }
  }, [filters, sort, groupBy, page, mode, sessionId]);

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid="workspace-toolbar"
    >
      {/* Share */}
      <button
        data-testid="share-button"
        className="btn-secondary inline-flex items-center gap-1.5"
        onClick={handleShare}
        title="Copy shareable link to clipboard"
      >
        {shareStatus === 'copied' ? (
          <>
            <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
            Copied!
          </>
        ) : (
          <>
            <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" /></svg>
            Share
          </>
        )}
      </button>

      {/* Save Workspace */}
      <button
        data-testid="save-workspace-button"
        className="btn-secondary inline-flex items-center gap-1.5"
        onClick={handleSaveWorkspace}
        disabled={saving}
        title="Save current workspace as downloadable file"
      >
        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
        {saving ? 'Saving…' : 'Save'}
      </button>

      {/* Export CSV */}
      <a
        data-testid="export-csv-button"
        href={csvExportUrl(filters, sort)}
        download
        className="btn-secondary inline-flex items-center gap-1.5"
        title="Download filtered contracts as CSV"
      >
        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 0v.75\" /></svg>
        CSV
      </a>

      {/* Export PDF */}
      <a
        data-testid="export-pdf-button"
        href={pdfExportUrl(filters, sort)}
        download
        className="btn-secondary inline-flex items-center gap-1.5"
        title="Download filtered contracts as PDF report"
      >
        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
        PDF
      </a>
    </div>
  );
}

'use client';
/**
 * HistoryDrawer — slide-in panel showing last 10 investigations from localStorage.
 * Click any entry to restore it as the active investigation.
 */
import { useEffect, useState } from 'react';
import type { HistoryEntry } from '@/lib/storage';
import { loadHistory, clearHistory } from '@/lib/storage';
import type { InvestigationResponse } from '@/lib/types';

interface Props {
  open:     boolean;
  onClose:  () => void;
  onRestore:(inv: InvestigationResponse) => void;
}

const severityColor: Record<string, string> = {
  critical: 'text-red-400 bg-red-900/30 border-red-700/40',
  high:     'text-orange-400 bg-orange-900/30 border-orange-700/40',
  medium:   'text-yellow-400 bg-yellow-900/30 border-yellow-700/40',
  low:      'text-green-400 bg-green-900/30 border-green-700/40',
  unknown:  'text-gray-400 bg-gray-800 border-gray-700',
};

export default function HistoryDrawer({ open, onClose, onRestore }: Props) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    if (open) setHistory(loadHistory());
  }, [open]);

  const handleClear = () => { clearHistory(); setHistory([]); };

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      )}

      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Investigation History"
        className={`fixed top-0 right-0 h-full w-80 max-w-full bg-gray-900 border-l border-gray-700 z-50
          flex flex-col shadow-2xl transition-transform duration-300 ease-in-out
          ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-700">
          <h2 className="text-base font-semibold text-white">📜 Investigation History</h2>
          <button onClick={onClose} aria-label="Close history"
            className="text-gray-400 hover:text-white transition-colors text-xl leading-none">&times;</button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {history.length === 0 ? (
            <div className="text-center text-gray-500 text-sm mt-16 space-y-2">
              <div className="text-3xl">📭</div>
              <p>No saved investigations yet.</p>
              <p className="text-xs">Start an investigation and it will appear here automatically.</p>
            </div>
          ) : (
            history.map(entry => (
              <button key={entry.id} onClick={() => { onRestore(entry.investigation); onClose(); }}
                className="w-full text-left p-3 rounded-lg bg-gray-800 border border-gray-700
                  hover:border-blue-500 hover:bg-gray-750 transition-colors space-y-1.5 group">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-white group-hover:text-blue-300 line-clamp-1">
                    {entry.title || entry.technology}
                  </p>
                  {entry.resolved && (
                    <span className="text-xs text-green-400 bg-green-900/30 border border-green-700/40 px-1.5 py-0.5 rounded shrink-0">
                      ✓ Resolved
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${severityColor[entry.severity] ?? severityColor.unknown}`}>
                    {entry.severity}
                  </span>
                  <span className="text-xs text-gray-500">iter {entry.iteration}</span>
                  <span className="text-xs text-gray-600">
                    {new Date(entry.savedAt).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        {history.length > 0 && (
          <div className="px-4 py-3 border-t border-gray-700">
            <button onClick={handleClear}
              className="text-xs text-red-400 hover:text-red-300 transition-colors">
              🗑 Clear all history
            </button>
          </div>
        )}
      </aside>
    </>
  );
}

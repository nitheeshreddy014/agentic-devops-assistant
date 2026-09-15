'use client';
import { useState } from 'react';
import type { AgentMessage } from '@/lib/types';

interface Props { messages: AgentMessage[] }

const AGENT_ICONS: Record<string, string> = {
  triage: '🔍', planner: '📋', log_analysis: '📊',
  rag_knowledge: '📚', root_cause: '🎯',
  troubleshooting: '🔧', safety_reviewer: '🛡', report: '📝',
};
const STATUS_CLS: Record<string, string> = {
  running: 'text-blue-400 animate-pulse', complete: 'text-green-400',
  error: 'text-red-400', pending: 'text-gray-500',
};
const STATUS_ICON: Record<string, string> = {
  running: '⟳', complete: '✓', error: '✗', pending: '○',
};

export default function AgentTimeline({ messages }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);
  if (!messages || messages.length === 0) return null;

  // Deduplicate: for each agent+phase pair keep only the LAST message.
  // The backend appends running → (error →) complete in sequence, so the last
  // entry for a given agent+phase is always the terminal state. Showing every
  // intermediate "running" entry produces permanently-stuck spinning rows.
  const deduped: AgentMessage[] = [];
  const seen = new Map<string, number>(); // key → index in deduped
  for (const m of messages) {
    const key = `${m.agent_name ?? m.agent}::${m.phase}`;
    if (seen.has(key)) {
      deduped[seen.get(key)!] = m; // overwrite with newer entry
    } else {
      seen.set(key, deduped.length);
      deduped.push(m);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4" role="log" aria-label="Agent activity timeline">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">🤖 Agent Activity</h3>
      <ol className="space-y-1.5">
        {deduped.map((m, i) => {
          // agent field may be absent in older backend responses — fall back to agent_name
          const agentLabel = m.agent ?? m.agent_name ?? '';
          const key  = Object.keys(AGENT_ICONS).find(k => agentLabel.toLowerCase().includes(k)) ?? '';
          const icon = AGENT_ICONS[key] ?? '🤖';
          const st   = m.status ?? 'complete';
          const dur  = m.duration_ms != null ? `${(m.duration_ms / 1000).toFixed(1)}s` : null;
          const open = expanded === i;
          return (
            <li key={i}>
              <button onClick={() => setExpanded(open ? null : i)} aria-expanded={open}
                className="w-full flex items-start gap-3 text-left hover:bg-gray-800/50 rounded-lg px-2 py-1.5 transition-colors group">
                <span className="text-lg leading-5 shrink-0 mt-0.5">{icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-white">{agentLabel}</span>
                    {dur && <span className="text-xs text-gray-600">{dur}</span>}
                    <span className={`text-xs ml-auto ${STATUS_CLS[st] ?? STATUS_CLS.complete}`}>
                      {STATUS_ICON[st] ?? '✓'} {st}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 truncate mt-0.5 group-hover:text-gray-300">{m.message}</p>
                </div>
              </button>
              {open && (
                <div className="ml-10 mt-1 mb-2 p-3 bg-gray-800 rounded-lg border border-gray-700 text-xs text-gray-300 whitespace-pre-wrap break-words">
                  {m.message}
                  {st === 'error' && (m as any).error && (
                    <p className="mt-2 text-red-300 border-t border-red-700/40 pt-2">Error: {(m as any).error}</p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

'use client';
import type { AgentMessage } from '@/lib/types';

const ICONS: Record<string, string> = { running: '⟳', complete: '✓', error: '✗', skipped: '–' };
const COLORS: Record<string, string> = {
  running: 'text-blue-400', complete: 'text-green-400',
  error: 'text-red-400',    skipped: 'text-gray-500',
};

interface Props { messages: AgentMessage[]; isLoading?: boolean }

export default function AgentTimeline({ messages, isLoading }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
        🤖 Agent Timeline
        {isLoading && <span className="text-blue-400 text-xs animate-pulse">● investigating…</span>}
      </h3>
      {messages.length === 0 && <p className="text-xs text-gray-500">Waiting for agents to start…</p>}
      <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
        {messages.map((m, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className={`mt-0.5 w-4 shrink-0 font-mono ${COLORS[m.status] ?? 'text-gray-400'}`}>
              {ICONS[m.status] ?? '?'}
            </span>
            <div className="flex-1 min-w-0">
              <span className="text-blue-300 font-medium">{m.agent_name}</span>
              <span className="text-gray-600 mx-1">·</span>
              <span className="text-gray-300">{m.message}</span>
            </div>
            <span className="text-gray-600 shrink-0">{new Date(m.timestamp).toLocaleTimeString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

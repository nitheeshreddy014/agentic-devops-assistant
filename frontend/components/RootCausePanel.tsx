'use client';
import { useState } from 'react';
import type { RootCause, Citation } from '@/lib/types';

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000); }}
      className="shrink-0 text-xs px-2 py-0.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors ml-2">
      {ok ? '✓' : '⧉'}
    </button>
  );
}

export default function RootCausePanel({ causes, citations }: { causes: RootCause[]; citations: Citation[] }) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <h3 className="text-lg font-semibold text-white mb-4">🎯 Probable Root Causes</h3>
      <div className="space-y-4">
        {causes.map((c) => (
          <div key={c.rank} className="border border-gray-700/70 rounded-lg p-4 bg-gray-800/30">
            <div className="flex items-start justify-between mb-2">
              <div className="flex gap-2 flex-1 min-w-0">
                <span className="text-gray-500 font-mono text-xs shrink-0 mt-0.5">#{c.rank}</span>
                <h4 className="text-white font-medium text-sm">{c.cause}</h4>
              </div>
              <span className={`text-xs font-bold shrink-0 ml-3 ${c.confidence >= 0.7 ? 'text-green-400' : c.confidence >= 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
                {Math.round(c.confidence * 100)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-700 rounded-full mb-3">
              <div className={`h-full rounded-full ${c.confidence >= 0.7 ? 'bg-green-500' : c.confidence >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`}
                style={{ width: `${c.confidence * 100}%` }} />
            </div>
            {c.supporting_evidence.length > 0 && (
              <div className="mb-2">
                <p className="text-xs font-medium text-green-400 mb-1">✓ Supporting Evidence</p>
                {c.supporting_evidence.map((e, i) => <p key={i} className="text-xs text-gray-300 ml-2">• {e}</p>)}
              </div>
            )}
            {c.contradicting_evidence.length > 0 && (
              <div className="mb-2">
                <p className="text-xs font-medium text-red-400 mb-1">✗ Contradicting</p>
                {c.contradicting_evidence.map((e, i) => <p key={i} className="text-xs text-gray-300 ml-2">• {e}</p>)}
              </div>
            )}
            {c.confirmation_check && (
              <div className="mt-2 flex items-center bg-gray-800 rounded p-2 gap-2">
                <span className="text-gray-400 text-xs shrink-0">Confirm:</span>
                <code className="text-yellow-300 text-xs flex-1 break-all">{c.confirmation_check}</code>
                <CopyBtn text={c.confirmation_check} />
              </div>
            )}
          </div>
        ))}
      </div>
      {citations.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-xs font-medium text-gray-400 mb-2">📚 Runbook Citations</p>
          <div className="flex flex-wrap gap-2">
            {citations.map((c, i) => (
              <span key={i} title={c.snippet ?? ''} className="text-xs bg-gray-800 text-blue-300 px-2 py-1 rounded border border-gray-600">
                {c.filename}§{c.section}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

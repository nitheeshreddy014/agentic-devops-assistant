'use client';
import { useState } from 'react';
import type { ProbableCause, RunbookCitation } from '@/lib/types';

interface Props {
  causes: ProbableCause[];
  citations: RunbookCitation[];
  onConfirm?: (cause: ProbableCause) => void;
}

const CONF_CLS = (c: number) =>
  c >= 0.75 ? 'bg-green-500' : c >= 0.5 ? 'bg-yellow-500' : 'bg-red-500';

export default function RootCausePanel({ causes, citations, onConfirm }: Props) {
  const [minConf,   setMinConf]   = useState(0);
  const [confirmed, setConfirmed] = useState<number | null>(null);
  const [openCite,  setOpenCite]  = useState<string | null>(null);

  if (!causes || causes.length === 0) return null;

  const visible     = causes.filter(c => c.confidence >= minConf);
  const getCitation = (ref: string) =>
    citations.find(c => c.id === ref || c.title?.toLowerCase().includes(ref.toLowerCase()));

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h3 className="text-lg font-semibold text-white">🎯 Probable Root Causes</h3>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400 whitespace-nowrap">
            Min confidence: {Math.round(minConf * 100)}%
          </label>
          <input type="range" min={0} max={0.9} step={0.05} value={minConf}
            onChange={e => setMinConf(Number(e.target.value))}
            className="w-24 accent-blue-500" aria-label="Minimum confidence filter" />
        </div>
      </div>
      <div className="space-y-4">
        {visible.map((cause, idx) => (
          <div key={idx} className={`border rounded-xl p-4 space-y-3 transition-colors
            ${confirmed === cause.rank ? 'border-green-600 bg-green-900/15' : 'border-gray-700 bg-gray-800/40'}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-xs text-gray-500 font-mono">#{cause.rank}</span>
                  <h4 className="text-sm font-semibold text-white">{cause.cause}</h4>
                  {confirmed === cause.rank && (
                    <span className="text-xs text-green-400 bg-green-900/30 border border-green-700/40 px-2 py-0.5 rounded">✓ Confirmed</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 max-w-32 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${CONF_CLS(cause.confidence)}`}
                      style={{ width: `${cause.confidence * 100}%` }} />
                  </div>
                  <span className="text-xs text-gray-400">{Math.round(cause.confidence * 100)}%</span>
                </div>
              </div>
              <button onClick={() => { setConfirmed(cause.rank); onConfirm?.(cause); }}
                disabled={confirmed !== null}
                className={`shrink-0 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors
                  ${confirmed === cause.rank
                    ? 'border-green-600 text-green-400 bg-green-900/30 cursor-default'
                    : 'border-gray-600 text-gray-400 hover:border-green-500 hover:text-green-400 hover:bg-green-900/20'}`}>
                {confirmed === cause.rank ? '✓ Confirmed' : 'This was it →'}
              </button>
            </div>
            {cause.supporting_evidence.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Supporting evidence</p>
                {cause.supporting_evidence.map((e, j) => (
                  <p key={j} className="text-xs text-green-300/80 flex gap-1.5"><span className="text-green-600">+</span>{e}</p>
                ))}
              </div>
            )}
            {cause.contradicting_evidence.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Contradicting evidence</p>
                {cause.contradicting_evidence.map((e, j) => (
                  <p key={j} className="text-xs text-red-300/80 flex gap-1.5"><span className="text-red-600">−</span>{e}</p>
                ))}
              </div>
            )}
            {cause.confirmation_check && (
              <div className="bg-gray-950 rounded border border-gray-700 px-3 py-2">
                <p className="text-xs text-gray-500 mb-1">Confirmation check</p>
                <code className="text-green-300 text-xs font-mono">{cause.confirmation_check}</code>
                {cause.expected_result && <p className="text-xs text-gray-400 mt-1">Expected: {cause.expected_result}</p>}
              </div>
            )}
            {cause.citations && cause.citations.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {cause.citations.map((ref, j) => {
                  const cite = getCitation(ref);
                  return (
                    <button key={j} onClick={() => setOpenCite(openCite === ref ? null : ref)}
                      className="text-xs px-2 py-0.5 rounded border border-blue-700/50 text-blue-400 hover:bg-blue-900/20 transition-colors">
                      📚 {cite?.title ?? ref}
                    </button>
                  );
                })}
              </div>
            )}
            {cause.citations?.map(ref => {
              const cite = getCitation(ref);
              return openCite === ref && cite ? (
                <div key={ref} className="bg-gray-800 border border-blue-700/30 rounded-lg p-3 text-xs text-gray-300 space-y-1">
                  <p className="font-semibold text-blue-300">{cite.title}</p>
                  {cite.content && <p className="text-gray-400 leading-relaxed">{cite.content}</p>}
                  {cite.url && <a href={cite.url} target="_blank" rel="noopener noreferrer"
                    className="text-blue-400 underline">Open Runbook ↗</a>}
                </div>
              ) : null;
            })}
          </div>
        ))}
        {visible.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            No causes at {Math.round(minConf * 100)}%+ confidence. Lower the slider above.
          </p>
        )}
      </div>
    </div>
  );
}

'use client';
import { useState } from 'react';
import type { DiagnosticStep, RecommendedFix } from '@/lib/types';
import { Button } from '@/components/ui/Button';

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000); }}
      className="shrink-0 text-xs px-2 py-0.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors">
      {ok ? '✓' : '⧉'}
    </button>
  );
}

const RISK_COLORS: Record<string, string> = {
  low: 'text-green-400 bg-green-900/30 border-green-700/50',
  medium: 'text-yellow-400 bg-yellow-900/30 border-yellow-700/50',
  high: 'text-orange-400 bg-orange-900/30 border-orange-700/50',
  critical: 'text-red-400 bg-red-900/30 border-red-700/50',
};

interface Props {
  steps: DiagnosticStep[];
  fixes: RecommendedFix[];
  flaggedItems: string[];
  onContinue: (output: string) => Promise<void>;
  isLoading: boolean;
  iteration: number;
}

export default function DiagnosticPanel({ steps, fixes, flaggedItems, onContinue, isLoading, iteration }: Props) {
  const [output, setOutput] = useState('');

  return (
    <div className="space-y-4">
      {/* Safety flags */}
      {flaggedItems.length > 0 && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-red-300 mb-2">⛔ Human Approval Required</h3>
          {flaggedItems.map((f, i) => <p key={i} className="text-xs text-red-200">• {f}</p>)}
        </div>
      )}

      {/* Diagnostic steps */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
        <h3 className="text-lg font-semibold text-white mb-4">🔬 Diagnostic Steps</h3>
        <div className="space-y-3">
          {steps.map((s) => (
            <div key={s.step_number} className="border border-gray-700/60 rounded-lg p-3 bg-gray-800/30">
              <div className="flex items-start justify-between mb-2 gap-2">
                <p className="text-sm text-white flex-1">
                  <span className="text-gray-500 font-mono text-xs mr-2">#{s.step_number}</span>
                  {s.purpose}
                </p>
                <span className={`shrink-0 text-xs px-2 py-0.5 rounded border font-medium ${RISK_COLORS[s.risk_level] ?? RISK_COLORS.medium}`}>
                  {s.risk_level}
                  {s.requires_approval && ' ⚠'}
                </span>
              </div>
              <div className="flex items-center gap-2 bg-gray-900 rounded p-2 mb-2">
                <code className="text-green-300 text-xs font-mono flex-1 break-all">{s.command}</code>
                <CopyBtn text={s.command} />
              </div>
              <p className="text-xs text-gray-400"><span className="text-gray-500">Expected: </span>{s.expected_result}</p>
              {s.interpretation && <p className="text-xs text-gray-400 mt-0.5"><span className="text-gray-500">Interpret: </span>{s.interpretation}</p>}
              {s.requires_approval && <p className="text-xs text-orange-400 mt-1">⚠ Obtain approval before running in production.</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Recommended fixes */}
      {fixes.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">🔧 Recommended Fixes</h3>
          <div className="space-y-3">
            {fixes.map((fix, i) => (
              <div key={i} className="border border-gray-700/60 rounded-lg p-3 bg-gray-800/30">
                <div className="flex items-start justify-between mb-1 gap-2">
                  <h4 className="text-sm font-medium text-white flex-1">{fix.title}</h4>
                  <span className={`shrink-0 text-xs px-2 py-0.5 rounded border ${RISK_COLORS[fix.risk_level] ?? RISK_COLORS.medium}`}>
                    {fix.risk_level}{fix.requires_approval && ' ⚠'}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mb-2">{fix.description}</p>
                {fix.estimated_impact && <p className="text-xs text-yellow-400 mb-2">Impact: {fix.estimated_impact}</p>}
                <div className="space-y-1 mb-2">
                  {fix.steps.map((step, j) => (
                    <div key={j} className="flex items-center gap-2 text-xs">
                      <span className="text-gray-500 shrink-0">{j + 1}.</span>
                      <code className="text-gray-300 flex-1 break-all">{step}</code>
                      <CopyBtn text={step} />
                    </div>
                  ))}
                </div>
                {fix.rollback_steps.length > 0 && (
                  <details className="mt-1">
                    <summary className="text-xs text-blue-400 cursor-pointer select-none">↩ Rollback steps</summary>
                    <div className="mt-1 pl-2 space-y-0.5">
                      {fix.rollback_steps.map((s, j) => <p key={j} className="text-xs text-gray-400">• {s}</p>)}
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Continue investigation */}
      <div className="bg-gray-900 border border-blue-700/40 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-blue-300 mb-1">▶ Continue Investigation — Iteration {iteration}</h3>
        <p className="text-xs text-gray-400 mb-3">
          Run the diagnostic commands above and paste the output here. The agents will update their analysis.
        </p>
        <textarea
          value={output}
          onChange={(e) => setOutput(e.target.value)}
          placeholder="Paste command output here…"
          rows={5}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-xs font-mono placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none resize-y mb-3"
        />
        <Button onClick={() => onContinue(output.trim())} isLoading={isLoading} disabled={!output.trim()}>
          Continue Investigation →
        </Button>
      </div>
    </div>
  );
}

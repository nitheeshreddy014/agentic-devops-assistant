'use client';
import { useState } from 'react';

interface Props {
  missingInfo: string[];
  onSubmitAnswers?: (answers: Record<string, string>) => Promise<void>;
  isLoading?: boolean;
}

export default function MissingInfoPanel({ missingInfo, onSubmitAnswers, isLoading }: Props) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  if (!missingInfo || missingInfo.length === 0) return null;

  const setAnswer = (q: string, v: string) => setAnswers(a => ({ ...a, [q]: v }));
  const filled    = Object.values(answers).filter(v => v.trim()).length;
  const canSubmit = filled > 0 && !!onSubmitAnswers;

  return (
    <div className="bg-amber-950/30 border border-amber-700/40 rounded-xl p-5 space-y-4">
      <div className="flex items-start gap-3">
        <span className="text-xl">⚠️</span>
        <div>
          <h3 className="text-sm font-semibold text-amber-300">Missing Information</h3>
          <p className="text-xs text-amber-400/70 mt-0.5">Fill in answers inline — no need to restart the investigation.</p>
        </div>
      </div>
      <div className="space-y-3">
        {missingInfo.map((item, i) => (
          <div key={i} className="space-y-1.5">
            <label className="block text-xs text-gray-300">
              <span className="text-amber-400 mr-1">•</span>{item}
            </label>
            <input type="text" value={answers[item] ?? ''} onChange={e => setAnswer(item, e.target.value)}
              placeholder={`Answer for: ${item.slice(0, 60)}…`}
              className="w-full px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-white
                text-xs placeholder-gray-600 focus:ring-2 focus:ring-amber-500 focus:outline-none" />
          </div>
        ))}
      </div>
      {onSubmitAnswers && (
        <button onClick={() => onSubmitAnswers(answers)} disabled={!canSubmit || isLoading}
          className="w-full py-2 rounded-lg bg-amber-700 hover:bg-amber-600 disabled:opacity-50
            disabled:cursor-not-allowed text-white text-sm font-medium transition-colors">
          {isLoading ? '⏳ Re-analysing…' : `✓ Submit ${filled} Answer${filled !== 1 ? 's' : ''} → Re-run Analysis`}
        </button>
      )}
    </div>
  );
}

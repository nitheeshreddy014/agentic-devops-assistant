'use client';
import { useState, useEffect } from 'react';
import type { DiagnosticStep, RecommendedFix, StepFeedback, StepStatus } from '@/lib/types';
import { Button } from '@/components/ui/Button';

const STATUS_CFG: Record<StepStatus, { icon: string; label: string; cls: string }> = {
  pending:    { icon: '○', label: 'Pending',    cls: 'text-gray-400 border-gray-600 bg-gray-800' },
  passed:     { icon: '✓', label: 'Passed',     cls: 'text-green-400 border-green-600 bg-green-900/30' },
  failed:     { icon: '✗', label: 'Failed',     cls: 'text-red-400 border-red-600 bg-red-900/30' },
  'cant-run': { icon: '⊘', label: "Can't Run",  cls: 'text-yellow-400 border-yellow-600 bg-yellow-900/30' },
};
const RISK: Record<string, string> = {
  low:      'text-green-400 bg-green-900/30 border-green-700/50',
  medium:   'text-yellow-400 bg-yellow-900/30 border-yellow-700/50',
  high:     'text-orange-400 bg-orange-900/30 border-orange-700/50',
  critical: 'text-red-400 bg-red-900/30 border-red-700/50',
};

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1500); }}
      className="shrink-0 text-xs px-2 py-0.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors">
      {ok ? '✓' : '⧉ Copy'}
    </button>
  );
}

interface Props {
  steps: DiagnosticStep[];
  fixes: RecommendedFix[];
  flaggedItems: string[];
  onContinue: (output: string, feedback: StepFeedback[]) => Promise<void>;
  isLoading: boolean;
  iteration: number;
}

function buildPlaceholder(steps: DiagnosticStep[]): string {
  return steps.map(s => `# Step ${s.step_number}: ${s.purpose}\n# $ ${s.command}\n\n`).join('');
}

export default function DiagnosticPanel({ steps, fixes, flaggedItems, onContinue, isLoading, iteration }: Props) {
  const [output,   setOutput]   = useState('');
  const [feedback, setFeedback] = useState<StepFeedback[]>([]);

  useEffect(() => {
    setFeedback(steps.map(s => ({ stepNumber: s.step_number, status: 'pending' as StepStatus })));
    setOutput('');
  }, [steps]);

  const getStatus = (n: number): StepStatus =>
    feedback.find(f => f.stepNumber === n)?.status ?? 'pending';

  const toggle = (n: number, s: StepStatus) =>
    setFeedback(fb => fb.map(f => f.stepNumber === n ? { ...f, status: f.status === s ? 'pending' : s } : f));

  const hasMarked = feedback.some(f => f.status === 'failed' || f.status === 'cant-run');
  const canSubmit = output.trim().length > 0 || hasMarked;

  const handleSubmit = async () => {
    const markedLines = feedback.filter(f => f.status !== 'pending')
      .map(f => `Step ${f.stepNumber}: ${f.status.toUpperCase()}`);
    const full = [output.trim(), markedLines.length ? `--- Step Feedback ---\n${markedLines.join('\n')}` : '']
      .filter(Boolean).join('\n\n');
    await onContinue(full, feedback);
  };

  const safeSteps   = steps.filter(s => s.is_safe_readonly);
  const dangerSteps = steps.filter(s => !s.is_safe_readonly);

  const StepCard = ({ s }: { s: DiagnosticStep }) => {
    const st  = getStatus(s.step_number);
    const cfg = STATUS_CFG[st];
    return (
      <div className={`rounded-lg border p-4 space-y-3 transition-all
        ${st === 'passed'    ? 'border-green-700/50 bg-green-900/10'
        : st === 'failed'   ? 'border-red-700/50   bg-red-900/10'
        : st === 'cant-run' ? 'border-yellow-700/50 bg-yellow-900/10'
        : 'border-gray-700 bg-gray-800/40'}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <span className={`shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold border ${cfg.cls}`}>
              {cfg.icon}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white">Step {s.step_number}: {s.purpose}</p>
              <div className="flex items-center gap-2 flex-wrap mt-1">
                <span className={`text-xs px-2 py-0.5 rounded border ${RISK[s.risk_level] ?? RISK.medium}`}>{s.risk_level} risk</span>
                {s.is_safe_readonly  && <span className="text-xs text-green-400">🔒 read-only</span>}
                {s.requires_approval && <span className="text-xs text-orange-400">⚠ needs approval</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0 flex-wrap">
            {(['passed', 'failed', 'cant-run'] as StepStatus[]).map(opt => (
              <button key={opt} onClick={() => toggle(s.step_number, opt)}
                className={`text-xs px-2 py-1 rounded border transition-colors
                  ${st === opt ? STATUS_CFG[opt].cls : 'border-gray-600 text-gray-500 bg-gray-900 hover:border-gray-400'}`}>
                {STATUS_CFG[opt].icon} {STATUS_CFG[opt].label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-start gap-2 bg-gray-950 rounded border border-gray-700 px-3 py-2.5">
          <code className="text-green-300 text-xs font-mono flex-1 break-all whitespace-pre-wrap">{s.command}</code>
          <CopyBtn text={s.command} />
        </div>
        <div className="text-xs text-gray-400 space-y-1">
          <p><span className="text-gray-500">Expected: </span>{s.expected_result}</p>
          {s.interpretation && <p><span className="text-gray-500">Interpret: </span>{s.interpretation}</p>}
          {s.requires_approval && s.approval_reason && (
            <p className="text-orange-300/80 bg-orange-900/20 border border-orange-700/30 rounded p-2 mt-1">⚠ {s.approval_reason}</p>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-5" role="region" aria-label="Diagnostic Steps">
      {flaggedItems.length > 0 && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-xl p-4" role="alert">
          <h3 className="text-sm font-semibold text-red-300 mb-2">⛔ Human Approval Required</h3>
          {flaggedItems.map((f, i) => <p key={i} className="text-xs text-red-200">• {f}</p>)}
        </div>
      )}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">🔬 Diagnostic Steps
          <span className="ml-2 text-sm font-normal text-gray-400">— Iteration {iteration}</span>
        </h3>
        <span className="text-xs text-gray-500">{steps.length} step{steps.length !== 1 ? 's' : ''}</span>
      </div>
      {safeSteps.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-green-400 uppercase tracking-wider">🔒 Safe / Read-only — Run First</p>
          {safeSteps.map(s => <StepCard key={s.step_number} s={s} />)}
        </div>
      )}
      {dangerSteps.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-orange-400 uppercase tracking-wider">⚠ Require Approval — Run After</p>
          {dangerSteps.map(s => <StepCard key={s.step_number} s={s} />)}
        </div>
      )}
      {fixes.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">🔧 Recommended Fixes</h3>
          <div className="space-y-3">
            {fixes.map((fix, i) => (
              <div key={i} className="border border-gray-700/60 rounded-lg p-3 bg-gray-800/30">
                <div className="flex items-start justify-between mb-1 gap-2">
                  <h4 className="text-sm font-medium text-white flex-1">{fix.title}</h4>
                  <span className={`shrink-0 text-xs px-2 py-0.5 rounded border ${RISK[fix.risk_level] ?? RISK.medium}`}>
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
                    <summary className="text-xs text-blue-400 cursor-pointer">↩ Rollback steps</summary>
                    <div className="mt-1 pl-2 space-y-0.5">
                      {fix.rollback_steps.map((rs, j) => <p key={j} className="text-xs text-gray-400">• {rs}</p>)}
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="bg-gray-900 border border-blue-700/40 rounded-xl p-5 space-y-3">
        <div>
          <h3 className="text-sm font-semibold text-blue-300">▶ Continue Investigation — Iteration {iteration}</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Paste output below, OR mark steps as Failed / Can't Run above — both feed the AI agents.
          </p>
        </div>
        <textarea value={output} onChange={e => setOutput(e.target.value)}
          placeholder={buildPlaceholder(steps)} rows={6}
          aria-label="Paste diagnostic command output"
          className="w-full px-3 py-2.5 bg-gray-800 border border-gray-600 rounded-lg text-white
            text-xs font-mono placeholder-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none resize-y" />
        {!canSubmit && (
          <p className="text-xs text-gray-500">
            💡 Can't run commands? Mark steps Failed or Can't Run above to continue anyway.
          </p>
        )}
        <Button onClick={handleSubmit} isLoading={isLoading} disabled={!canSubmit || isLoading} size="lg" className="w-full">
          Continue Investigation → {hasMarked && !output.trim() ? '(via step feedback)' : ''}
        </Button>
      </div>
    </div>
  );
}

'use client';
/**
 * EscalationPanel — shown when user is stuck after ≥2 iterations.
 * Provides: export report, restart with context, try next root cause, create Jira ticket.
 */
import { useState } from 'react';
import type { InvestigationResponse } from '@/lib/types';

interface Props {
  investigation: InvestigationResponse;
  onRestartWithContext: () => void;
  onTryNextCause: () => void;
  onExportReport: () => void;
}

export default function EscalationPanel({ investigation, onRestartWithContext, onTryNextCause, onExportReport }: Props) {
  const [jiraOpen, setJiraOpen] = useState(false);
  const [copied, setCopied]     = useState(false);

  const copyJiraText = () => {
    const causes = investigation.probable_causes.map(c => `• ${c.cause} (${Math.round(c.confidence * 100)}%)`).join('\n');
    const steps  = investigation.diagnostic_steps.map(s => `${s.step_number}. ${s.command}`).join('\n');
    const text = [
      `**Incident:** ${investigation.issue_category}`,
      `**Severity:** ${investigation.severity.toUpperCase()}`,
      `**Session:** ${investigation.session_id}`,
      `**Iteration:** ${investigation.iteration}`,
      '',
      '**Probable Causes:**',
      causes,
      '',
      '**Diagnostic Steps Run:**',
      steps,
      '',
      '**Affected Services:**',
      investigation.affected_services.join(', ') || 'Unknown',
    ].join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-red-950/30 border border-red-700/50 rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-2xl">🚨</span>
        <div>
          <h3 className="text-lg font-semibold text-red-300">Still Stuck? Here Are Your Options</h3>
          <p className="text-sm text-red-400/80 mt-0.5">
            After {investigation.iteration} iterations the issue isn&apos;t resolved — try one of these escalation paths.
          </p>
        </div>
      </div>

      {/* Action grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Export Report */}
        <button onClick={onExportReport}
          className="flex items-start gap-3 p-4 rounded-lg bg-gray-800 border border-gray-600 hover:border-blue-500 hover:bg-gray-750 transition-colors text-left group">
          <span className="text-xl shrink-0">📥</span>
          <div>
            <p className="text-sm font-medium text-white group-hover:text-blue-300">Download Full Report</p>
            <p className="text-xs text-gray-400 mt-0.5">Export all findings as Markdown for expert review or post-mortem</p>
          </div>
        </button>

        {/* Restart with context */}
        <button onClick={onRestartWithContext}
          className="flex items-start gap-3 p-4 rounded-lg bg-gray-800 border border-gray-600 hover:border-green-500 hover:bg-gray-750 transition-colors text-left group">
          <span className="text-xl shrink-0">🔄</span>
          <div>
            <p className="text-sm font-medium text-white group-hover:text-green-300">Restart With Context</p>
            <p className="text-xs text-gray-400 mt-0.5">Start a fresh investigation pre-filled with this session&apos;s findings</p>
          </div>
        </button>

        {/* Try next root cause */}
        {investigation.probable_causes.length > 1 && (
          <button onClick={onTryNextCause}
            className="flex items-start gap-3 p-4 rounded-lg bg-gray-800 border border-gray-600 hover:border-yellow-500 hover:bg-gray-750 transition-colors text-left group">
            <span className="text-xl shrink-0">🎯</span>
            <div>
              <p className="text-sm font-medium text-white group-hover:text-yellow-300">Try Next Root Cause</p>
              <p className="text-xs text-gray-400 mt-0.5">
                Root cause #1 wasn&apos;t it — explore root cause #2: &ldquo;{investigation.probable_causes[1]?.cause}&rdquo;
              </p>
            </div>
          </button>
        )}

        {/* Jira ticket */}
        <button onClick={() => setJiraOpen(o => !o)}
          className="flex items-start gap-3 p-4 rounded-lg bg-gray-800 border border-gray-600 hover:border-purple-500 hover:bg-gray-750 transition-colors text-left group">
          <span className="text-xl shrink-0">🎫</span>
          <div>
            <p className="text-sm font-medium text-white group-hover:text-purple-300">Copy Jira / Ticket Text</p>
            <p className="text-xs text-gray-400 mt-0.5">Pre-formatted incident summary ready to paste into any ticket system</p>
          </div>
        </button>
      </div>

      {/* Jira copy panel */}
      {jiraOpen && (
        <div className="rounded-lg bg-gray-900 border border-gray-700 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-gray-300">📋 Ticket Summary</p>
            <button onClick={copyJiraText}
              className="text-xs px-3 py-1 bg-purple-700 hover:bg-purple-600 text-white rounded transition-colors">
              {copied ? '✓ Copied!' : 'Copy to clipboard'}
            </button>
          </div>
          <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono leading-relaxed max-h-40 overflow-y-auto">
{`Incident: ${investigation.issue_category}
Severity: ${investigation.severity.toUpperCase()}
Session: ${investigation.session_id}
Iteration: ${investigation.iteration}

Probable Causes:
${investigation.probable_causes.map(c => `• ${c.cause} (${Math.round(c.confidence * 100)}%)`).join('\n')}

Affected Services: ${investigation.affected_services.join(', ') || 'Unknown'}
Error Codes: ${investigation.error_codes.join(', ') || 'None'}`}
          </pre>
        </div>
      )}

      {/* Tip */}
      <p className="text-xs text-gray-500 border-t border-gray-700/50 pt-3">
        💡 Tip: If you&apos;re escalating to a team-mate, download the report first — it contains all agent findings, root cause analysis, and steps already attempted.
      </p>
    </div>
  );
}

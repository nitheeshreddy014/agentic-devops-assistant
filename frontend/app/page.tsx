'use client';
/**
 * Main page - wires ALL improvements together:
 * Session persistence (localStorage)
 * Investigation history drawer
 * Escalation panel after 2+ failed iterations
 * Restart with context carried over
 * Missing info inline answers
 * Browser notification on completion
 * Keyboard shortcuts (Cmd+Enter, Escape, Cmd+K)
 * Error retry with specific messaging
 * Mark resolved
 */
import { useState, useEffect, useCallback } from 'react';
import type { InvestigationResponse, StartInvestigationRequest, StepFeedback } from '@/lib/types';
import { startInvestigation, continueInvestigation, checkHealth } from '@/lib/api';
import {
  saveActiveSession, loadActiveSession, clearActiveSession,
  saveToHistory, markHistoryResolved, clearFormDraft,
} from '@/lib/storage';
import { useNotification }      from '@/lib/hooks/useNotification';
import { useKeyboardShortcuts } from '@/lib/hooks/useKeyboardShortcuts';

import InvestigationForm from '@/components/InvestigationForm';
import DiagnosticPanel   from '@/components/DiagnosticPanel';
import RootCausePanel    from '@/components/RootCausePanel';
import MissingInfoPanel  from '@/components/MissingInfoPanel';
import AgentTimeline     from '@/components/AgentTimeline';
import FinalReport       from '@/components/FinalReport';
import EscalationPanel   from '@/components/EscalationPanel';
import HistoryDrawer     from '@/components/HistoryDrawer';
import GroqStatus        from '@/components/GroqStatus';

// ── helpers ──────────────────────────────────────────────────────────────────
function getErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes('429'))        return 'Rate limited by Groq. Please wait 30 seconds and retry.';
    if (msg.includes('503'))        return 'Backend is starting up (cold start). Retrying...';
    if (msg.includes('401'))        return 'Invalid Groq API key. Click the status badge above for setup help.';
    if (msg.includes('network'))    return 'Network error — is the API server running?';
    return msg;
  }
  return 'Unknown error occurred.';
}

function buildPrefillFromContext(inv: InvestigationResponse): Partial<StartInvestigationRequest> {
  const causes = inv.probable_causes.map(c => c.cause).join('; ');
  return {
    problem_title:       `[Retry] ${inv.issue_category}`,
    problem_description: `Previous investigation (session ${inv.session_id.slice(0, 8)}) found these root causes: ${causes}. ` +
                         `None resolved the issue after ${inv.iteration} iterations. ` +
                         `Please investigate further with fresh perspective.`,
    technology:          inv.issue_category?.split(':')[0]?.toLowerCase().trim() ?? 'kubernetes',
    environment:         'production',
    recent_changes:      `Previous investigation: ${inv.iteration} iterations, severity: ${inv.severity}`,
  };
}

// ── component ────────────────────────────────────────────────────────────────
export default function Home() {
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [isLoading,     setIsLoading]     = useState(false);
  const [error,         setError]         = useState<string | null>(null);
  const [groqOk,        setGroqOk]        = useState<boolean | null>(null);
  const [groqModel,     setGroqModel]     = useState<string | undefined>(undefined);
  const [historyOpen,   setHistoryOpen]   = useState(false);
  const [resolved,      setResolved]      = useState(false);
  const [prefill,       setPrefill]       = useState<Partial<StartInvestigationRequest> | undefined>(undefined);
  const [stuckIter,     setStuckIter]     = useState(0); // track iterations without progress
  const [retryCount,    setRetryCount]    = useState(0);

  const { notify } = useNotification();

  // Restore active session on mount
  useEffect(() => {
    const saved = loadActiveSession();
    if (saved) setInvestigation(saved);
  }, []);

  // Health check on mount
  useEffect(() => {
    checkHealth()
      .then(h => { setGroqOk(h.groq_configured); setGroqModel(h.model); })
      .catch(() => setGroqOk(false));
  }, []);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onEscape:  () => { setError(null); setHistoryOpen(false); },
    onHistory: () => setHistoryOpen(o => !o),
  });

  // ── Start investigation ───────────────────────────────────────────────────
  const handleStart = useCallback(async (req: StartInvestigationRequest) => {
    setIsLoading(true);
    setError(null);
    setResolved(false);
    setStuckIter(0);
    setPrefill(undefined);
    try {
      const inv = await startInvestigation(req);
      setInvestigation(inv);
      saveActiveSession(inv);
      saveToHistory(inv);
      notify('Investigation complete', `Found ${inv.probable_causes.length} probable cause(s) — ${inv.severity} severity`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [notify]);

  // ── Continue investigation ────────────────────────────────────────────────
  const handleContinue = useCallback(async (output: string, _feedback: StepFeedback[]) => {
    if (!investigation) return;
    setIsLoading(true);
    setError(null);
    try {
      const inv = await continueInvestigation(investigation.investigation_token, output);
      setInvestigation(inv);
      saveActiveSession(inv);
      saveToHistory(inv);
      // Track stuck iterations (no new root causes)
      if (inv.probable_causes.length <= (investigation.probable_causes.length) && inv.iteration > 2) {
        setStuckIter(s => s + 1);
      } else {
        setStuckIter(0);
      }
      notify('Iteration complete', `Iteration ${inv.iteration} done — ${inv.severity} severity`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [investigation, notify]);

  // ── Missing info answers ──────────────────────────────────────────────────
  const handleMissingInfo = useCallback(async (answers: Record<string, string>) => {
    if (!investigation) return;
    setIsLoading(true);
    setError(null);
    try {
      const answerText = Object.entries(answers)
        .map(([q, a]) => `${q}: ${a}`)
        .join('\n');
      const inv = await continueInvestigation(investigation.investigation_token, answerText);
      setInvestigation(inv);
      saveActiveSession(inv);
      saveToHistory(inv);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [investigation]);

  // ── Mark resolved ─────────────────────────────────────────────────────────
  const handleMarkResolved = useCallback(() => {
    if (!investigation) return;
    setResolved(true);
    markHistoryResolved(investigation.session_id);
    saveToHistory(investigation, true);
    clearActiveSession();
  }, [investigation]);

  // ── Restart with context ──────────────────────────────────────────────────
  const handleRestartWithContext = useCallback(() => {
    if (!investigation) return;
    const pf = buildPrefillFromContext(investigation);
    setPrefill(pf);
    setInvestigation(null);
    setResolved(false);
    setStuckIter(0);
    clearActiveSession();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [investigation]);

  // ── Try next root cause ───────────────────────────────────────────────────
  const handleTryNextCause = useCallback(async () => {
    if (!investigation || investigation.probable_causes.length < 2) return;
    const nextCause = investigation.probable_causes[1];
    const prompt = `The first root cause "${investigation.probable_causes[0]?.cause}" did not resolve the issue. ` +
                   `Please now investigate root cause #2: "${nextCause.cause}" ` +
                   `and provide new diagnostic steps focused on this.`;
    await handleContinue(prompt, []);
  }, [investigation, handleContinue]);

  // ── Export report ─────────────────────────────────────────────────────────
  const handleExportReport = useCallback(() => {
    if (!investigation) return;
    const lines = [
      `# Incident Report`,
      `Session: ${investigation.session_id}`,
      `Severity: ${investigation.severity}`,
      `Iteration: ${investigation.iteration}`,
      ``,
      `## Root Causes`,
      ...investigation.probable_causes.map(c => `- ${c.cause} (${Math.round(c.confidence * 100)}%)`),
      ``,
      `## Diagnostic Steps`,
      ...investigation.diagnostic_steps.map(s => `${s.step_number}. ${s.command}`),
    ].join('\n');
    const blob = new Blob([lines], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `incident-${investigation.session_id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [investigation]);

  // ── New investigation ─────────────────────────────────────────────────────
  const handleNew = useCallback(() => {
    setInvestigation(null);
    setError(null);
    setResolved(false);
    setStuckIter(0);
    setPrefill(undefined);
    clearActiveSession();
    clearFormDraft();   // prevent old form data reloading on remount
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // ── Retry after error ─────────────────────────────────────────────────────
  const handleRetry = useCallback(() => {
    setError(null);
    setRetryCount(r => r + 1);
  }, []);

  const showEscalation = (investigation?.iteration ?? 0) >= 2 && stuckIter >= 1 && !resolved;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Top bar */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="text-xl">🛠</span>
            <div>
              <h1 className="text-base font-bold text-white leading-tight">
                Agentic DevOps Assistant
              </h1>
              <p className="text-xs text-gray-500 hidden sm:block">
                AI-powered incident investigation
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {groqOk !== null && <GroqStatus configured={groqOk} model={groqModel} />}
            <button
              onClick={() => setHistoryOpen(true)}
              title="Investigation History (Cmd+K)"
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-600 text-gray-400
                hover:border-blue-500 hover:text-blue-300 transition-colors"
              aria-label="Open investigation history"
            >
              History
            </button>
            {investigation && (
              <button onClick={handleNew}
                className="text-xs px-3 py-1.5 rounded-lg border border-gray-600 text-gray-400
                  hover:border-red-500 hover:text-red-300 transition-colors">
                New Investigation
              </button>
            )}
          </div>
        </div>
      </header>

      {/* History drawer */}
      <HistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onRestore={inv => { setInvestigation(inv); setHistoryOpen(false); }}
      />

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">

        {/* Error banner */}
        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 flex items-start justify-between gap-3"
            role="alert" aria-live="assertive">
            <div className="flex items-start gap-2">
              <span className="text-red-400 shrink-0 mt-0.5">⚠</span>
              <p className="text-sm text-red-300">{error}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button onClick={handleRetry}
                className="text-xs px-3 py-1 bg-red-700 hover:bg-red-600 text-white rounded transition-colors">
                Retry
              </button>
              <button onClick={() => setError(null)}
                className="text-gray-400 hover:text-white text-lg leading-none"
                aria-label="Dismiss error">&times;</button>
            </div>
          </div>
        )}

        {/* Restored session banner */}
        {investigation && !isLoading && (
          <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg px-4 py-2.5 flex items-center justify-between text-xs flex-wrap gap-2"
            aria-live="polite">
            <span className="text-blue-300">
              Active session: <span className="font-mono">{investigation.session_id.slice(0, 12)}…</span>
              {' '}· Iteration {investigation.iteration} · {investigation.severity} severity
            </span>
            <button onClick={handleNew} className="text-gray-400 hover:text-white">
              Start fresh
            </button>
          </div>
        )}

        {!investigation ? (
          /* ── FORM ── */
          <InvestigationForm
            onSubmit={handleStart}
            isLoading={isLoading}
            prefill={prefill}
          />
        ) : (
          /* ── RESULTS ── */
          <div className="space-y-6">
            {/* Agent timeline */}
            {investigation.agent_messages?.length > 0 && (
              <AgentTimeline messages={investigation.agent_messages} />
            )}

            {/* Missing info — interactive */}
            {investigation.missing_info?.length > 0 && (
              <MissingInfoPanel
                missingInfo={investigation.missing_info}
                onSubmitAnswers={handleMissingInfo}
                isLoading={isLoading}
              />
            )}

            {/* Root causes */}
            {investigation.probable_causes?.length > 0 && (
              <RootCausePanel
                causes={investigation.probable_causes}
                citations={(investigation.runbook_citations ?? []).map(c => ({
                  id:      (c as any).id      ?? (c as any).filename ?? '',
                  title:   (c as any).title   ?? (c as any).section  ?? (c as any).filename ?? '',
                  content: (c as any).content ?? (c as any).snippet,
                  url:     (c as any).url,
                }))}
                onConfirm={() => {}}
              />
            )}

            {/* Escalation panel — shown when stuck */}
            {showEscalation && (
              <EscalationPanel
                investigation={investigation}
                onRestartWithContext={handleRestartWithContext}
                onTryNextCause={handleTryNextCause}
                onExportReport={handleExportReport}
              />
            )}

            {/* Diagnostic panel or Final report */}
            {investigation.status === 'completed' ? (
              <FinalReport
                investigation={investigation}
                onMarkResolved={handleMarkResolved}
                resolved={resolved}
              />
            ) : (
              <DiagnosticPanel
                steps={investigation.diagnostic_steps ?? []}
                fixes={investigation.recommended_fixes ?? []}
                flaggedItems={investigation.flagged_for_human_review ?? []}
                onContinue={handleContinue}
                isLoading={isLoading}
                iteration={investigation.iteration}
              />
            )}
          </div>
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-20 flex items-center justify-center"
            aria-live="polite" aria-label="Investigation in progress">
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 flex flex-col items-center gap-4 shadow-2xl">
              <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <div className="text-center">
                <p className="text-sm font-medium text-white">
                  {investigation ? `Running iteration ${(investigation.iteration ?? 0) + 1}…` : 'Starting investigation…'}
                </p>
                <p className="text-xs text-gray-400 mt-1">8 AI agents are analysing your incident</p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-16">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between text-xs text-gray-600 flex-wrap gap-2">
          <span>Agentic DevOps Assistant · Powered by Groq + LangGraph</span>
          <span>Cmd+K — History &nbsp;|&nbsp; Cmd+Enter — Submit &nbsp;|&nbsp; Esc — Dismiss</span>
        </div>
      </footer>
    </div>
  );
}

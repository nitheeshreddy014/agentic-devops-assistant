'use client';
import { useState, useEffect } from 'react';
import type { InvestigationResponse, StartInvestigationRequest } from '@/lib/types';
import { startInvestigation, continueInvestigation, checkHealth } from '@/lib/api';
import InvestigationForm   from '@/components/InvestigationForm';
import AgentTimeline       from '@/components/AgentTimeline';
import RootCausePanel      from '@/components/RootCausePanel';
import DiagnosticPanel     from '@/components/DiagnosticPanel';
import FinalReport         from '@/components/FinalReport';
import GroqStatus          from '@/components/GroqStatus';
import MissingInfoPanel    from '@/components/MissingInfoPanel';

export default function Home() {
  const [inv, setInv]             = useState<InvestigationResponse | null>(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [llmOk, setLlmOk]        = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth()
      .then(h => setLlmOk(h.llm_configured))
      .catch(() => setLlmOk(false));
  }, []);

  const run = async <T,>(fn: () => Promise<T>) => {
    setLoading(true); setError(null);
    try { return await fn(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); return null; }
    finally { setLoading(false); }
  };

  const handleStart = async (req: StartInvestigationRequest) => {
    const resp = await run(() => startInvestigation(req));
    if (resp) setInv(resp);
  };

  const handleContinue = async (diagnosticOutput: string) => {
    if (!inv) return;
    const resp = await run(() => continueInvestigation(inv.investigation_token, diagnosticOutput));
    if (resp) setInv(resp);
  };

  const handleNew = () => { setInv(null); setError(null); };

  return (
    <main className="min-h-screen bg-gray-950">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">

        {/* ── Header ─────────────────────────────────────────────── */}
        <header>
          <h1 className="text-3xl font-bold text-white">
            🔍 Agentic DevOps Troubleshooting Assistant
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            LangGraph orchestration · CrewAI specialists · LangChain/Groq LLM · BM25 RAG · MCP-compatible tools
          </p>
          {llmOk !== null && <GroqStatus configured={llmOk} />}
        </header>

        {/* ── Error banner ────────────────────────────────────────── */}
        {error && (
          <div className="p-4 bg-red-900/40 border border-red-600/50 rounded-lg text-red-200 text-sm">
            ⚠ {error}
          </div>
        )}

        {/* ── Investigation form (idle state) ─────────────────────── */}
        {!inv && !loading && (
          <InvestigationForm onSubmit={handleStart} isLoading={loading} />
        )}

        {/* ── Loading placeholder ──────────────────────────────────── */}
        {loading && !inv && (
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-10 text-center">
            <svg className="animate-spin h-10 w-10 text-blue-400 mx-auto mb-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <p className="text-gray-300 font-medium">Agents investigating…</p>
            <p className="text-gray-500 text-sm mt-1">Triage → Plan → Analyse → RAG → Root Cause → Troubleshoot → Report</p>
          </div>
        )}

        {/* ── Investigation results ────────────────────────────────── */}
        {inv && (
          <div className="space-y-6">
            {/* Summary bar */}
            <div className="flex flex-wrap items-center gap-3 p-4 bg-gray-900 border border-gray-700 rounded-xl text-xs">
              <span className="text-gray-400">Category: <span className="text-white font-medium">{inv.issue_category}</span></span>
              <span className="text-gray-600">·</span>
              <span className="text-gray-400">Severity: <span className={`font-medium ${
                inv.severity === 'critical' ? 'text-red-400' :
                inv.severity === 'high'     ? 'text-orange-400' :
                inv.severity === 'medium'   ? 'text-yellow-400' : 'text-green-400'
              }`}>{inv.severity.toUpperCase()}</span></span>
              <span className="text-gray-600">·</span>
              <span className="text-gray-400">Iteration: <span className="text-white font-medium">{inv.iteration}</span></span>
              {!inv.llm_configured && (
                <span className="text-yellow-400">⚠ AI analysis unavailable — set GROQ_API_KEY</span>
              )}
            </div>

            <AgentTimeline  messages={inv.agent_messages} isLoading={loading} />
            {inv.missing_info.length > 0   && <MissingInfoPanel missingInfo={inv.missing_info} />}
            {inv.probable_causes.length > 0 && <RootCausePanel causes={inv.probable_causes} citations={inv.runbook_citations} />}
            {inv.diagnostic_steps.length > 0 && (
              <DiagnosticPanel
                steps={inv.diagnostic_steps}
                fixes={inv.recommended_fixes}
                flaggedItems={inv.flagged_items}
                onContinue={handleContinue}
                isLoading={loading}
                iteration={inv.iteration}
              />
            )}
            {inv.report && Object.keys(inv.report).length > 0 && <FinalReport report={inv.report} />}

            <button onClick={handleNew}
              className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
              🔄 New Investigation
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

'use client';
import React from 'react';

interface ReportData {
  title?: string;
  severity?: string;
  executive_summary?: string;
  probable_causes?: { rank?: number; cause: string; confidence?: number }[];
  recommended_fixes?: { title: string; description: string }[];
  rollback_guidance?: string;
  prevention_recommendations?: string[];
  runbook_citations?: { filename: string; section: string }[];
  investigation_date?: string;
  iteration?: number;
}

interface Props { report: ReportData }

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h4 className="text-sm font-semibold text-gray-300 mb-2 border-b border-gray-700 pb-1">{title}</h4>
      {children}
    </div>
  );
}

export default function FinalReport({ report }: Props) {
  const causes = report.probable_causes ?? [];
  const fixes = report.recommended_fixes ?? [];
  const citations = report.runbook_citations ?? [];

  return (
    <div className="bg-gray-900 border border-green-700/40 rounded-xl p-5">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Final Investigation Report</h3>
        <span className={`text-xs px-2 py-1 rounded border font-medium ${
          report.severity === 'critical' ? 'bg-red-900/60 text-red-300 border-red-700' :
          report.severity === 'high'     ? 'bg-orange-900/60 text-orange-300 border-orange-700' :
          report.severity === 'medium'   ? 'bg-yellow-900/60 text-yellow-300 border-yellow-700' :
                                           'bg-green-900/60 text-green-300 border-green-700'
        }`}>
          {String(report.severity ?? 'unknown').toUpperCase()}
        </span>
      </div>

      <h2 className="text-base font-bold text-white mb-4">{String(report.title ?? '')}</h2>

      {report.executive_summary ? (
        <Section title="Executive Summary">
          <p className="text-sm text-gray-300 leading-relaxed">{String(report.executive_summary)}</p>
        </Section>
      ) : null}

      {causes.length > 0 ? (
        <Section title="Probable Causes">
          {causes.map((c, i) => (
            <div key={i} className="mb-1 flex gap-2 text-sm">
              <span className="text-gray-500">#{c.rank ?? i + 1}</span>
              <span className="text-gray-200">
                {c.cause}{' '}
                <span className="text-blue-400 text-xs">({Math.round((c.confidence ?? 0) * 100)}%)</span>
              </span>
            </div>
          ))}
        </Section>
      ) : null}

      {fixes.length > 0 ? (
        <Section title="Recommended Fixes">
          {fixes.map((f, i) => (
            <div key={i} className="mb-2">
              <p className="text-sm font-medium text-white">{f.title}</p>
              <p className="text-xs text-gray-400">{f.description}</p>
            </div>
          ))}
        </Section>
      ) : null}

      {report.rollback_guidance ? (
        <Section title="Rollback Guidance">
          <p className="text-xs text-gray-300 leading-relaxed">{String(report.rollback_guidance)}</p>
        </Section>
      ) : null}

      {(report.prevention_recommendations ?? []).length > 0 ? (
        <Section title="Prevention">
          {(report.prevention_recommendations ?? []).map((r, i) => (
            <p key={i} className="text-xs text-gray-300">- {r}</p>
          ))}
        </Section>
      ) : null}

      {citations.length > 0 ? (
        <Section title="Runbook Citations">
          <div className="flex flex-wrap gap-2">
            {citations.map((c, i) => (
              <span key={i} className="text-xs bg-gray-800 text-blue-300 px-2 py-1 rounded border border-gray-600">
                {c.filename} - {c.section}
              </span>
            ))}
          </div>
        </Section>
      ) : null}

      <p className="text-xs text-gray-500 mt-4 pt-3 border-t border-gray-700">
        Generated: {String(report.investigation_date ?? new Date().toISOString())} - Iteration {String(report.iteration ?? 1)}
      </p>
    </div>
  );
}

/**
 * Tests for the EscalationPanel component (dead-end recovery).
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import EscalationPanel from '../components/EscalationPanel';
import type { InvestigationResponse } from '../lib/types';

const INV: InvestigationResponse = {
  session_id: 'ses-abc', request_id: 'r-1', phase: 'troubleshooting',
  issue_category: 'kubernetes', severity: 'critical', status: 'in_progress',
  missing_info: [], affected_services: ['api'], error_codes: [],
  agent_messages: [], diagnostic_plan: [], log_findings: [], config_findings: [],
  runbook_citations: [],
  probable_causes: [
    { rank: 1, cause: 'OOMKilled', confidence: 0.9, supporting_evidence: [],
      contradicting_evidence: [], confirmation_check: '', expected_result: '' },
    { rank: 2, cause: 'Resource limits too low', confidence: 0.6,
      supporting_evidence: [], contradicting_evidence: [], confirmation_check: '', expected_result: '' },
  ],
  diagnostic_steps: [], recommended_fixes: [], flagged_items: [],
  flagged_for_human_review: [], investigation_token: 'tok', llm_configured: false, iteration: 3,
};

describe('EscalationPanel', () => {
  test('renders escalation header', () => {
    render(
      <EscalationPanel
        investigation={INV}
        onRestartWithContext={jest.fn()}
        onTryNextCause={jest.fn()}
        onExportReport={jest.fn()}
      />
    );
    expect(screen.getByText(/Still Stuck/i)).toBeInTheDocument();
  });

  test('calls onExportReport when Download button clicked', () => {
    const onExport = jest.fn();
    render(
      <EscalationPanel
        investigation={INV}
        onRestartWithContext={jest.fn()}
        onTryNextCause={jest.fn()}
        onExportReport={onExport}
      />
    );
    fireEvent.click(screen.getByText(/Download Full Report/i));
    expect(onExport).toHaveBeenCalled();
  });

  test('calls onRestartWithContext when Restart clicked', () => {
    const onRestart = jest.fn();
    render(
      <EscalationPanel
        investigation={INV}
        onRestartWithContext={onRestart}
        onTryNextCause={jest.fn()}
        onExportReport={jest.fn()}
      />
    );
    fireEvent.click(screen.getByText(/Restart With Context/i));
    expect(onRestart).toHaveBeenCalled();
  });

  test('shows Try Next Root Cause when 2+ causes exist', () => {
    render(
      <EscalationPanel
        investigation={INV}
        onRestartWithContext={jest.fn()}
        onTryNextCause={jest.fn()}
        onExportReport={jest.fn()}
      />
    );
    expect(screen.getByText(/Try Next Root Cause/i)).toBeInTheDocument();
  });

  test('shows iteration count in subtitle', () => {
    render(
      <EscalationPanel
        investigation={INV}
        onRestartWithContext={jest.fn()}
        onTryNextCause={jest.fn()}
        onExportReport={jest.fn()}
      />
    );
    expect(screen.getByText(/3 iterations/i)).toBeInTheDocument();
  });
});

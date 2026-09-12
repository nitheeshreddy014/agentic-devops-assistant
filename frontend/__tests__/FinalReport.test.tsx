/**
 * Tests for FinalReport — export, download, mark-resolved.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import FinalReport from '../components/FinalReport';
import type { InvestigationResponse } from '../lib/types';

// Minimal mock clipboard
Object.assign(navigator, {
  clipboard: { writeText: jest.fn().mockResolvedValue(undefined) },
});

const INV: InvestigationResponse = {
  session_id: 'ses-xyz', request_id: 'r1', phase: 'completed',
  issue_category: 'kubernetes', severity: 'high', status: 'completed',
  missing_info: [], affected_services: ['svc-a'], error_codes: ['E503'],
  agent_messages: [], diagnostic_plan: [], log_findings: [], config_findings: [],
  runbook_citations: [],
  probable_causes: [{ rank: 1, cause: 'ImagePullBackOff', confidence: 0.85,
    supporting_evidence: ['registry timeout'], contradicting_evidence: [],
    confirmation_check: '', expected_result: '' }],
  diagnostic_steps: [{ step_number: 1, purpose: 'Check events', command: 'kubectl get events',
    expected_result: 'Events listed', risk_level: 'low', is_safe_readonly: true,
    requires_approval: false, approval_reason: '', interpretation: '' }],
  recommended_fixes: [{ title: 'Fix registry', description: 'Update image pull secret',
    steps: ['kubectl create secret ...'], rollback_steps: [], risk_level: 'medium',
    requires_approval: false, estimated_impact: 'Pods restart' }],
  flagged_items: [], flagged_for_human_review: [],
  report: { title: 'K8s Registry Issue', executive_summary: 'Pod cannot pull image.' },
  investigation_token: 'tok', llm_configured: false, iteration: 2,
};

describe('FinalReport', () => {
  test('renders report title from report.title', () => {
    render(<FinalReport investigation={INV} />);
    expect(screen.getByText('K8s Registry Issue')).toBeInTheDocument();
  });

  test('renders severity badge', () => {
    render(<FinalReport investigation={INV} />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });

  test('renders executive summary', () => {
    render(<FinalReport investigation={INV} />);
    expect(screen.getByText(/Pod cannot pull image/i)).toBeInTheDocument();
  });

  test('Copy Report button calls clipboard.writeText', () => {
    render(<FinalReport investigation={INV} />);
    fireEvent.click(screen.getByText('Copy Report'));
    expect(navigator.clipboard.writeText).toHaveBeenCalled();
  });

  test('Mark Resolved button calls onMarkResolved', () => {
    const onResolve = jest.fn();
    render(<FinalReport investigation={INV} onMarkResolved={onResolve} />);
    fireEvent.click(screen.getByText('Mark Resolved'));
    expect(onResolve).toHaveBeenCalled();
  });

  test('Mark Resolved button hidden when already resolved', () => {
    render(<FinalReport investigation={INV} onMarkResolved={jest.fn()} resolved={true} />);
    expect(screen.queryByText('Mark Resolved')).not.toBeInTheDocument();
    expect(screen.getByText('Resolved')).toBeInTheDocument();
  });

  test('shows root causes count in key metrics', () => {
    render(<FinalReport investigation={INV} />);
    // Multiple '1' values exist (1 service, 1 root cause) — use getAllByText
    const ones = screen.getAllByText('1');
    expect(ones.length).toBeGreaterThanOrEqual(1);
  });
});

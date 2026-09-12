/**
 * Tests for localStorage session persistence helpers.
 */
import {
  saveActiveSession, loadActiveSession, clearActiveSession,
  saveToHistory, loadHistory, clearHistory,
  saveFormDraft, loadFormDraft, clearFormDraft,
} from '../lib/storage';
import type { InvestigationResponse } from '../lib/types';

const MOCK_INV: InvestigationResponse = {
  session_id:               'sess-001',
  request_id:               'req-001',
  phase:                    'troubleshooting',
  issue_category:           'kubernetes',
  severity:                 'high',
  status:                   'in_progress',
  missing_info:             [],
  affected_services:        ['api'],
  error_codes:              ['E500'],
  agent_messages:           [],
  diagnostic_plan:          [],
  log_findings:             [],
  config_findings:          [],
  runbook_citations:        [],
  probable_causes:          [{ rank: 1, cause: 'OOM', confidence: 0.9,
                               supporting_evidence: [], contradicting_evidence: [],
                               confirmation_check: '', expected_result: '' }],
  diagnostic_steps:         [],
  recommended_fixes:        [],
  flagged_items:            [],
  flagged_for_human_review: [],
  investigation_token:      'tok-abc',
  llm_configured:           false,
  iteration:                1,
};

beforeEach(() => {
  localStorage.clear();
});

describe('Active session', () => {
  test('save then load returns same session_id', () => {
    saveActiveSession(MOCK_INV);
    expect(loadActiveSession()?.session_id).toBe('sess-001');
  });

  test('clear removes session', () => {
    saveActiveSession(MOCK_INV);
    clearActiveSession();
    expect(loadActiveSession()).toBeNull();
  });

  test('load returns null when nothing saved', () => {
    expect(loadActiveSession()).toBeNull();
  });
});

describe('History', () => {
  test('saveToHistory then loadHistory has entry', () => {
    saveToHistory(MOCK_INV);
    const h = loadHistory();
    expect(h.length).toBe(1);
    expect(h[0].id).toBe('sess-001');
  });

  test('duplicate session updates existing entry', () => {
    saveToHistory(MOCK_INV);
    saveToHistory(MOCK_INV);
    expect(loadHistory().length).toBe(1);
  });

  test('resolved flag persists', () => {
    saveToHistory(MOCK_INV, true);
    expect(loadHistory()[0].resolved).toBe(true);
  });

  test('clearHistory empties list', () => {
    saveToHistory(MOCK_INV);
    clearHistory();
    expect(loadHistory().length).toBe(0);
  });
});

describe('Form draft', () => {
  test('save and load draft', () => {
    saveFormDraft({ problem_title: 'Test incident' });
    expect(loadFormDraft()?.problem_title).toBe('Test incident');
  });

  test('clearFormDraft removes draft', () => {
    saveFormDraft({ problem_title: 'x' });
    clearFormDraft();
    expect(loadFormDraft()).toBeNull();
  });
});

/**
 * localStorage helpers — session persistence & investigation history.
 * All reads are wrapped in try/catch so SSR and private-mode never crash.
 */
import type { InvestigationResponse, StartInvestigationRequest } from './types';

const ACTIVE_KEY   = 'devops_active_investigation';
const HISTORY_KEY  = 'devops_investigation_history';
const FORM_KEY     = 'devops_form_draft';
const MAX_HISTORY  = 10;

// ── Types ────────────────────────────────────────────────────────────────────

export interface HistoryEntry {
  id:           string;
  title:        string;
  technology:   string;
  environment:  string;
  severity:     string;
  iteration:    number;
  resolved:     boolean;
  savedAt:      string;            // ISO string
  investigation: InvestigationResponse;
}

// ── Active session ────────────────────────────────────────────────────────────

export function saveActiveSession(inv: InvestigationResponse): void {
  try { localStorage.setItem(ACTIVE_KEY, JSON.stringify(inv)); } catch {}
}

export function loadActiveSession(): InvestigationResponse | null {
  try {
    const raw = localStorage.getItem(ACTIVE_KEY);
    return raw ? (JSON.parse(raw) as InvestigationResponse) : null;
  } catch { return null; }
}

export function clearActiveSession(): void {
  try { localStorage.removeItem(ACTIVE_KEY); } catch {}
}

// ── History ───────────────────────────────────────────────────────────────────

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch { return []; }
}

export function saveToHistory(inv: InvestigationResponse, resolved = false): void {
  try {
    const history = loadHistory();
    const entry: HistoryEntry = {
      id:           inv.session_id,
      title:        (inv.report as Record<string, string>)?.title ?? inv.issue_category,
      technology:   inv.issue_category,
      environment:  'production',
      severity:     inv.severity,
      iteration:    inv.iteration,
      resolved,
      savedAt:      new Date().toISOString(),
      investigation: inv,
    };
    // Replace existing entry or prepend
    const idx = history.findIndex(h => h.id === inv.session_id);
    if (idx >= 0) history[idx] = entry;
    else history.unshift(entry);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
  } catch {}
}

export function markHistoryResolved(sessionId: string): void {
  try {
    const history = loadHistory();
    const idx = history.findIndex(h => h.id === sessionId);
    if (idx >= 0) { history[idx].resolved = true; }
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  } catch {}
}

export function clearHistory(): void {
  try { localStorage.removeItem(HISTORY_KEY); } catch {}
}

// ── Form draft ────────────────────────────────────────────────────────────────

export function saveFormDraft(form: Partial<StartInvestigationRequest>): void {
  try { localStorage.setItem(FORM_KEY, JSON.stringify(form)); } catch {}
}

export function loadFormDraft(): Partial<StartInvestigationRequest> | null {
  try {
    const raw = localStorage.getItem(FORM_KEY);
    return raw ? (JSON.parse(raw) as Partial<StartInvestigationRequest>) : null;
  } catch { return null; }
}

export function clearFormDraft(): void {
  try { localStorage.removeItem(FORM_KEY); } catch {}
}

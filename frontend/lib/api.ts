import type { StartInvestigationRequest, InvestigationResponse, HealthResponse } from './types';

const BASE = '/api';

async function call<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const startInvestigation = (req: StartInvestigationRequest): Promise<InvestigationResponse> =>
  call('/investigations', { method: 'POST', body: JSON.stringify(req) });

export const continueInvestigation = (token: string, diagnosticOutput: string): Promise<InvestigationResponse> =>
  call('/investigations/continue', {
    method: 'POST',
    body: JSON.stringify({ investigation_token: token, diagnostic_output: diagnosticOutput }),
  });

export const checkHealth = (): Promise<HealthResponse> => call('/health');

export const searchRunbooks = (query: string, maxResults = 5) =>
  call('/rag/search', { method: 'POST', body: JSON.stringify({ query, max_results: maxResults }) });

export const analyzeLogs = (logs: string, technology?: string) =>
  call('/analyze/logs', { method: 'POST', body: JSON.stringify({ logs, technology }) });

export const analyzeConfig = (configuration: string, config_type: string) =>
  call('/analyze/config', { method: 'POST', body: JSON.stringify({ configuration, config_type }) });

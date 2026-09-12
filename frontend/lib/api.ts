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

export const checkHealth = async (): Promise<HealthResponse> => {
  const raw = await call<Record<string, unknown>>('/health');
  // Normalise backend field names → frontend HealthResponse shape
  return {
    ...raw,
    groq_configured: (raw.groq_configured ?? raw.llm_configured ?? false) as boolean,
    llm_configured:  (raw.llm_configured  ?? false) as boolean,
    model:           (raw.groq_model ?? raw.llm_model ?? raw.model ?? '') as string,
    llm_model:       (raw.llm_model  ?? '') as string,
    llm_provider:    (raw.llm_provider ?? '') as string,
    status:          (raw.status  ?? '') as string,
    version:         (raw.version ?? '') as string,
    request_id:      (raw.request_id ?? '') as string,
  } as HealthResponse;
};

export const searchRunbooks = (query: string, maxResults = 5) =>
  call('/rag/search', { method: 'POST', body: JSON.stringify({ query, max_results: maxResults }) });

export const analyzeLogs = (logs: string, technology?: string) =>
  call('/analyze/logs', { method: 'POST', body: JSON.stringify({ logs, technology }) });

export const analyzeConfig = (configuration: string, config_type: string) =>
  call('/analyze/config', { method: 'POST', body: JSON.stringify({ configuration, config_type }) });

// Re-run analysis with user-supplied answers for missing info
export const continueWithAnswers = (
  token: string,
  answers: Record<string, string>,
): Promise<InvestigationResponse> =>
  call('/investigations/continue', {
    method: 'POST',
    body: JSON.stringify({
      investigation_token: token,
      diagnostic_output: Object.entries(answers)
        .map(([q, a]) => `${q}: ${a}`)
        .join('\n'),
    }),
  });

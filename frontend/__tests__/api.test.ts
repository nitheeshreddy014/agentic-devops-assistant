/**
 * Frontend API client tests.
 * Uses jest.fn() mocks — never calls the real backend.
 */
global.fetch = jest.fn();

import { startInvestigation, continueInvestigation, checkHealth } from '@/lib/api';

const mockFetch = global.fetch as jest.Mock;

function mockOk(data: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => data,
  });
}

function mockErr(status: number, detail: string) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail }),
  });
}

beforeEach(() => mockFetch.mockClear());

describe('checkHealth', () => {
  it('returns llm_configured from /api/health', async () => {
    mockOk({ status: 'ok', llm_configured: false, llm_provider: 'groq', llm_model: 'llama-3.3-70b-versatile', version: '1.0.0', request_id: 'x' });
    const h = await checkHealth();
    expect(h.status).toBe('ok');
    expect(typeof h.llm_configured).toBe('boolean');
    expect(mockFetch).toHaveBeenCalledWith('/api/health', expect.anything());
  });
});

describe('startInvestigation', () => {
  it('POSTs to /api/investigations and returns response', async () => {
    const mockResp = { session_id: 'abc', issue_category: 'kubernetes', severity: 'high',
      probable_causes: [], diagnostic_steps: [], investigation_token: 'tok.sig', llm_configured: false };
    mockOk(mockResp);

    const resp = await startInvestigation({
      problem_title: 'Pod CrashLoopBackOff',
      problem_description: 'Pod keeps restarting',
      technology: 'kubernetes',
      environment: 'production',
    });

    expect(resp.session_id).toBe('abc');
    expect(resp.issue_category).toBe('kubernetes');
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/investigations');
    expect(opts.method).toBe('POST');
    const body = JSON.parse(opts.body);
    expect(body.problem_title).toBe('Pod CrashLoopBackOff');
  });

  it('throws on HTTP error', async () => {
    mockErr(422, 'Field too large');
    await expect(startInvestigation({
      problem_title: 'x', problem_description: 'y', technology: 'k', environment: 'p',
    })).rejects.toThrow('Field too large');
  });
});

describe('continueInvestigation', () => {
  it('sends token and diagnostic_output', async () => {
    mockOk({ session_id: 'abc', iteration: 2, investigation_token: 'new.tok' });
    await continueInvestigation('old.tok', 'Error: OOM');
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/investigations/continue');
    const body = JSON.parse(opts.body);
    expect(body.investigation_token).toBe('old.tok');
    expect(body.diagnostic_output).toBe('Error: OOM');
  });
});

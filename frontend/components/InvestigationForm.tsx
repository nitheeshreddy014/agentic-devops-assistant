'use client';
/**
 * InvestigationForm - enhanced:
 * Example incidents quick-fill (CrashLoopBackOff, Terraform, GitHub Actions)
 * Drag-and-drop file upload for logs and config
 * Real-time char counter with warning at 80%
 * Multi-tech hint (type comma for multiple)
 * Form draft auto-saved to localStorage
 * Keyboard shortcut: Cmd+Enter to submit
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import type { StartInvestigationRequest } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { saveFormDraft, loadFormDraft } from '@/lib/storage';

const TECHNOLOGIES = [
  { value: 'kubernetes',      label: 'Kubernetes' },
  { value: 'terraform',       label: 'Terraform' },
  { value: 'docker',          label: 'Docker' },
  { value: 'aws',             label: 'AWS' },
  { value: 'azure',           label: 'Azure' },
  { value: 'gcp',             label: 'Google Cloud' },
  { value: 'jenkins',         label: 'Jenkins' },
  { value: 'github_actions',  label: 'GitHub Actions' },
  { value: 'gitlab_ci',       label: 'GitLab CI' },
  { value: 'linux',           label: 'Linux / System' },
  { value: 'database',        label: 'Database' },
  { value: 'networking',      label: 'Networking / DNS' },
  { value: 'api',             label: 'API / HTTP' },
  { value: 'ssl_tls',         label: 'SSL / TLS' },
  { value: 'iam',             label: 'IAM / Permissions' },
  { value: 'other',           label: 'Other' },
];
const ENVS = [
  { value: 'production',  label: 'Production' },
  { value: 'staging',     label: 'Staging' },
  { value: 'development', label: 'Development' },
  { value: 'testing',     label: 'Testing' },
  { value: 'unknown',     label: 'Unknown' },
];

const EXAMPLES = [
  {
    label: 'K8s CrashLoopBackOff',
    form: {
      problem_title:       'Kubernetes pod stuck in CrashLoopBackOff',
      problem_description: 'Our payment-service pods in the prod namespace are stuck in CrashLoopBackOff after the latest deployment. The pods restart every ~30 seconds and never become Ready. Traffic is being dropped and customers are affected.',
      technology:          'kubernetes',
      environment:         'production',
      recent_changes:      'Deployed v2.4.1 of payment-service 45 minutes ago. Only changed DB connection pool size from 10 to 50.',
      logs:                'Error: dial tcp: connect: connection refused\nat net.(*Dialer).DialContext\nFATAL: Max connections reached\nkubernetes/pkg/kubelet: Back-off restarting failed container',
      configuration:       '',
    },
  },
  {
    label: 'Terraform AccessDenied',
    form: {
      problem_title:       'Terraform plan fails with AccessDenied on S3',
      problem_description: 'Running terraform plan in our CI pipeline fails with AccessDeniedException when trying to access the remote state bucket. This worked yesterday. No IAM changes were made intentionally.',
      technology:          'terraform',
      environment:         'staging',
      recent_changes:      'Rotated AWS credentials in GitHub secrets 2 hours ago.',
      logs:                'Error: Failed to get existing workspaces: S3 bucket does not exist.\nAccessDeniedException: User arn:aws:iam::123456789:user/ci-user is not authorized to perform: s3:ListBucket',
      configuration:       'terraform {\n  backend "s3" {\n    bucket = "my-tf-state"\n    key    = "prod/terraform.tfstate"\n    region = "us-east-1"\n  }\n}',
    },
  },
  {
    label: 'GitHub Actions timeout',
    form: {
      problem_title:       'GitHub Actions workflow times out at Docker build step',
      problem_description: 'Our main CI workflow is consistently timing out at the Docker build step after exactly 6 hours. The image used to build in ~12 minutes. Started happening after we added a new ML model dependency.',
      technology:          'github_actions',
      environment:         'staging',
      recent_changes:      'Added torch==2.1.0 and transformers==4.35.0 to requirements.txt in last PR.',
      logs:                'Error: The operation was canceled.\nError: buildx call failed with: exit status 1\n##[error]Process completed with exit code 1.\nExceeded maximum allowed time.',
      configuration:       'jobs:\n  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: 360\n    steps:\n      - uses: docker/build-push-action@v5',
    },
  },
];

const inputCls  = 'w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm';
const labelCls  = 'block text-sm font-medium text-gray-300 mb-1';
const DESC_MAX  = 5000;

interface Props {
  onSubmit:   (req: StartInvestigationRequest) => Promise<void>;
  isLoading:  boolean;
  prefill?:   Partial<StartInvestigationRequest>;
}

const EMPTY: StartInvestigationRequest = {
  problem_title: '', problem_description: '', technology: 'kubernetes',
  environment: 'production', recent_changes: '', logs: '', configuration: '',
} as StartInvestigationRequest;

export default function InvestigationForm({ onSubmit, isLoading, prefill }: Props) {
  const [form,      setForm]      = useState<StartInvestigationRequest>({ ...EMPTY, ...prefill });
  const [logDrag,   setLogDrag]   = useState(false);
  const [confDrag,  setConfDrag]  = useState(false);
  const [showExamples, setShowExamples] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const logRef  = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const confRef = useRef<any>(null);

  // Load draft on mount
  useEffect(() => {
    if (prefill && Object.keys(prefill).length > 0) return;
    const draft = loadFormDraft();
    if (draft) setForm(f => ({ ...f, ...draft }));
  }, [prefill]);

  // Prefill from parent (restart-with-context)
  useEffect(() => {
    if (prefill && Object.keys(prefill).length > 0) setForm(f => ({ ...f, ...prefill }));
  }, [prefill]);

  // Auto-save draft
  useEffect(() => {
    saveFormDraft(form);
  }, [form]);

  const set = (k: keyof StartInvestigationRequest) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }));

  const readFile = async (file: File, key: 'logs' | 'configuration') => {
    const limit = key === 'logs' ? 50_000 : 30_000;
    const text  = await file.text();
    setForm(f => ({ ...f, [key]: text.slice(0, limit) }));
  };

  const handleDrop = (e: React.DragEvent, key: 'logs' | 'configuration') => {
    e.preventDefault();
    if (key === 'logs') setLogDrag(false); else setConfDrag(false);
    const file = e.dataTransfer.files?.[0];
    if (file) readFile(file, key);
  };

  const applyExample = (ex: typeof EXAMPLES[0]) => {
    setForm(f => ({ ...f, ...ex.form }));
    setShowExamples(false);
  };

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!form.problem_title.trim() || !form.problem_description.trim() || isLoading) return;
    await onSubmit(form);
  }, [form, isLoading, onSubmit]);

  // Cmd/Ctrl+Enter shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleSubmit();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSubmit]);

  const descPct   = form.problem_description.length / DESC_MAX;
  const descWarn  = descPct > 0.8;

  const DropZone = ({
    value, onChange, fileKey, isDrag, setIsDrag, inputRef, accept, placeholder, rows,
  }: {
    value: string; onChange: (v: string) => void; fileKey: 'logs' | 'configuration';
    isDrag: boolean; setIsDrag: (v: boolean) => void; inputRef: React.RefObject<any>;
    accept: string; placeholder: string; rows: number;
  }) => (
    <div
      onDragOver={e => { e.preventDefault(); setIsDrag(true); }}
      onDragLeave={() => setIsDrag(false)}
      onDrop={e => handleDrop(e, fileKey)}
      className={`relative rounded-lg border transition-colors
        ${isDrag ? 'border-blue-500 bg-blue-900/20' : 'border-gray-600'}`}
    >
      {isDrag && (
        <div className="absolute inset-0 flex items-center justify-center bg-blue-900/40 rounded-lg z-10">
          <p className="text-blue-300 font-medium text-sm">Drop file here</p>
        </div>
      )}
      <textarea value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} rows={rows}
        className={`${inputCls} border-0 resize-y font-mono text-xs`} />
      <div className="flex items-center gap-3 px-3 py-1.5 border-t border-gray-700">
        <button type="button" onClick={() => inputRef.current?.click()}
          className="text-xs text-blue-400 hover:text-blue-300 underline">
          Upload file
        </button>
        <span className="text-xs text-gray-600">or drag &amp; drop</span>
        {value && <span className="text-xs text-gray-500 ml-auto">{value.length.toLocaleString()} chars</span>}
        <input ref={inputRef} type="file" accept={accept} className="hidden"
          onChange={e => e.target.files?.[0] && readFile(e.target.files[0], fileKey)} />
      </div>
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-5 bg-gray-900 rounded-xl p-6 border border-gray-700" noValidate>
      {/* Header + examples */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-xl font-semibold text-white">Start Investigation</h2>
        <div className="relative">
          <button type="button" onClick={() => setShowExamples(o => !o)}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-600 text-gray-400
              hover:border-blue-500 hover:text-blue-300 transition-colors">
            Try an example
          </button>
          {showExamples && (
            <div className="absolute right-0 top-full mt-1 w-56 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-20 overflow-hidden">
              {EXAMPLES.map(ex => (
                <button key={ex.label} type="button" onClick={() => applyExample(ex)}
                  className="w-full text-left px-4 py-2.5 text-xs text-gray-300 hover:bg-gray-700 hover:text-white transition-colors">
                  {ex.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Title */}
      <div>
        <label className={labelCls}>Problem Title <span className="text-red-400">*</span></label>
        <input type="text" value={form.problem_title} onChange={set('problem_title')}
          placeholder="e.g. Kubernetes pod CrashLoopBackOff in production"
          maxLength={200} required className={inputCls}
          aria-required="true" />
      </div>

      {/* Description */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className={`${labelCls} mb-0`}>Description <span className="text-red-400">*</span></label>
          <span className={`text-xs ${descWarn ? 'text-orange-400' : 'text-gray-500'}`}>
            {form.problem_description.length}/{DESC_MAX}
            {descWarn && ' — approaching limit'}
          </span>
        </div>
        <textarea value={form.problem_description} onChange={set('problem_description')}
          placeholder="Describe the issue: what failed, when, what you observe, business impact..."
          rows={4} maxLength={DESC_MAX} required
          className={`${inputCls} resize-y`} aria-required="true" />
      </div>

      {/* Technology + Environment */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Technology</label>
          <select value={form.technology} onChange={set('technology')} className={inputCls}>
            {TECHNOLOGIES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls}>Environment</label>
          <select value={form.environment} onChange={set('environment')} className={inputCls}>
            {ENVS.map(e => <option key={e.value} value={e.value}>{e.label}</option>)}
          </select>
        </div>
      </div>

      {/* Recent changes */}
      <div>
        <label className={labelCls}>Recent Changes <span className="text-gray-500 font-normal">(optional)</span></label>
        <textarea value={form.recent_changes} onChange={set('recent_changes')}
          placeholder="Any deployments, config changes, or infra updates in last 24h..."
          rows={2} maxLength={2000} className={`${inputCls} resize-y`} />
      </div>

      {/* Logs */}
      <div>
        <label className={labelCls}>Error Logs <span className="text-gray-500 font-normal">(optional — paste or drag & drop)</span></label>
        <DropZone
          value={form.logs ?? ''} onChange={v => setForm(f => ({ ...f, logs: v }))}
          fileKey="logs" isDrag={logDrag} setIsDrag={setLogDrag} inputRef={logRef}
          accept=".log,.txt,.json" rows={5}
          placeholder="Paste error logs, kubectl logs, CloudWatch output..."
        />
      </div>

      {/* Config */}
      <div>
        <label className={labelCls}>
          Configuration <span className="text-gray-500 font-normal">(Terraform / K8s YAML / Dockerfile — optional)</span>
        </label>
        <DropZone
          value={form.configuration ?? ''} onChange={v => setForm(f => ({ ...f, configuration: v }))}
          fileKey="configuration" isDrag={confDrag} setIsDrag={setConfDrag} inputRef={confRef}
          accept=".yaml,.yml,.tf,.json,.toml,.ini,.conf" rows={5}
          placeholder="Paste relevant configuration here..."
        />
      </div>

      <Button type="submit" isLoading={isLoading} size="lg"
        disabled={!form.problem_title.trim() || !form.problem_description.trim() || isLoading}
        className="w-full" aria-label="Start investigation (Cmd+Enter)">
        Start Investigation
        <span className="ml-2 text-xs opacity-60">Cmd+Enter</span>
      </Button>
    </form>
  );
}

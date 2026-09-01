'use client';
import { useState, useRef } from 'react';
import type { StartInvestigationRequest } from '@/lib/types';
import { Button } from '@/components/ui/Button';

const TECHNOLOGIES = [
  { value: 'kubernetes', label: 'Kubernetes' }, { value: 'terraform', label: 'Terraform' },
  { value: 'docker', label: 'Docker' }, { value: 'aws', label: 'AWS' },
  { value: 'azure', label: 'Azure' }, { value: 'gcp', label: 'Google Cloud' },
  { value: 'jenkins', label: 'Jenkins' }, { value: 'github_actions', label: 'GitHub Actions' },
  { value: 'gitlab_ci', label: 'GitLab CI' }, { value: 'linux', label: 'Linux / System' },
  { value: 'database', label: 'Database' }, { value: 'networking', label: 'Networking / DNS' },
  { value: 'api', label: 'API / HTTP' }, { value: 'ssl_tls', label: 'SSL / TLS' },
  { value: 'iam', label: 'IAM / Permissions' }, { value: 'other', label: 'Other' },
];
const ENVS = [
  { value: 'production', label: 'Production' }, { value: 'staging', label: 'Staging' },
  { value: 'development', label: 'Development' }, { value: 'testing', label: 'Testing' },
  { value: 'unknown', label: 'Unknown' },
];

interface Props { onSubmit: (req: StartInvestigationRequest) => Promise<void>; isLoading: boolean }

const inputCls = 'w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm';
const labelCls = 'block text-sm font-medium text-gray-300 mb-1';

export default function InvestigationForm({ onSubmit, isLoading }: Props) {
  const [form, setForm] = useState<StartInvestigationRequest>({
    problem_title: '', problem_description: '', technology: 'kubernetes',
    environment: 'production', recent_changes: '', logs: '', configuration: '',
  });
  const logRef   = useRef<HTMLInputElement>(null);
  const confRef  = useRef<HTMLInputElement>(null);

  const set = (k: keyof StartInvestigationRequest) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }));

  const readFile = async (file: File, key: 'logs' | 'configuration') => {
    const limit = key === 'logs' ? 50_000 : 30_000;
    const text  = await file.text();
    setForm(f => ({ ...f, [key]: text.slice(0, limit) }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.problem_title.trim() || !form.problem_description.trim()) return;
    await onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 bg-gray-900 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-semibold text-white">Start Investigation</h2>

      {/* Title */}
      <div>
        <label className={labelCls}>Problem Title <span className="text-red-400">*</span></label>
        <input type="text" value={form.problem_title} onChange={set('problem_title')}
          placeholder="e.g. Kubernetes pod CrashLoopBackOff in production" maxLength={200} required className={inputCls} />
      </div>

      {/* Description */}
      <div>
        <label className={labelCls}>Description <span className="text-red-400">*</span></label>
        <textarea value={form.problem_description} onChange={set('problem_description')}
          placeholder="Describe the issue in detail: what failed, when, and what you observe…" rows={4}
          maxLength={5000} required className={`${inputCls} resize-y`} />
        <p className="text-xs text-gray-500 mt-1">{form.problem_description.length}/5000</p>
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
          placeholder="Any recent deployments, config changes, or infrastructure updates…" rows={2}
          maxLength={2000} className={`${inputCls} resize-y`} />
      </div>

      {/* Logs */}
      <div>
        <label className={labelCls}>Error Logs <span className="text-gray-500 font-normal">(optional)</span></label>
        <textarea value={form.logs} onChange={set('logs')}
          placeholder="Paste error logs, kubectl logs, or CloudWatch output here…" rows={5}
          className={`${inputCls} resize-y font-mono text-xs`} />
        <div className="flex items-center gap-3 mt-1">
          <button type="button" onClick={() => logRef.current?.click()}
            className="text-xs text-blue-400 hover:text-blue-300 underline">Upload log file</button>
          <input ref={logRef} type="file" accept=".log,.txt,.json" className="hidden"
            onChange={e => e.target.files?.[0] && readFile(e.target.files[0], 'logs')} />
          {form.logs && <span className="text-xs text-gray-500">{form.logs.length} chars</span>}
        </div>
      </div>

      {/* Config */}
      <div>
        <label className={labelCls}>Configuration <span className="text-gray-500 font-normal">(Terraform / K8s YAML / Dockerfile / CI config — optional)</span></label>
        <textarea value={form.configuration} onChange={set('configuration')}
          placeholder="Paste relevant configuration here…" rows={5}
          className={`${inputCls} resize-y font-mono text-xs`} />
        <div className="flex items-center gap-3 mt-1">
          <button type="button" onClick={() => confRef.current?.click()}
            className="text-xs text-blue-400 hover:text-blue-300 underline">Upload config file</button>
          <input ref={confRef} type="file" accept=".yaml,.yml,.tf,.json,.toml,.ini,.conf" className="hidden"
            onChange={e => e.target.files?.[0] && readFile(e.target.files[0], 'configuration')} />
        </div>
      </div>

      <Button type="submit" isLoading={isLoading} size="lg"
        disabled={!form.problem_title.trim() || !form.problem_description.trim() || isLoading}
        className="w-full">
        🔍 Start Investigation
      </Button>
    </form>
  );
}

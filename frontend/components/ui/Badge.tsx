import { ReactNode } from 'react';

const colours: Record<string, string> = {
  critical: 'bg-red-900/60 text-red-300 border-red-700',
  high:     'bg-orange-900/60 text-orange-300 border-orange-700',
  medium:   'bg-yellow-900/60 text-yellow-300 border-yellow-700',
  low:      'bg-green-900/60 text-green-300 border-green-700',
  info:     'bg-blue-900/60 text-blue-300 border-blue-700',
  purple:   'bg-purple-900/60 text-purple-300 border-purple-700',
  gray:     'bg-gray-800 text-gray-400 border-gray-600',
};

interface BadgeProps {
  variant?: string;
  children: ReactNode;
  className?: string;
}

export function Badge({ variant = 'info', children, className = '' }: BadgeProps) {
  const cls = colours[variant] ?? colours.gray;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cls} ${className}`}>
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const icons: Record<string, string> = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢', unknown: '⚪' };
  return <Badge variant={severity}>{icons[severity] ?? '⚪'} {severity.toUpperCase()}</Badge>;
}

export function RiskBadge({ risk, requiresApproval }: { risk: string; requiresApproval?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1">
      <Badge variant={risk}>{risk}</Badge>
      {requiresApproval && (
        <Badge variant="purple">⚠ approval required</Badge>
      )}
    </span>
  );
}

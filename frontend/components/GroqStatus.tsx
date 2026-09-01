'use client';
interface Props { configured: boolean }
export default function GroqStatus({ configured }: Props) {
  return (
    <div className={`inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full text-xs border ${
      configured ? 'bg-green-900/30 text-green-400 border-green-700/50'
                 : 'bg-yellow-900/30 text-yellow-400 border-yellow-700/50'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${configured ? 'bg-green-400' : 'bg-yellow-400 animate-pulse'}`}/>
      {configured ? '✓ Groq AI ready' : '⚠ GROQ_API_KEY not set — add it to .env (see .env.example) for AI analysis'}
    </div>
  );
}

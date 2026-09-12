'use client';
import { useState } from 'react';
interface Props { configured: boolean; model?: string; }
export default function GroqStatus({ configured, model }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => !configured && setOpen(true)}
        title={configured ? `Model: ${model ?? 'groq'}` : 'Click for setup guide'}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors
          ${configured
            ? 'bg-green-900/30 border-green-700/50 text-green-400'
            : 'bg-red-900/30 border-red-700/50 text-red-400 cursor-pointer hover:bg-red-900/50 animate-pulse'}`}
        aria-label={configured ? 'Groq connected' : 'Groq not configured — click for setup'}>
        <span className={`w-1.5 h-1.5 rounded-full ${configured ? 'bg-green-400' : 'bg-red-400'}`} />
        {configured ? `Groq ✓${model ? ` · ${model}` : ''}` : 'Groq not configured — click to fix'}
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-white">🔑 Set Up Groq API Key</h2>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white text-xl leading-none">&times;</button>
            </div>
            <ol className="space-y-3 text-sm text-gray-300 list-none">
              {[
                <>Go to <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">console.groq.com/keys</a> and create a free API key.</>,
                <>Create <code className="bg-gray-800 px-1 rounded text-green-300">api/.env</code></>,
                'Add the line below:',
              ].map((step, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-blue-400 font-bold shrink-0">{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
            <pre className="bg-gray-950 border border-gray-700 rounded-lg p-3 text-xs text-green-300 font-mono select-all">GROQ_API_KEY=gsk_your_key_here</pre>
            <ol start={4} className="space-y-3 text-sm text-gray-300 list-none">
              {[
                <>Restart: <code className="bg-gray-800 px-1 rounded text-green-300">cd api && uvicorn index:app --reload</code></>,
                'Refresh this page — indicator turns green ✓',
              ].map((step, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-blue-400 font-bold shrink-0">{i + 4}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
            <button onClick={() => setOpen(false)}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
}

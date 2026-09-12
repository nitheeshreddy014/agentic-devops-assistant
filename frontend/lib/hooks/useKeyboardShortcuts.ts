/**
 * Global keyboard shortcuts hook.
 * Cmd/Ctrl+Enter → submit form
 * Escape         → clear / close modal
 * Cmd/Ctrl+K     → focus search / history
 */
import { useEffect } from 'react';

interface Shortcuts {
  onSubmit?:  () => void;
  onEscape?:  () => void;
  onHistory?: () => void;
}

export function useKeyboardShortcuts({ onSubmit, onEscape, onHistory }: Shortcuts) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (meta && e.key === 'Enter')  { e.preventDefault(); onSubmit?.(); }
      if (e.key === 'Escape')          { e.preventDefault(); onEscape?.(); }
      if (meta && e.key === 'k')      { e.preventDefault(); onHistory?.(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onSubmit, onEscape, onHistory]);
}

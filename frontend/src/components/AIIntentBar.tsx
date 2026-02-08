'use client';

import { useState } from 'react';
import { Sparkles, Send } from 'lucide-react';

interface AIIntentBarProps {
  placeholder: string;
  suggestions?: string[];
  disabled?: boolean;
  submitLabel?: string;
  loadingLabel?: string;
  onSubmit: (text: string) => Promise<void> | void;
}

export default function AIIntentBar({
  placeholder,
  suggestions = [],
  disabled = false,
  submitLabel = 'Apply',
  loadingLabel = 'Applying...',
  onSubmit,
}: AIIntentBarProps) {
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const value = text.trim();
    if (!value || disabled || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(value);
      setText('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="glass-card p-4 space-y-3">
      <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-rb-text-secondary">
        <Sparkles className="w-3.5 h-3.5 text-rb-cyan" />
        AI Intent Input
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder={placeholder}
          className="flex-1 w-full input-base input-md"
          disabled={disabled || submitting}
        />
        <button
          onClick={() => { void submit(); }}
          disabled={disabled || submitting || !text.trim()}
          className="btn-primary btn-md inline-flex items-center justify-center gap-2 disabled:opacity-50 w-full sm:w-auto shrink-0"
        >
          <Send className="w-4 h-4" />
          {submitting ? loadingLabel : submitLabel}
        </button>
      </div>

      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => setText(s)}
              disabled={disabled || submitting}
              className="px-2.5 py-1 text-[11px] font-mono rounded border border-layer-4/60 bg-layer-3/20 text-rb-cyan hover:bg-layer-3/40 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

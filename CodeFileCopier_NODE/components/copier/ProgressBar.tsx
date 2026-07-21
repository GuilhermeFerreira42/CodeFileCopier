'use client';

import { useCopier } from '@/lib/copier/store';

export function ProgressBar() {
  const { state } = useCopier();
  const { value, max, label } = state.progress;

  if (value === null) return null;

  const isPulse = value === 'pulse';
  const pct = isPulse ? 0 : Math.round(((value as number) / max) * 100);

  return (
    <div className="flex-shrink-0">
      <div className="flex justify-between text-[10px] text-text2 mb-1">
        <span>{label || 'Processando…'}</span>
        {!isPulse && <span>{pct}%</span>}
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r from-primary to-success rounded-full transition-all duration-200 ${isPulse ? 'animate-pulse w-1/2' : ''}`}
          style={!isPulse ? { width: `${pct}%` } : {}}
        />
      </div>
    </div>
  );
}

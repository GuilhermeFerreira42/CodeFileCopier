'use client';

import { useCopier } from '@/lib/copier/store';

export function LoadingOverlay() {
  const { state } = useCopier();

  if (!state.isLoading) return null;

  return (
    <div className="absolute inset-0 bg-white/85 dark:bg-slate-900/85 flex flex-col items-center justify-center gap-3 rounded-lg z-10">
      <div className="w-8 h-8 border-[3px] border-border border-t-primary rounded-full animate-spin" />
      <p className="text-xs text-text2">{state.loadingText}</p>
    </div>
  );
}

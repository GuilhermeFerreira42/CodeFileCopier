'use client';

import { useCopier } from '@/lib/copier/store';

const borderMap: Record<string, string> = {
  ok: 'border-l-success',
  warn: 'border-l-warn',
  err: 'border-l-danger',
};

export function ToastContainer() {
  const { state } = useCopier();

  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-1.5 z-[2000]" aria-live="polite">
      {state.toasts.map((t) => (
        <div
          key={t.id}
          className={`bg-slate-800 text-white px-3.5 py-2 rounded-lg text-xs shadow-lg border-l-4 max-w-[280px] animate-in slide-in-from-right-full duration-200 ${borderMap[t.type] ?? ''}`}
        >
          {t.msg}
        </div>
      ))}
    </div>
  );
}

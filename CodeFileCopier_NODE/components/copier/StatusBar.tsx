'use client';

import { useCopier } from '@/lib/copier/store';

export function StatusBar() {
  const { state } = useCopier();
  const selected = state.selectedFiles.size;
  const total = state.allMeta.length;

  return (
    <div className="flex justify-between items-center text-[10px] text-text2 flex-shrink-0 px-0.5">
      <span>{state.isLoading ? state.loadingText : total > 0 ? `✓ ${total} arquivo(s) prontos` : 'Pronto'}</span>
      <span>{selected} sel. | {total} total | v2.1</span>
    </div>
  );
}

'use client';

import { useCopier } from '@/lib/copier/store';
import { estimateTokens } from '@/lib/copier/utils';

export function CounterBar() {
  const { state } = useCopier();
  let totalChars = 0;
  state.selectedFiles.forEach((rp) => {
    const m = state.allMeta.find((x) => x.relPath === rp);
    if (m) totalChars += m.size;
  });
  const tokens = estimateTokens(totalChars);

  return (
    <div className="flex items-center justify-between bg-success-light border border-success/40 rounded-md px-3 py-1.5 flex-shrink-0">
      <span className="text-xs font-bold text-success-dark font-mono">
        {state.selectedFiles.size} arquivo(s) selecionado(s) | ~{totalChars.toLocaleString('pt-BR')} chars
      </span>
      <span className="text-[10px] text-success-dark/70">
        ~{tokens.toLocaleString('pt-BR')} tokens est.
      </span>
    </div>
  );
}

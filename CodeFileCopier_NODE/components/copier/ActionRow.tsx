'use client';

import { useCopier } from '@/lib/copier/store';
import { useOutput } from '@/lib/copier/useOutput';

export function ActionRow() {
  const { state, dispatch, log, toast } = useCopier();
  const { startCopy, clipboardCopy } = useOutput();

  function clearAll() {
    dispatch({ type: 'CLEAR_ALL' });
    log('✓ Tudo limpo.', 'ok');
    toast('Limpo!', 'ok');
  }

  return (
    <div className="flex gap-1.5 flex-shrink-0">
      <button
        id="btn-start"
        onClick={startCopy}
        disabled={state.isLoading}
        className="flex-[2] py-2.5 bg-success-light border-2 border-success rounded-lg cursor-pointer text-sm font-bold text-success-dark hover:bg-success/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
      >
        INICIAR COPIA
      </button>
      <button
        onClick={clearAll}
        className="flex-1 py-2.5 bg-warn-light border border-warn rounded-lg cursor-pointer text-xs text-warn-dark hover:bg-warn/20 transition-all"
      >
        Limpar
      </button>
      <button
        onClick={clipboardCopy}
        className="flex-1 py-2.5 bg-primary-light border border-primary rounded-lg cursor-pointer text-xs text-primary hover:bg-primary/20 transition-all"
      >
        Clipboard
      </button>
    </div>
  );
}

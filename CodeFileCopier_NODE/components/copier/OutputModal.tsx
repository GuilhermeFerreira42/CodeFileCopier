'use client';

import { useCopier } from '@/lib/copier/store';
import { useOutput } from '@/lib/copier/useOutput';
import { estimateTokens } from '@/lib/copier/utils';
import { useEffect } from 'react';

export function OutputModal() {
  const { state, dispatch } = useCopier();
  const { downloadOutput, copyModalContent } = useOutput();

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && state.modalOpen) {
        dispatch({ type: 'CLOSE_MODAL' });
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [state.modalOpen, dispatch]);

  if (!state.modalOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/60 z-[999] flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) dispatch({ type: 'CLOSE_MODAL' }); }}
      role="dialog"
      aria-modal="true"
      aria-label="Resultado da copia"
    >
      <div className="bg-white dark:bg-surface w-full max-w-3xl max-h-[90vh] flex flex-col rounded-xl shadow-2xl">
        {/* Head */}
        <div className="flex items-center justify-between px-4 py-3 bg-primary text-white rounded-t-xl flex-shrink-0">
          <h2 className="text-sm font-semibold">{state.modalFilename}</h2>
          <div className="flex items-center gap-2">
            <span className="text-[10px] opacity-80">
              {state.modalCount} arq. | {state.modalChars.toLocaleString('pt-BR')} chars | ~{estimateTokens(state.modalChars).toLocaleString('pt-BR')} tokens
            </span>
            <button
              className="bg-none border-none text-white text-xl cursor-pointer leading-none hover:opacity-70 transition-opacity"
              onClick={() => dispatch({ type: 'CLOSE_MODAL' })}
              aria-label="Fechar"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-3">
          <pre className="font-mono text-[10px] whitespace-pre-wrap break-words leading-relaxed text-text">
            {state.modalContent}
          </pre>
        </div>

        {/* Foot */}
        <div className="px-4 py-2.5 flex gap-2 justify-end border-t border-border flex-shrink-0 flex-wrap">
          <button
            className="px-4 py-1.5 bg-primary text-white rounded-md text-xs cursor-pointer hover:bg-primary-dark transition-colors"
            onClick={copyModalContent}
          >
            Copiar tudo
          </button>
          <button
            className="px-4 py-1.5 bg-success text-white rounded-md text-xs cursor-pointer hover:opacity-80 transition-opacity"
            onClick={downloadOutput}
          >
            Baixar .txt
          </button>
          <button
            className="px-4 py-1.5 bg-surface2 border border-border text-text rounded-md text-xs cursor-pointer hover:bg-border transition-colors"
            onClick={() => dispatch({ type: 'CLOSE_MODAL' })}
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

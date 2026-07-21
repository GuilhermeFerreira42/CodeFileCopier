'use client';

import { ALL_IGNORE_PATTERNS, PATTERN_GROUPS } from '@/lib/copier/constants';
import { useCopier } from '@/lib/copier/store';
import { useEffect } from 'react';

export function IgnorePatternsModal() {
  const { state, dispatch } = useCopier();
  const active = new Set(state.ignorePatterns);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && state.ignoreModalOpen) {
        dispatch({ type: 'CLOSE_IGNORE_MODAL' });
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [state.ignoreModalOpen, dispatch]);

  if (!state.ignoreModalOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/60 z-[999] flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) dispatch({ type: 'CLOSE_IGNORE_MODAL' });
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Gerenciar padroes globais"
    >
      <div className="bg-white dark:bg-surface w-full max-w-lg max-h-[90vh] flex flex-col rounded-xl shadow-2xl">
        {/* Head */}
        <div className="flex items-center justify-between px-4 py-3 bg-primary text-white rounded-t-xl flex-shrink-0">
          <div className="flex flex-col">
            <h2 className="text-sm font-semibold">Padroes globais a ignorar</h2>
            <span className="text-[10px] opacity-80">
              Itens marcados nao serao incluidos na copia
            </span>
          </div>
          <button
            className="bg-none border-none text-white text-xl cursor-pointer leading-none hover:opacity-70 transition-opacity"
            onClick={() => dispatch({ type: 'CLOSE_IGNORE_MODAL' })}
            aria-label="Fechar"
          >
            &#10005;
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border flex-shrink-0">
          <button
            className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
            onClick={() => dispatch({ type: 'SET_IGNORE_PATTERNS', payload: [...ALL_IGNORE_PATTERNS] })}
          >
            Marcar tudo
          </button>
          <button
            className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
            onClick={() => dispatch({ type: 'SET_IGNORE_PATTERNS', payload: [] })}
          >
            Desmarcar tudo
          </button>
          <span className="text-[10px] text-text2 ml-auto">
            {state.ignorePatterns.length}/{ALL_IGNORE_PATTERNS.length} ativos
          </span>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-4 flex flex-col gap-4 copier-scroll">
          {PATTERN_GROUPS.map((group) => {
            const groupPatterns = group.patterns.map((p) => p.pattern);
            const allOn = groupPatterns.every((p) => active.has(p));
            const someOn = groupPatterns.some((p) => active.has(p));
            return (
              <div key={group.id} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-text2 uppercase tracking-wide">
                    {group.label}
                  </h3>
                  <button
                    className="text-[10px] text-primary hover:underline cursor-pointer"
                    onClick={() => {
                      const set = new Set(active);
                      if (allOn) groupPatterns.forEach((p) => set.delete(p));
                      else groupPatterns.forEach((p) => set.add(p));
                      dispatch({
                        type: 'SET_IGNORE_PATTERNS',
                        payload: ALL_IGNORE_PATTERNS.filter((p) => set.has(p)),
                      });
                    }}
                  >
                    {allOn ? 'desmarcar grupo' : someOn ? 'marcar grupo' : 'marcar grupo'}
                  </button>
                </div>
                <div className="flex flex-col rounded-md border border-border overflow-hidden">
                  {group.patterns.map((p) => {
                    const on = active.has(p.pattern);
                    return (
                      <label
                        key={p.pattern}
                        className={`flex items-center gap-2.5 px-3 py-2 cursor-pointer border-b border-border last:border-b-0 transition-colors select-none ${
                          on ? 'bg-green-50 dark:bg-green-900/20' : 'bg-surface2 hover:bg-primary-light'
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="cursor-pointer accent-primary flex-shrink-0"
                          checked={on}
                          onChange={(e) =>
                            dispatch({
                              type: 'TOGGLE_IGNORE_PATTERN',
                              pattern: p.pattern,
                              active: e.target.checked,
                            })
                          }
                        />
                        <code className="text-xs font-mono font-semibold text-text flex-shrink-0 min-w-[110px]">
                          {p.pattern}
                        </code>
                        <span className="text-[11px] text-text2 leading-snug">{p.desc}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Foot */}
        <div className="px-4 py-2.5 flex gap-2 justify-end border-t border-border flex-shrink-0">
          <button
            className="px-4 py-1.5 bg-primary text-white rounded-md text-xs cursor-pointer hover:bg-primary-dark transition-colors"
            onClick={() => dispatch({ type: 'CLOSE_IGNORE_MODAL' })}
          >
            Concluir
          </button>
        </div>
      </div>
    </div>
  );
}

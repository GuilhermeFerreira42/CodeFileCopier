'use client';

import { useCopier } from '@/lib/copier/store';
import { useState } from 'react';

export function ExtTab() {
  const { state, dispatch } = useCopier();
  const [query, setQuery] = useState('');

  const filtered = state.allExts.filter((e) => e.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="flex flex-col gap-2 flex-1 overflow-hidden min-h-0">
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <label className="text-xs font-semibold text-text2 min-w-[50px]" htmlFor="ext-search">Filtrar:</label>
        <input
          id="ext-search"
          className="flex-1 px-2 py-1 border border-border rounded-md text-xs bg-surface2 text-text focus:outline-none focus:ring-1 focus:ring-primary min-w-0"
          placeholder="Filtrar extensoes…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto border border-border rounded-md bg-surface2 min-h-0">
        {!filtered.length ? (
          <div className="p-5 text-center text-text2 text-xs">
            {state.allMeta.length === 0 ? 'Selecione uma pasta de entrada.' : 'Nenhuma extensao encontrada.'}
          </div>
        ) : (
          filtered.map((ext) => {
            const count = state.allMeta.filter((m) => m.ext === ext).length;
            const allBinary = state.allMeta.filter((m) => m.ext === ext).every((m) => m.isBinary);
            const sel = state.selectedExts.has(ext);
            return (
              <label
                key={ext}
                className={`flex items-center gap-2 px-2.5 py-1.5 cursor-pointer border-b border-border last:border-b-0 transition-colors select-none
                  ${sel ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-primary-light'}`}
              >
                <input
                  type="checkbox"
                  className="cursor-pointer accent-primary flex-shrink-0"
                  checked={sel}
                  onChange={(e) => dispatch({ type: 'SELECT_EXT', ext, selected: e.target.checked })}
                />
                <span className={`text-xs break-all leading-snug ${allBinary ? 'text-danger font-semibold' : 'text-text'}`}>
                  {ext}
                  {allBinary && <span className="ml-1 text-[9px] font-normal opacity-70">(binario)</span>}
                </span>
                <span className="text-[10px] text-text2 ml-auto whitespace-nowrap">{count} arq.</span>
              </label>
            );
          })
        )}
      </div>

      <div className="flex gap-1.5 flex-wrap flex-shrink-0">
        <button
          className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
          onClick={() => dispatch({ type: 'SEL_ALL_EXT' })}
        >
          Tudo
        </button>
        <button
          className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
          onClick={() => dispatch({ type: 'DESEL_ALL_EXT' })}
        >
          Nenhum
        </button>
        <span className="text-[10px] text-text2 ml-auto self-center">{state.selectedExts.size} sel.</span>
      </div>
    </div>
  );
}

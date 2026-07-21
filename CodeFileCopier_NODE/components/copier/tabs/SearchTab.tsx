'use client';

import { useCopier } from '@/lib/copier/store';
import { useSearch } from '@/lib/copier/useSearch';
import { useState } from 'react';

export function SearchTab() {
  const { state, dispatch } = useCopier();
  const { doSearch } = useSearch();
  const [query, setQuery] = useState('');

  function handleSearch() {
    doSearch(query);
  }

  return (
    <div className="flex flex-col gap-2 flex-1 overflow-hidden min-h-0">
      <small className="text-text2 flex-shrink-0 text-[11px]">
        Cole nomes, caminhos ou saida de <code className="font-mono">git status</code>:
      </small>
      <textarea
        className="w-full h-16 px-2 py-1.5 border border-border rounded-md font-mono text-xs resize-y bg-surface2 text-text focus:outline-none focus:ring-1 focus:ring-primary flex-shrink-0"
        placeholder={"modified: src/main.py\nnew file: config.json\nutils, README"}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.nativeEvent.isComposing && e.ctrlKey) handleSearch();
        }}
      />
      <div className="flex gap-1.5 flex-wrap flex-shrink-0">
        <button
          className="px-2.5 py-1 bg-primary text-white border border-primary rounded-md cursor-pointer text-xs hover:bg-primary-dark transition-colors"
          onClick={handleSearch}
        >
          Buscar
        </button>
        <button
          className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
          onClick={() => dispatch({ type: 'SELECT_SEARCH_ALL' })}
        >
          Tudo
        </button>
        <button
          className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
          onClick={() => dispatch({ type: 'DESEL_SEARCH_ALL' })}
        >
          Nenhum
        </button>
      </div>

      <div className="flex-1 overflow-y-auto border border-border rounded-md bg-surface2 min-h-0">
        {!state.searchResults.length ? (
          <div className="p-5 text-center text-text2 text-xs">Use o campo acima para buscar.</div>
        ) : (
          state.searchResults.map((rp) => {
            const sel = state.selectedFiles.has(rp);
            const m = state.allMeta.find((x) => x.relPath === rp);
            const isBin = m?.isBinary ?? false;
            return (
              <label
                key={rp}
                className={`flex items-center gap-2 px-2.5 py-1.5 cursor-pointer border-b border-border last:border-b-0 transition-colors select-none
                  ${sel ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-primary-light'}`}
              >
                <input
                  type="checkbox"
                  className="cursor-pointer accent-primary flex-shrink-0"
                  checked={sel}
                  onChange={(e) => dispatch({ type: 'SELECT_FILE', relPath: rp, selected: e.target.checked })}
                />
                <span className={`text-xs break-all ${isBin ? 'text-danger font-semibold' : 'text-text'}`}>
                  {rp}
                  {isBin && <span className="ml-1 text-[9px] font-normal opacity-70">(binario)</span>}
                </span>
              </label>
            );
          })
        )}
      </div>
    </div>
  );
}

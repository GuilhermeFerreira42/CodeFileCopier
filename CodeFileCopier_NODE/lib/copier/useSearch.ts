'use client';

import { useCallback } from 'react';
import { useCopier } from './store';

export function useSearch() {
  const { state, dispatch, log, toast } = useCopier();

  const doSearch = useCallback(
    (raw: string) => {
      if (!raw.trim()) {
        dispatch({ type: 'SET_SEARCH_RESULTS', payload: state.allMeta.map((m) => m.relPath) });
        return;
      }
      const terms = raw
        .split(/[\s,\n]+/)
        .filter(Boolean)
        .map((t) => {
          t = t.replace(/^(modified:|new file:|deleted:|renamed:)\s*/i, '').trim();
          if (t.includes('->')) t = t.split('->').pop()!.trim();
          return t;
        })
        .filter(Boolean);

      const found = new Set<string>();
      state.allMeta.forEach((m) => {
        const rp = m.relPath.replace(/\\/g, '/');
        const noExt = m.name.replace(/\.[^.]+$/, '');
        for (const term of terms) {
          const tl = term.toLowerCase().replace(/\\/g, '/');
          const hasSlash = tl.includes('/');
          if (hasSlash) {
            if (rp.toLowerCase().endsWith(tl)) { found.add(m.relPath); break; }
          } else {
            if (m.name.toLowerCase() === tl || noExt.toLowerCase() === tl) { found.add(m.relPath); break; }
          }
        }
      });

      dispatch({ type: 'SET_SEARCH_RESULTS', payload: [...found] });
      if (!found.size) toast('Nenhum arquivo encontrado.', 'warn');
      else log(`✓ ${found.size} arquivo(s) encontrado(s).`, 'ok');
    },
    [state.allMeta, dispatch, log, toast]
  );

  return { doSearch };
}

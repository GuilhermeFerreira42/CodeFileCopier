'use client';

import { useCopier } from '@/lib/copier/store';
import { TabId } from '@/lib/copier/types';

const TABS: { id: TabId; label: string }[] = [
  { id: 'ext', label: 'Extensoes' },
  { id: 'files', label: 'Arquivos' },
  { id: 'search', label: 'Buscar Nome' },
  { id: 'explorer', label: 'Explorador' },
  { id: 'arb', label: 'Avulsos' },
  { id: 'gi', label: 'Gitignore' },
];

export function TabNav() {
  const { state, dispatch } = useCopier();

  return (
    <nav className="flex gap-0.5 flex-shrink-0 overflow-x-auto scrollbar-none" aria-label="Abas">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: tab.id })}
          className={`px-3 h-9 border border-b-0 rounded-t-md cursor-pointer text-xs whitespace-nowrap flex-shrink-0 transition-all
            ${
              state.activeTab === tab.id
                ? 'bg-primary text-white font-semibold border-primary'
                : 'bg-surface border-border text-text2 hover:bg-primary-light hover:text-primary'
            }`}
          aria-selected={state.activeTab === tab.id}
          role="tab"
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

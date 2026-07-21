'use client';

import { useCopier } from '@/lib/copier/store';
import { ArbTab } from './tabs/ArbTab';
import { ExtTab } from './tabs/ExtTab';
import { ExplorerTab } from './tabs/ExplorerTab';
import { FilesTab } from './tabs/FilesTab';
import { GitignoreTab } from './tabs/GitignoreTab';
import { SearchTab } from './tabs/SearchTab';
import { LoadingOverlay } from './LoadingOverlay';

export function TabArea() {
  const { state } = useCopier();

  return (
    <div className="flex-1 bg-surface border border-border rounded-b-lg rounded-tr-lg flex flex-col overflow-hidden min-h-0 relative">
      <LoadingOverlay />
      <div className="flex-1 flex flex-col gap-2 p-2.5 overflow-hidden min-h-0">
        {state.activeTab === 'ext' && <ExtTab />}
        {state.activeTab === 'files' && <FilesTab />}
        {state.activeTab === 'search' && <SearchTab />}
        {state.activeTab === 'explorer' && <ExplorerTab />}
        {state.activeTab === 'arb' && <ArbTab />}
        {state.activeTab === 'gi' && <GitignoreTab />}
      </div>
    </div>
  );
}

'use client';

import { ActionRow } from '@/components/copier/ActionRow';
import { ConfigSection } from '@/components/copier/ConfigSection';
import { CounterBar } from '@/components/copier/CounterBar';
import { Header } from '@/components/copier/Header';
import { IgnorePatternsModal } from '@/components/copier/IgnorePatternsModal';
import { LogSection } from '@/components/copier/LogSection';
import { OutputModal } from '@/components/copier/OutputModal';
import { ProgressBar } from '@/components/copier/ProgressBar';
import { StatusBar } from '@/components/copier/StatusBar';
import { TabArea } from '@/components/copier/TabArea';
import { TabNav } from '@/components/copier/TabNav';
import { ToastContainer } from '@/components/copier/ToastContainer';
import { CopierProvider } from '@/lib/copier/store';
import { useEffect } from 'react';

function KeyboardHandler() {
  // Global Escape handler
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        const extSearch = document.getElementById('ext-search') as HTMLInputElement | null;
        const fileSearch = document.getElementById('file-search') as HTMLInputElement | null;
        if (extSearch) extSearch.value = '';
        if (fileSearch) fileSearch.value = '';
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, []);
  return null;
}

export default function CopierPage() {
  return (
    <CopierProvider>
      <KeyboardHandler />
      <main
        className="flex flex-col h-screen max-w-[1200px] mx-auto p-2 gap-1.5 overflow-hidden"
        style={{ background: 'var(--copier-bg)' }}
      >
        <Header />
        <ConfigSection />
        <TabNav />
        <TabArea />
        <CounterBar />
        <ProgressBar />
        <ActionRow />
        <LogSection />
        <StatusBar />
      </main>

      <OutputModal />
      <IgnorePatternsModal />
      <ToastContainer />
    </CopierProvider>
  );
}

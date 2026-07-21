'use client';

import { useCopier } from '@/lib/copier/store';
import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export function Header() {
  const { state } = useCopier();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('theme');
      if (saved === 'dark') {
        document.documentElement.classList.add('dark');
        setDark(true);
      }
    } catch { /* ignore */ }
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    try { localStorage.setItem('theme', next ? 'dark' : 'light'); } catch { /* ignore */ }
  }

  const totalFiles = state.allMeta.length;

  return (
    <header className="flex items-center justify-between bg-primary text-white px-3.5 h-12 rounded-lg flex-shrink-0">
      <h1 className="text-sm font-bold tracking-tight">Copiador de Código v2.1</h1>
      <div className="flex items-center gap-2.5 text-xs opacity-85">
        <button
          onClick={toggleTheme}
          className="bg-white/20 border-none text-white px-2 py-1 rounded-md cursor-pointer text-xs leading-none hover:bg-white/30 transition-colors"
          aria-label="Alternar tema"
        >
          {dark ? <Sun size={13} /> : <Moon size={13} />}
        </button>
        <span className="bg-white/20 px-2 py-0.5 rounded-xl font-semibold whitespace-nowrap">
          {totalFiles} arq.
        </span>
        <span id="header-status" className="hidden sm:inline">
          {state.isLoading ? state.loadingText : 'Pronto'}
        </span>
      </div>
    </header>
  );
}

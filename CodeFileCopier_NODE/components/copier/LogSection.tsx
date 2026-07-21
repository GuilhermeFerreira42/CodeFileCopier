'use client';

import { useCopier } from '@/lib/copier/store';
import { useEffect, useRef, useState } from 'react';

export function LogSection() {
  const { state, dispatch } = useCopier();
  const bodyRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (bodyRef.current && !state.logCollapsed) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [state.logEntries, state.logCollapsed]);

  const logColorMap: Record<string, string> = {
    ok: 'text-green-400',
    warn: 'text-yellow-400',
    err: 'text-red-400',
    info: 'text-blue-400',
    '': 'text-slate-400',
  };

  return (
    <div className="flex-shrink-0 bg-surface border border-border rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between px-2.5 py-1.5 cursor-pointer select-none rounded-lg"
        onClick={() => dispatch({ type: 'TOGGLE_LOG_COLLAPSED' })}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-text2">Log</span>
          <span className="text-[10px] bg-primary text-white px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
            {state.logCount > 99 ? '99+' : state.logCount}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="text-[10px] text-text2 bg-none border-none cursor-pointer px-1.5 py-0.5 hover:text-danger transition-colors"
            onClick={(e) => { e.stopPropagation(); dispatch({ type: 'CLEAR_LOG' }); }}
          >
            limpar
          </button>
          <button
            className="text-[10px] border border-border rounded px-1.5 py-0.5 bg-surface2 text-text hover:bg-border transition-colors"
            onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v); }}
          >
            {expanded ? 'reduzir' : 'expandir'}
          </button>
          <span className="text-[10px] text-text2">
            {state.logCollapsed ? 'expandir' : 'recolher'}
          </span>
        </div>
      </div>

      {!state.logCollapsed && (
        <div
          ref={bodyRef}
          className={`overflow-y-auto px-2.5 py-1.5 bg-slate-900 transition-all ${expanded ? 'h-44' : 'h-[70px]'}`}
        >
          {state.logEntries.map((entry) => (
            <div
              key={entry.id}
              className={`font-mono text-[10px] leading-relaxed ${logColorMap[entry.type] ?? 'text-slate-400'}`}
            >
              [{entry.time}] {entry.msg}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

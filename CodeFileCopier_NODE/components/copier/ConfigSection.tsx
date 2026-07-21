'use client';

import { ALL_IGNORE_PATTERNS } from '@/lib/copier/constants';
import { useCopier } from '@/lib/copier/store';
import { ChevronDown, ChevronRight, FolderArchive, SlidersHorizontal } from 'lucide-react';
import { useRef } from 'react';

export function ConfigSection() {
  const { state, dispatch, loadFiles, loadZip } = useCopier();
  const srcPickerRef = useRef<HTMLInputElement>(null);
  const zipPickerRef = useRef<HTMLInputElement>(null);

  async function handlePicker(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    await loadFiles(files);
    e.target.value = '';
  }

  async function handleZipPicker(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await loadZip(file);
    e.target.value = '';
  }

  const activeCount = state.ignorePatterns.length;
  const totalCount = ALL_IGNORE_PATTERNS.length;

  return (
    <div className="bg-surface border border-border rounded-lg flex-shrink-0">
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer select-none"
        onClick={() => dispatch({ type: 'TOGGLE_CONFIG_COLLAPSED' })}
      >
        <span className="font-semibold text-xs text-text2">Configuracoes</span>
        <span className="text-xs text-text2 flex items-center gap-1">
          {state.configCollapsed ? (
            <><ChevronRight size={12} /> expandir</>
          ) : (
            <><ChevronDown size={12} /> recolher</>
          )}
        </span>
      </div>

      {!state.configCollapsed && (
        <div className="px-3 pb-3 flex flex-col gap-1.5">
          {/* Entrada */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-text2 min-w-[52px]">Entrada:</span>
            <input
              className="flex-1 px-2 py-1 border border-border rounded-md text-xs bg-surface2 text-text focus:outline-none focus:ring-1 focus:ring-primary min-w-0"
              id="src-input"
              type="text"
              placeholder="Selecione a pasta ou um .zip…"
              readOnly
              value={state.srcDir}
            />
            <button
              className="px-2.5 py-1 bg-primary text-white border-none rounded-md cursor-pointer text-xs whitespace-nowrap hover:bg-primary-dark transition-colors"
              onClick={() => srcPickerRef.current?.click()}
            >
              Procurar…
            </button>
            <button
              className="px-2.5 py-1 bg-surface2 border border-border text-text rounded-md cursor-pointer text-xs whitespace-nowrap hover:bg-border transition-colors flex items-center gap-1"
              onClick={() => zipPickerRef.current?.click()}
              title="Carregar um arquivo .zip como se fosse uma pasta"
            >
              <FolderArchive size={13} /> ZIP
            </button>
            <input
              ref={srcPickerRef}
              type="file"
              // @ts-expect-error webkitdirectory is non-standard
              webkitdirectory=""
              multiple
              className="hidden"
              onChange={handlePicker}
            />
            <input
              ref={zipPickerRef}
              type="file"
              accept=".zip,application/zip,application/x-zip-compressed"
              className="hidden"
              onChange={handleZipPicker}
            />
          </div>

          {/* Saída */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-text2 min-w-[52px]">Saida:</span>
            <input
              className="flex-1 px-2 py-1 border border-border rounded-md text-xs bg-surface2 text-text focus:outline-none focus:ring-1 focus:ring-primary min-w-0"
              type="text"
              placeholder="codigo_completo.txt"
              value={state.outName}
              onChange={(e) => dispatch({ type: 'SET_OUT_NAME', payload: e.target.value })}
            />
          </div>

          {/* Opções */}
          <div className="flex items-center gap-3 flex-wrap">
            <label className="text-xs text-text2 font-semibold">Ordem:</label>
            <select
              className="px-2 py-1 border border-border rounded-md text-xs bg-surface text-text"
              value={state.sortMode}
              onChange={(e) => dispatch({ type: 'SET_SORT_MODE', payload: e.target.value as 'natural' | 'alpha' })}
            >
              <option value="natural">Natural</option>
              <option value="alpha">Alfabetica</option>
            </select>

            <button
              className="flex items-center gap-1.5 px-2 py-1 border border-border rounded-md text-xs text-text bg-surface2 hover:bg-border transition-colors cursor-pointer"
              onClick={() => dispatch({ type: 'OPEN_IGNORE_MODAL' })}
              title="Escolher quais itens globais nao serao copiados"
            >
              <SlidersHorizontal size={13} />
              Padroes globais
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
                  activeCount > 0 ? 'bg-primary text-white' : 'bg-border text-text2'
                }`}
              >
                {activeCount}/{totalCount}
              </span>
            </button>

            <label className="flex items-center gap-1.5 cursor-pointer text-xs text-text">
              <input
                type="checkbox"
                className="cursor-pointer accent-primary"
                checked={state.sizeFilterEnabled}
                onChange={(e) =>
                  dispatch({ type: 'SET_SIZE_FILTER', enabled: e.target.checked, maxKb: state.maxSizeKb })
                }
              />
              Ignorar &gt;
              <input
                type="number"
                className="w-14 px-1 py-0.5 border border-border rounded text-xs bg-surface2 text-text"
                value={state.maxSizeKb}
                min={1}
                onChange={(e) =>
                  dispatch({ type: 'SET_SIZE_FILTER', enabled: state.sizeFilterEnabled, maxKb: Number(e.target.value) || 500 })
                }
              />
              KB
            </label>
          </div>
        </div>
      )}
    </div>
  );
}

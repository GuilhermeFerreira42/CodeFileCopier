'use client';

import { useCopier } from '@/lib/copier/store';
import { ArbFile } from '@/lib/copier/types';
import { readFileSingle } from '@/lib/copier/utils';
import { useRef, useState } from 'react';

export function ArbTab() {
  const { state, dispatch, log, toast } = useCopier();
  const pickerRef = useRef<HTMLInputElement>(null);
  const [checked, setChecked] = useState<Set<number>>(new Set());

  async function readArbFiles(files: File[]) {
    let n = 0;
    for (const f of files) {
      if (state.arbFiles.some((a) => a.name === f.name && a.size === f.size)) continue;
      const content = await readFileSingle(f);
      dispatch({
        type: 'SET_ARB_FILES',
        payload: [...state.arbFiles, { name: f.name, content, size: f.size }],
      });
      n++;
    }
    log(`${n} arquivo(s) avulso(s) adicionado(s).`, 'ok');
    // Rebuild checked with all indexes
    setChecked(new Set(Array.from({ length: state.arbFiles.length + n }, (_, i) => i)));
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    readArbFiles(Array.from(e.dataTransfer.files));
  }

  function handlePicker(e: React.ChangeEvent<HTMLInputElement>) {
    readArbFiles(Array.from(e.target.files ?? []));
    e.target.value = '';
  }

  function toggleCheck(i: number) {
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function remChecked() {
    const idxs = Array.from(checked).sort((a, b) => b - a);
    const updated = [...state.arbFiles];
    idxs.forEach((i) => updated.splice(i, 1));
    dispatch({ type: 'SET_ARB_FILES', payload: updated });
    setChecked(new Set());
    log(`${idxs.length} removido(s).`, 'ok');
  }

  function clearAll() {
    dispatch({ type: 'SET_ARB_FILES', payload: [] });
    setChecked(new Set());
    log('Lista avulsa limpa.', 'ok');
  }

  // Expose checked to useOutput via data attributes - store selected arb files in a hidden container
  // The useOutput hook reads arbFiles directly from state; we filter by checked here on "start copy"
  // We need to communicate which are checked. We'll use a different approach:
  // Store a global ref of checked arb indexes via a custom event or we store in state.
  // Simplest: dispatch SET_ARB_FILES with only checked when starting copy isn't ideal.
  // Instead, let's expose the selected arb files via state by always storing the selection.

  return (
    <div className="flex flex-col gap-2 flex-1 overflow-hidden min-h-0">
      <small className="text-text2 flex-shrink-0 text-[11px]">
        Adicione arquivos avulsos de qualquer local (arraste e solte):
      </small>

      <div
        className={`flex-1 overflow-y-auto border-2 border-dashed border-border rounded-md bg-surface2 min-h-[60px] transition-colors`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        id="arb-drop"
        data-checked-arb={JSON.stringify(Array.from(checked))}
      >
        {!state.arbFiles.length ? (
          <div className="flex items-center justify-center h-16 text-text2 text-xs">
            Arraste arquivos aqui ou use o botao abaixo
          </div>
        ) : (
          state.arbFiles.map((f, i) => (
            <label
              key={`${f.name}-${i}`}
              className="flex items-center gap-2 px-2.5 py-1.5 border-b border-border cursor-pointer select-none hover:bg-primary-light transition-colors"
            >
              <input
                type="checkbox"
                className="accent-primary"
                data-i={i}
                checked={checked.has(i)}
                onChange={() => toggleCheck(i)}
              />
              <span className="text-xs break-all font-mono text-text flex-1">{f.name}</span>
              <span className="text-[10px] text-text2 whitespace-nowrap">{(f.size / 1024).toFixed(1)}KB</span>
            </label>
          ))
        )}
      </div>

      <div className="flex gap-1.5 flex-wrap flex-shrink-0">
        <button
          className="px-2.5 py-1 bg-primary text-white border border-primary rounded-md cursor-pointer text-xs hover:bg-primary-dark transition-colors"
          onClick={() => pickerRef.current?.click()}
        >
          Adicionar…
        </button>
        <button
          className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
          onClick={remChecked}
        >
          Remover
        </button>
        <button
          className="px-2.5 py-1 bg-danger text-white border border-danger rounded-md cursor-pointer text-xs hover:opacity-80 transition-opacity"
          onClick={clearAll}
        >
          Limpar
        </button>
        <input ref={pickerRef} type="file" multiple className="hidden" onChange={handlePicker} />
      </div>
    </div>
  );
}

'use client';

import { useCallback } from 'react';
import { useCopier } from './store';
import { ArbFile } from './types';
import { buildArbOutput, buildFileOutput, giMatches, readFilesBatch, shouldIgnoreGlobal } from './utils';

export function useOutput() {
  const { state, dispatch, log, toast } = useCopier();

  const startCopy = useCallback(async () => {
    const { activeTab, allMeta, selectedExts, selectedFiles, applyGI, ignorePatterns, giFileRules, giManualRules, srcDir, outName, arbFiles } = state;

    const effectiveOutName = outName.trim() || 'codigo_completo.txt';

    if (activeTab === 'arb') {
      // Arbitrary files tab
      const arbDrop = document.getElementById('arb-drop');
      const checked = arbDrop
        ? (Array.from(arbDrop.querySelectorAll('input:checked')) as HTMLInputElement[])
            .map((c) => arbFiles[Number(c.dataset.i)])
            .filter(Boolean)
        : arbFiles;

      if (!checked.length) {
        toast('Nenhum avulso selecionado.', 'warn');
        return;
      }
      const { out, n } = buildArbOutput(checked as ArbFile[]);
      dispatch({ type: 'SET_LAST_OUTPUT', payload: out });
      toast(`✓ ${n} avulso(s) prontos!`, 'ok');
      dispatch({ type: 'SHOW_MODAL', content: out, filename: effectiveOutName, count: n, chars: out.length });
      return;
    }

    // Seleção do usuário (ainda sem filtrar binários), para detectá-los e avisar.
    const inSelection = (m: (typeof allMeta)[number]): boolean => {
      if (giMatches(m.relPath, applyGI, giFileRules, giManualRules)) return false;
      if (activeTab === 'gi') return !shouldIgnoreGlobal(m.name, ignorePatterns);
      if (activeTab === 'ext') return selectedExts.has(m.ext);
      return selectedFiles.has(m.relPath);
    };

    const selected = allMeta.filter(inSelection);
    const binariesInSelection = selected.filter((m) => m.isBinary);
    let metas = selected.filter((m) => !m.isBinary);

    if (activeTab === 'ext' && !selectedExts.size) {
      toast('Selecione ao menos uma extensão.', 'warn');
      return;
    }

    // Aviso: arquivos binários selecionados não podem ir para o texto e serão ignorados.
    if (binariesInSelection.length) {
      const names = binariesInSelection.map((m) => m.relPath);
      const preview = names.slice(0, 8).join(', ');
      const extra = names.length > 8 ? ` (+${names.length - 8})` : '';
      log(`⚠ ${binariesInSelection.length} arquivo(s) binário(s) ignorado(s): ${names.join(', ')}`, 'warn');
      toast(`${binariesInSelection.length} binário(s) ignorado(s): ${preview}${extra}`, 'warn', 5000);
    }

    if (!metas.length) {
      toast('Nenhum arquivo (de texto) para copiar.', 'warn');
      return;
    }

    const totalSize = metas.reduce((s, m) => s + m.size, 0);
    if (totalSize > 10 * 1024 * 1024) {
      if (!confirm(`⚠ Estimativa: ${(totalSize / 1024 / 1024).toFixed(1)} MB. Continuar?`)) return;
    }

    log(`Gerando output: ${metas.length} arquivo(s)…`, 'info');
    dispatch({ type: 'SET_LOADING', isLoading: true, text: 'Gerando output…' });
    dispatch({ type: 'SET_PROGRESS', value: 0, max: metas.length, label: 'Lendo arquivos…' });

    const contentMap = await readFilesBatch(metas, (done, total) => {
      dispatch({ type: 'SET_PROGRESS', value: done, max: total, label: `Lendo ${done}/${total}…` });
    });

    dispatch({ type: 'SET_PROGRESS', value: 'pulse', label: 'Gerando texto…' });

    const { out, copied, skipped } = buildFileOutput(metas, contentMap, srcDir, applyGI);

    dispatch({ type: 'SET_LAST_OUTPUT', payload: out });
    dispatch({ type: 'SET_LOADING', isLoading: false });
    dispatch({ type: 'SET_PROGRESS', value: null });

    log(`✓ ${copied} arquivo(s) gerado(s). ${skipped} ignorado(s).`, 'ok');
    toast(`✓ ${copied} arquivo(s) prontos!`, 'ok');
    dispatch({ type: 'SHOW_MODAL', content: out, filename: effectiveOutName, count: copied, chars: out.length });
  }, [state, dispatch, log, toast]);

  const clipboardCopy = useCallback(() => {
    const txt = state.lastOutput;
    if (!txt) { toast('Execute a cópia primeiro.', 'warn'); return; }
    copyText(txt, toast);
  }, [state.lastOutput, toast]);

  const downloadOutput = useCallback(() => {
    const c = state.modalContent;
    const fn = state.modalFilename || 'codigo_completo.txt';
    const blob = new Blob([c], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = fn;
    a.click();
    URL.revokeObjectURL(a.href);
    toast('Download iniciado!', 'ok');
    log(`Download: ${fn}`, 'ok');
  }, [state.modalContent, state.modalFilename, toast, log]);

  const copyModalContent = useCallback(() => {
    copyText(state.modalContent, toast);
  }, [state.modalContent, toast]);

  return { startCopy, clipboardCopy, downloadOutput, copyModalContent };
}

function copyText(txt: string, toast: (msg: string, type?: 'ok' | 'warn' | 'err') => void) {
  if (navigator.clipboard) {
    navigator.clipboard
      .writeText(txt)
      .then(() => toast(`✓ Copiado (${txt.length.toLocaleString()} chars)`, 'ok'))
      .catch(() => fallbackCopy(txt, toast));
  } else {
    fallbackCopy(txt, toast);
  }
}

function fallbackCopy(txt: string, toast: (msg: string, type?: 'ok' | 'warn' | 'err') => void) {
  const ta = document.createElement('textarea');
  ta.value = txt;
  ta.style.cssText = 'position:fixed;opacity:0';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  toast('✓ Copiado!', 'ok');
}

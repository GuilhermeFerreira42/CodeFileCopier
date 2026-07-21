'use client';

import { useCopier } from '@/lib/copier/store';
import { giMatches } from '@/lib/copier/utils';
import { useState } from 'react';

export function GitignoreTab() {
  const { state, dispatch, log, toast } = useCopier();
  const [ruleInput, setRuleInput] = useState('');

  function addRule() {
    const v = ruleInput.trim();
    if (!v || state.giManualRules.includes(v)) {
      toast('Regra ja existe ou vazia.', 'warn');
      return;
    }
    dispatch({ type: 'SET_GI_MANUAL_RULES', payload: [...state.giManualRules, v] });
    setRuleInput('');
    log(`Regra adicionada: ${v}`, 'ok');
  }

  function remRule() {
    const fl = state.giFileRules.length;
    if (state.giSelIdx < fl) {
      toast('Apenas regras manuais podem ser removidas.', 'warn');
      return;
    }
    const r = state.giManualRules[state.giSelIdx - fl];
    const updated = [...state.giManualRules];
    updated.splice(state.giSelIdx - fl, 1);
    dispatch({ type: 'SET_GI_MANUAL_RULES', payload: updated });
    dispatch({ type: 'SET_GI_SEL_IDX', payload: -1 });
    log(`Regra removida: ${r}`, 'ok');
  }

  const allRules = [
    ...state.giFileRules,
    ...state.giManualRules.map((r) => `[manual] ${r}`),
  ];

  const hasGitignore = state.giFileRules.length > 0;

  const preview = state.allMeta.slice(0, 400).map((m) => ({
    relPath: m.relPath,
    isBinary: m.isBinary,
    ignored: giMatches(m.relPath, state.applyGI, state.giFileRules, state.giManualRules),
  }));

  return (
    <div className="flex flex-col gap-2 flex-1 overflow-hidden min-h-0">
      <div className="flex items-center gap-2.5 flex-shrink-0 flex-wrap">
        <label className="flex items-center gap-1.5 cursor-pointer text-xs text-text">
          <input
            type="checkbox"
            className="cursor-pointer accent-primary"
            id="gi-cb"
            checked={state.applyGI}
            disabled={!hasGitignore}
            onChange={(e) => {
              dispatch({ type: 'SET_APPLY_GI', payload: e.target.checked });
              log(`Gitignore ${e.target.checked ? 'ativado' : 'desativado'}.`, 'info');
            }}
          />
          Aplicar regras .gitignore
        </label>
        <span className="text-xs text-text2">
          {hasGitignore
            ? `✓ .gitignore: ${state.giFileRules.length} linha(s).`
            : state.allMeta.length
            ? '⚠ Nenhum .gitignore encontrado.'
            : '⚠ Nenhum diretorio selecionado.'}
        </span>
      </div>

      <div className="flex gap-2 flex-1 min-h-0 overflow-hidden">
        {/* Regras */}
        <div className="flex flex-col gap-1.5 flex-1 min-w-0 overflow-hidden">
          <small className="font-semibold text-text2 text-[10px]">Regras:</small>
          <div className="flex-1 overflow-y-auto border border-border rounded-md bg-surface2 min-h-0">
            {allRules.map((r, i) => (
              <div
                key={i}
                className={`px-2 py-0.5 text-xs font-mono border-b border-border cursor-pointer transition-colors
                  ${r.startsWith('[manual]') ? 'text-purple-600 dark:text-purple-400' : ''}
                  ${state.giSelIdx === i ? 'bg-primary text-white' : 'hover:bg-primary-light'}`}
                onClick={() => dispatch({ type: 'SET_GI_SEL_IDX', payload: i })}
              >
                {r}
              </div>
            ))}
          </div>
          <div className="flex gap-1 flex-shrink-0">
            <input
              type="text"
              className="flex-1 px-2 py-1 border border-border rounded-md text-xs font-mono bg-surface2 text-text focus:outline-none focus:ring-1 focus:ring-primary min-w-0"
              placeholder="Ex: *.log, temp/"
              value={ruleInput}
              onChange={(e) => setRuleInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.nativeEvent.isComposing) addRule();
              }}
            />
            <button
              className="px-2.5 py-1 bg-primary text-white border border-primary rounded-md cursor-pointer text-xs hover:bg-primary-dark transition-colors"
              onClick={addRule}
            >
              +
            </button>
            <button
              className="px-2.5 py-1 border border-border bg-surface2 rounded-md cursor-pointer text-xs text-text hover:bg-border transition-colors"
              onClick={remRule}
            >
              −
            </button>
          </div>
        </div>

        {/* Preview */}
        <div className="flex flex-col gap-1.5 flex-1 min-w-0 overflow-hidden">
          <small className="font-semibold text-text2 text-[10px]">Preview:</small>
          <div className="flex-1 overflow-y-auto border border-border rounded-md bg-surface2 min-h-0">
            {!preview.length ? (
              <div className="p-4 text-center text-text2 text-xs">Carregue arquivos primeiro.</div>
            ) : (
              preview.map((item, i) => (
                <div
                  key={i}
                  className={`px-2 py-0.5 text-[10px] font-mono border-b border-border
                    ${item.isBinary ? 'text-danger font-semibold' : item.ignored ? 'text-danger bg-red-50 dark:bg-red-900/10' : 'text-success'}`}
                >
                  {item.ignored ? '✗' : '✓'} {item.relPath}
                  {item.isBinary && <span className="ml-1 text-[9px] font-normal opacity-70">(binario)</span>}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

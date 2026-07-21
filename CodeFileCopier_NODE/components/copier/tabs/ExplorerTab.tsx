'use client';

import { useCopier } from '@/lib/copier/store';
import { FileMeta, TreeNode } from '@/lib/copier/types';
import { natKey, shouldIgnoreGlobal } from '@/lib/copier/utils';
import { useMemo, useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';

function buildTree(allMeta: FileMeta[]): TreeNode {
  const root: TreeNode = { name: '', ch: {}, files: [] };
  allMeta.forEach((m) => {
    const parts = m.relPath.split('/');
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!node.ch[parts[i]]) node.ch[parts[i]] = { name: parts[i], ch: {}, files: [] };
      node = node.ch[parts[i]];
    }
    node.files.push(m);
  });
  return root;
}

function getAllFilesInNode(node: TreeNode): FileMeta[] {
  let f = [...node.files];
  Object.values(node.ch).forEach((c) => { f = f.concat(getAllFilesInNode(c)); });
  return f;
}

interface DirItemProps {
  name: string;
  node: TreeNode;
  ignorePatterns: string[];
  selectedFiles: Set<string>;
  onToggle: (relPaths: string[], allSelected: boolean) => void;
  initiallyOpen?: boolean;
}

function DirItem({ name, node, ignorePatterns, selectedFiles, onToggle, initiallyOpen = false }: DirItemProps) {
  const [open, setOpen] = useState(initiallyOpen);
  const allF = useMemo(() => getAllFilesInNode(node), [node]);
  const selCount = allF.filter((m) => selectedFiles.has(m.relPath)).length;
  const allSel = allF.length > 0 && selCount === allF.length;
  const partial = selCount > 0 && selCount < allF.length;

  const icon = selCount === 0 ? '☐' : allSel ? '☑' : '⊟';
  const bgCls = allSel
    ? 'bg-green-50 dark:bg-green-900/20'
    : partial
    ? 'bg-yellow-50 dark:bg-yellow-900/20'
    : '';

  const sortedKeys = Object.keys(node.ch).sort((a, b) => (natKey(a) < natKey(b) ? -1 : 1));

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-1.5 py-1 rounded cursor-pointer min-h-[28px] hover:bg-primary-light transition-colors select-none ${bgCls}`}
        onClick={() => onToggle(allF.map((m) => m.relPath), allSel)}
      >
        <span
          className="text-text2 min-w-[12px] cursor-pointer px-0.5"
          onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        >
          {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </span>
        <span className="text-xs min-w-[18px] text-center">{icon}</span>
        <span className="text-xs text-primary font-semibold break-all">{name}</span>
      </div>
      {open && (
        <div className="pl-4">
          {sortedKeys.map((k) =>
            shouldIgnoreGlobal(k, ignorePatterns) ? null : (
              <DirItem
                key={k}
                name={k}
                node={node.ch[k]}
                ignorePatterns={ignorePatterns}
                selectedFiles={selectedFiles}
                onToggle={onToggle}
                initiallyOpen={initiallyOpen}
              />
            )
          )}
          {node.files
            .sort((a, b) => (natKey(a.name) < natKey(b.name) ? -1 : 1))
            .map((m) => {
              if (shouldIgnoreGlobal(m.name, ignorePatterns)) return null;
              const sel = selectedFiles.has(m.relPath);
              return (
                <div
                  key={m.relPath}
                  data-rp={m.relPath}
                  className={`flex items-center gap-1 px-1.5 py-1 rounded cursor-pointer min-h-[28px] transition-colors select-none
                    ${sel ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-primary-light'}`}
                  onClick={() => onToggle([m.relPath], sel)}
                >
                  <span className="min-w-[12px]" />
                  <span className="text-xs min-w-[18px] text-center">{sel ? '☑' : '☐'}</span>
                  <span className={`text-xs break-all ${m.isBinary ? 'text-danger font-semibold' : 'text-text'}`}>
                    {m.name}
                    {m.isBinary && <span className="ml-1 text-[9px] font-normal opacity-70">(binario)</span>}
                  </span>
                  <span className="text-[10px] text-text2 ml-auto whitespace-nowrap">
                    {(m.size / 1024).toFixed(0)}KB
                  </span>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}

export function ExplorerTab() {
  const { state, dispatch } = useCopier();
  const tree = useMemo(() => buildTree(state.allMeta), [state.allMeta]);

  const [expandVersion, setExpandVersion] = useState(0);
  const [expandMode, setExpandMode] = useState<'none' | 'all' | 'none'>('none');

  function handleExpandAll() {
    setExpandMode('all');
    setExpandVersion((v) => v + 1);
  }

  function handleCollapseAll() {
    setExpandMode('none');
    setExpandVersion((v) => v + 1);
  }

  function handleToggle(relPaths: string[], allSelected: boolean) {
    relPaths.forEach((rp) => {
      dispatch({ type: 'SELECT_FILE', relPath: rp, selected: !allSelected });
    });
  }

  const sortedKeys = Object.keys(tree.ch).sort((a, b) => (natKey(a) < natKey(b) ? -1 : 1));

  return (
    <div className="flex flex-col gap-2 flex-1 overflow-hidden min-h-0">
      <div className="flex items-center justify-between flex-shrink-0">
        <small className="text-text2 text-[11px]">Clique para marcar arquivos e pastas:</small>
        <div className="flex gap-1">
          <button
            className="px-2 py-0.5 border border-border bg-surface2 rounded text-[10px] text-text hover:bg-border transition-colors cursor-pointer"
            onClick={handleExpandAll}
          >
            Expandir tudo
          </button>
          <button
            className="px-2 py-0.5 border border-border bg-surface2 rounded text-[10px] text-text hover:bg-border transition-colors cursor-pointer"
            onClick={handleCollapseAll}
          >
            Recolher tudo
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto border border-border rounded-md bg-surface2 p-1 min-h-0">
        {!state.allMeta.length ? (
          <div className="p-5 text-center text-text2 text-xs">Selecione uma pasta de entrada.</div>
        ) : (
          <div key={expandVersion}>
            {sortedKeys.map((k) =>
              shouldIgnoreGlobal(k, state.ignorePatterns) ? null : (
                <DirItem
                  key={k}
                  name={k}
                  node={tree.ch[k]}
                  ignorePatterns={state.ignorePatterns}
                  selectedFiles={state.selectedFiles}
                  onToggle={handleToggle}
                  initiallyOpen={expandMode === 'all'}
                />
              )
            )}
            {tree.files.map((m) => {
              if (shouldIgnoreGlobal(m.name, state.ignorePatterns)) return null;
              const sel = state.selectedFiles.has(m.relPath);
              return (
                <div
                  key={m.relPath}
                  className={`flex items-center gap-1 px-1.5 py-1 rounded cursor-pointer transition-colors select-none
                    ${sel ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-primary-light'}`}
                  onClick={() => dispatch({ type: 'SELECT_FILE', relPath: m.relPath, selected: !sel })}
                >
                  <span className="min-w-[12px]" />
                  <span className="text-xs min-w-[18px] text-center">{sel ? '☑' : '☐'}</span>
                  <span className={`text-xs break-all ${m.isBinary ? 'text-danger font-semibold' : 'text-text'}`}>
                    {m.name}
                    {m.isBinary && <span className="ml-1 text-[9px] font-normal opacity-70">(binario)</span>}
                  </span>
                  <span className="text-[10px] text-text2 ml-auto whitespace-nowrap">
                    {(m.size / 1024).toFixed(0)}KB
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

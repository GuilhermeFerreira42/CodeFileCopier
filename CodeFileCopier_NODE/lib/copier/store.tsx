'use client';

import React, { createContext, useCallback, useContext, useEffect, useRef } from 'react';
import { ALL_IGNORE_PATTERNS, IGNORE_STORAGE_KEY } from './constants';
import { ArbFile, FileMeta, LogEntry, LogType, TabId, ToastEntry, ToastType, TreeNode } from './types';
import { extractZip, getExt, getRelPath, isBinExt, natKey, readFileSingle, shouldIgnoreGlobal, shouldIgnoreSize, sleep, sortArrBy } from './utils';

export interface CopierState {
  allMeta: FileMeta[];
  allExts: string[];
  selectedFiles: Set<string>;
  selectedExts: Set<string>;
  arbFiles: ArbFile[];
  giFileRules: string[];
  giManualRules: string[];
  giSelIdx: number;
  applyGI: boolean;
  ignorePatterns: string[];
  ignoreModalOpen: boolean;
  lastOutput: string;
  activeTab: TabId;
  searchResults: string[];
  treeData: TreeNode | null;
  logEntries: LogEntry[];
  logCount: number;
  logCollapsed: boolean;
  configCollapsed: boolean;
  cancelFlag: boolean;
  srcDir: string;
  outName: string;
  sortMode: 'natural' | 'alpha';
  sizeFilterEnabled: boolean;
  maxSizeKb: number;
  isLoading: boolean;
  loadingText: string;
  progress: { value: number | 'pulse' | null; max: number; label: string };
  toasts: ToastEntry[];
  modalOpen: boolean;
  modalContent: string;
  modalFilename: string;
  modalCount: number;
  modalChars: number;
  toastCounter: number;
  logCounter: number;
}

export type CopierAction =
  | { type: 'SET_ALL_META'; payload: FileMeta[] }
  | { type: 'SET_ALL_EXTS'; payload: string[] }
  | { type: 'SELECT_EXT'; ext: string; selected: boolean }
  | { type: 'SEL_ALL_EXT' }
  | { type: 'DESEL_ALL_EXT' }
  | { type: 'SELECT_FILE'; relPath: string; selected: boolean }
  | { type: 'SEL_ALL_FILES' }
  | { type: 'DESEL_ALL_FILES' }
  | { type: 'SELECT_SEARCH_ALL' }
  | { type: 'DESEL_SEARCH_ALL' }
  | { type: 'SET_SEARCH_RESULTS'; payload: string[] }
  | { type: 'SET_ARB_FILES'; payload: ArbFile[] }
  | { type: 'SET_GI_FILE_RULES'; payload: string[] }
  | { type: 'SET_GI_MANUAL_RULES'; payload: string[] }
  | { type: 'SET_GI_SEL_IDX'; payload: number }
  | { type: 'SET_APPLY_GI'; payload: boolean }
  | { type: 'SET_IGNORE_PATTERNS'; payload: string[] }
  | { type: 'TOGGLE_IGNORE_PATTERN'; pattern: string; active: boolean }
  | { type: 'OPEN_IGNORE_MODAL' }
  | { type: 'CLOSE_IGNORE_MODAL' }
  | { type: 'SET_LAST_OUTPUT'; payload: string }
  | { type: 'SET_ACTIVE_TAB'; payload: TabId }
  | { type: 'SET_TREE_DATA'; payload: TreeNode | null }
  | { type: 'ADD_LOG'; entry: LogEntry }
  | { type: 'CLEAR_LOG' }
  | { type: 'TOGGLE_LOG_COLLAPSED' }
  | { type: 'TOGGLE_CONFIG_COLLAPSED' }
  | { type: 'SET_CANCEL_FLAG'; payload: boolean }
  | { type: 'SET_SRC_DIR'; payload: string }
  | { type: 'SET_OUT_NAME'; payload: string }
  | { type: 'SET_SORT_MODE'; payload: 'natural' | 'alpha' }
  | { type: 'SET_SIZE_FILTER'; enabled: boolean; maxKb: number }
  | { type: 'SET_LOADING'; isLoading: boolean; text?: string }
  | { type: 'SET_PROGRESS'; value: number | 'pulse' | null; max?: number; label?: string }
  | { type: 'ADD_TOAST'; entry: ToastEntry }
  | { type: 'REMOVE_TOAST'; id: number }
  | { type: 'SHOW_MODAL'; content: string; filename: string; count: number; chars: number }
  | { type: 'CLOSE_MODAL' }
  | { type: 'CLEAR_ALL' };

const initialState: CopierState = {
  allMeta: [],
  allExts: [],
  selectedFiles: new Set(),
  selectedExts: new Set(),
  arbFiles: [],
  giFileRules: [],
  giManualRules: [],
  giSelIdx: -1,
  applyGI: false,
  ignorePatterns: [...ALL_IGNORE_PATTERNS],
  ignoreModalOpen: false,
  lastOutput: '',
  activeTab: 'ext',
  searchResults: [],
  treeData: null,
  logEntries: [],
  logCount: 0,
  logCollapsed: false,
  configCollapsed: false,
  cancelFlag: false,
  srcDir: '',
  outName: 'codigo_completo.txt',
  sortMode: 'natural',
  sizeFilterEnabled: false,
  maxSizeKb: 500,
  isLoading: false,
  loadingText: 'Carregando…',
  progress: { value: null, max: 100, label: '' },
  toasts: [],
  modalOpen: false,
  modalContent: '',
  modalFilename: 'codigo_completo.txt',
  modalCount: 0,
  modalChars: 0,
  toastCounter: 0,
  logCounter: 0,
};

function reducer(state: CopierState, action: CopierAction): CopierState {
  switch (action.type) {
    case 'SET_ALL_META':
      return { ...state, allMeta: action.payload };
    case 'SET_ALL_EXTS':
      return { ...state, allExts: action.payload };
    case 'SELECT_EXT': {
      const s = new Set(state.selectedExts);
      action.selected ? s.add(action.ext) : s.delete(action.ext);
      return { ...state, selectedExts: s };
    }
    case 'SEL_ALL_EXT':
      return { ...state, selectedExts: new Set(state.allExts) };
    case 'DESEL_ALL_EXT':
      return { ...state, selectedExts: new Set() };
    case 'SELECT_FILE': {
      const s = new Set(state.selectedFiles);
      action.selected ? s.add(action.relPath) : s.delete(action.relPath);
      return { ...state, selectedFiles: s };
    }
    case 'SEL_ALL_FILES':
      return { ...state, selectedFiles: new Set(state.allMeta.map((m) => m.relPath)) };
    case 'DESEL_ALL_FILES':
      return { ...state, selectedFiles: new Set() };
    case 'SELECT_SEARCH_ALL':
      return { ...state, selectedFiles: new Set([...state.selectedFiles, ...state.searchResults]) };
    case 'DESEL_SEARCH_ALL': {
      const s = new Set(state.selectedFiles);
      state.searchResults.forEach((rp) => s.delete(rp));
      return { ...state, selectedFiles: s };
    }
    case 'SET_SEARCH_RESULTS':
      return { ...state, searchResults: action.payload };
    case 'SET_ARB_FILES':
      return { ...state, arbFiles: action.payload };
    case 'SET_GI_FILE_RULES':
      return { ...state, giFileRules: action.payload };
    case 'SET_GI_MANUAL_RULES':
      return { ...state, giManualRules: action.payload };
    case 'SET_GI_SEL_IDX':
      return { ...state, giSelIdx: action.payload };
    case 'SET_APPLY_GI':
      return { ...state, applyGI: action.payload };
    case 'SET_IGNORE_PATTERNS':
      return { ...state, ignorePatterns: action.payload };
    case 'TOGGLE_IGNORE_PATTERN': {
      const set = new Set(state.ignorePatterns);
      action.active ? set.add(action.pattern) : set.delete(action.pattern);
      // Mantém a ordem canônica de ALL_IGNORE_PATTERNS.
      return { ...state, ignorePatterns: ALL_IGNORE_PATTERNS.filter((p) => set.has(p)) };
    }
    case 'OPEN_IGNORE_MODAL':
      return { ...state, ignoreModalOpen: true };
    case 'CLOSE_IGNORE_MODAL':
      return { ...state, ignoreModalOpen: false };
    case 'SET_LAST_OUTPUT':
      return { ...state, lastOutput: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_TREE_DATA':
      return { ...state, treeData: action.payload };
    case 'ADD_LOG': {
      const entries = state.logCollapsed ? state.logEntries : [...state.logEntries, action.entry].slice(-500);
      return { ...state, logEntries: entries, logCount: state.logCount + 1 };
    }
    case 'CLEAR_LOG':
      return { ...state, logEntries: [], logCount: 0 };
    case 'TOGGLE_LOG_COLLAPSED':
      return { ...state, logCollapsed: !state.logCollapsed };
    case 'TOGGLE_CONFIG_COLLAPSED':
      return { ...state, configCollapsed: !state.configCollapsed };
    case 'SET_CANCEL_FLAG':
      return { ...state, cancelFlag: action.payload };
    case 'SET_SRC_DIR':
      return { ...state, srcDir: action.payload };
    case 'SET_OUT_NAME':
      return { ...state, outName: action.payload };
    case 'SET_SORT_MODE':
      return { ...state, sortMode: action.payload };
    case 'SET_SIZE_FILTER':
      return { ...state, sizeFilterEnabled: action.enabled, maxSizeKb: action.maxKb };
    case 'SET_LOADING':
      return { ...state, isLoading: action.isLoading, loadingText: action.text ?? state.loadingText };
    case 'SET_PROGRESS':
      return {
        ...state,
        progress: { value: action.value, max: action.max ?? 100, label: action.label ?? '' },
      };
    case 'ADD_TOAST': {
      const toasts = [...state.toasts, action.entry].slice(-5);
      return { ...state, toasts, toastCounter: state.toastCounter + 1 };
    }
    case 'REMOVE_TOAST':
      return { ...state, toasts: state.toasts.filter((t) => t.id !== action.id) };
    case 'SHOW_MODAL':
      return {
        ...state,
        modalOpen: true,
        modalContent: action.content,
        modalFilename: action.filename,
        modalCount: action.count,
        modalChars: action.chars,
      };
    case 'CLOSE_MODAL':
      return { ...state, modalOpen: false };
    case 'CLEAR_ALL':
      return {
        ...initialState,
        ignorePatterns: state.ignorePatterns,
        sortMode: state.sortMode,
        configCollapsed: state.configCollapsed,
        logCollapsed: state.logCollapsed,
        toastCounter: state.toastCounter,
        logCounter: state.logCounter,
      };
    default:
      return state;
  }
}

// Context
interface CopierContextValue {
  state: CopierState;
  dispatch: React.Dispatch<CopierAction>;
  log: (msg: string, type?: LogType) => void;
  toast: (msg: string, type?: ToastType, ms?: number) => void;
  loadFiles: (files: File[]) => Promise<void>;
  loadZip: (zipFile: File) => Promise<void>;
}

const CopierContext = createContext<CopierContextValue | null>(null);

export function CopierProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = React.useReducer(reducer, initialState);
  const logCounterRef = useRef(0);
  const toastCounterRef = useRef(0);
  const hydratedRef = useRef(false);

  // Carrega padrões globais salvos (uma vez, após montar no cliente).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(IGNORE_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          const valid = parsed.filter((p): p is string => typeof p === 'string' && ALL_IGNORE_PATTERNS.includes(p));
          dispatch({ type: 'SET_IGNORE_PATTERNS', payload: valid });
        }
      }
    } catch {
      /* ignora localStorage indisponível ou corrompido */
    }
    hydratedRef.current = true;
  }, []);

  // Persiste padrões globais sempre que mudarem (após a hidratação inicial).
  useEffect(() => {
    if (!hydratedRef.current) return;
    try {
      localStorage.setItem(IGNORE_STORAGE_KEY, JSON.stringify(state.ignorePatterns));
    } catch {
      /* ignora falha de escrita */
    }
  }, [state.ignorePatterns]);

  const log = useCallback((msg: string, type: LogType = '') => {
    logCounterRef.current++;
    const entry: LogEntry = {
      id: logCounterRef.current,
      msg,
      type,
      time: new Date().toLocaleTimeString('pt-BR'),
    };
    dispatch({ type: 'ADD_LOG', entry });
  }, []);

  const toast = useCallback((msg: string, type: ToastType = 'ok', ms = 2800) => {
    toastCounterRef.current++;
    const id = toastCounterRef.current;
    dispatch({ type: 'ADD_TOAST', entry: { id, msg, type } });
    setTimeout(() => dispatch({ type: 'REMOVE_TOAST', id }), ms);
  }, []);

  const loadFiles = useCallback(
    async (files: File[]) => {
      dispatch({ type: 'SET_CANCEL_FLAG', payload: false });
      dispatch({ type: 'SET_LOADING', isLoading: true, text: 'Lendo metadados…' });
      dispatch({ type: 'SET_PROGRESS', value: 'pulse', label: 'Analisando arquivos…' });
      log('⟳ Iniciando varredura (apenas metadados)…', 'info');

      const topDir = getRelPath(files[0]).split('/')[0];
      dispatch({ type: 'SET_SRC_DIR', payload: topDir });

      const activePatterns = state.ignorePatterns;
      const sizeFilter = state.sizeFilterEnabled;
      const maxKb = state.maxSizeKb;

      const allMeta: FileMeta[] = [];
      const BATCH = 200;

      for (let i = 0; i < files.length; i += BATCH) {
        const batch = files.slice(i, Math.min(i + BATCH, files.length));
        for (const file of batch) {
          const relPath = getRelPath(file);
          const parts = relPath.split('/');
          const name = parts[parts.length - 1];
          let skip = false;
          for (const p of parts) {
            if (shouldIgnoreGlobal(p, activePatterns)) { skip = true; break; }
          }
          if (skip) continue;
          if (shouldIgnoreSize(file.size, sizeFilter, maxKb)) continue;
          const ext = getExt(name);
          const bin = isBinExt(name);
          const estLines = bin ? 0 : Math.round(file.size / 45);
          allMeta.push({ name, relPath, ext, size: file.size, isBinary: bin, lines: estLines, file });
        }
        dispatch({ type: 'SET_PROGRESS', value: Math.min(i + BATCH, files.length), max: files.length, label: `Analisando ${Math.min(i + BATCH, files.length)}/${files.length}…` });
        dispatch({ type: 'SET_LOADING', isLoading: true, text: `Metadados: ${allMeta.length} arquivos encontrados…` });
        await sleep(0);
      }

      const sorted = sortArrBy(allMeta, (m) => m.relPath, state.sortMode);
      const extSet = new Set(sorted.map((m) => m.ext));
      const allExts = [...extSet].sort((a, b) => {
        const ka = state.sortMode === 'natural' ? natKey(a) : a.toLowerCase();
        const kb = state.sortMode === 'natural' ? natKey(b) : b.toLowerCase();
        return ka < kb ? -1 : ka > kb ? 1 : 0;
      });

      dispatch({ type: 'SET_ALL_META', payload: sorted });
      dispatch({ type: 'SET_ALL_EXTS', payload: allExts });

      // .gitignore
      const giFile = sorted.find((m) => m.name === '.gitignore');
      if (giFile) {
        const txt = await readFileSingle(giFile.file);
        const rules = txt ? txt.split('\n').map((l) => l.trimEnd()) : [];
        dispatch({ type: 'SET_GI_FILE_RULES', payload: rules });
        log(`✅ .gitignore: ${rules.length} linha(s).`, 'ok');
      } else {
        dispatch({ type: 'SET_GI_FILE_RULES', payload: [] });
        log('⚠ Nenhum .gitignore encontrado.', 'warn');
      }

      dispatch({ type: 'SET_LOADING', isLoading: false });
      dispatch({ type: 'SET_PROGRESS', value: null });
      log(`✓ ${sorted.length} arquivo(s), ${allExts.length} extensão(ões).`, 'ok');
    },
    [state.ignorePatterns, state.sizeFilterEnabled, state.maxSizeKb, state.sortMode, log]
  );

  const loadZip = useCallback(
    async (zipFile: File) => {
      dispatch({ type: 'SET_LOADING', isLoading: true, text: 'Descompactando ZIP…' });
      dispatch({ type: 'SET_PROGRESS', value: 'pulse', label: 'Extraindo arquivos do ZIP…' });
      log(`⟳ Descompactando "${zipFile.name}"…`, 'info');
      try {
        const files = await extractZip(zipFile);
        if (!files.length) {
          dispatch({ type: 'SET_LOADING', isLoading: false });
          dispatch({ type: 'SET_PROGRESS', value: null });
          log('⚠ ZIP vazio ou sem arquivos válidos.', 'warn');
          toast('ZIP vazio ou inválido.', 'warn');
          return;
        }
        log(`✓ ${files.length} arquivo(s) extraído(s) do ZIP.`, 'ok');
        await loadFiles(files);
      } catch (err) {
        dispatch({ type: 'SET_LOADING', isLoading: false });
        dispatch({ type: 'SET_PROGRESS', value: null });
        const msg = err instanceof Error ? err.message : 'erro desconhecido';
        log(`✗ Falha ao ler ZIP: ${msg}`, 'err');
        toast('Falha ao ler o ZIP.', 'err');
      }
    },
    [loadFiles, log, toast]
  );

  const value: CopierContextValue = { state, dispatch, log, toast, loadFiles, loadZip };

  return <CopierContext.Provider value={value}>{children}</CopierContext.Provider>;
}

export function useCopier(): CopierContextValue {
  const ctx = useContext(CopierContext);
  if (!ctx) throw new Error('useCopier must be used inside CopierProvider');
  return ctx;
}

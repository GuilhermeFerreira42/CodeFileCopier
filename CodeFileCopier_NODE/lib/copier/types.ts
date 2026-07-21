export interface FileMeta {
  name: string;
  relPath: string;
  ext: string;
  size: number;
  isBinary: boolean;
  lines: number;
  file: File;
}

export interface ArbFile {
  name: string;
  content: string | null;
  size: number;
}

export type LogType = '' | 'ok' | 'warn' | 'err' | 'info';

export interface LogEntry {
  id: number;
  msg: string;
  type: LogType;
  time: string;
}

export type ToastType = 'ok' | 'warn' | 'err';

export interface ToastEntry {
  id: number;
  msg: string;
  type: ToastType;
}

export type TabId = 'ext' | 'files' | 'search' | 'explorer' | 'arb' | 'gi';

export type SortMode = 'natural' | 'alpha';

export interface TreeNode {
  name: string;
  ch: Record<string, TreeNode>;
  files: FileMeta[];
}

export interface PatternDef {
  pattern: string;
  desc: string;
}

export interface PatternGroup {
  id: string;
  label: string;
  patterns: PatternDef[];
}

/**
 * File estendido com caminho relativo sintético.
 * Usado por arquivos extraídos de um ZIP, onde `webkitRelativePath`
 * não pode ser definido diretamente.
 */
export type CopierFile = File & { _relPath?: string };

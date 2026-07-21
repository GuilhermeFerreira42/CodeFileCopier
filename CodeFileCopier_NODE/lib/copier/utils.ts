import { unzip } from 'fflate';
import { BINARY_EXTS } from './constants';
import { CopierFile, FileMeta, TreeNode } from './types';

export function esc(s: string): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function natKey(s: string): string {
  return s.replace(/(\d+)/g, (m) => m.padStart(20, '0'));
}

export function sortArr(arr: string[], mode: 'natural' | 'alpha'): string[] {
  return [...arr].sort((a, b) => {
    const ka = mode === 'natural' ? natKey(a) : a.toLowerCase();
    const kb = mode === 'natural' ? natKey(b) : b.toLowerCase();
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
}

export function sortArrBy<T>(arr: T[], fn: (item: T) => string, mode: 'natural' | 'alpha'): T[] {
  return [...arr].sort((a, b) => {
    const ka = mode === 'natural' ? natKey(fn(a)) : fn(a).toLowerCase();
    const kb = mode === 'natural' ? natKey(fn(b)) : fn(b).toLowerCase();
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
}

export function getExt(name: string): string {
  const d = name.lastIndexOf('.');
  if (d <= 0) return name.startsWith('.') ? name : '(sem extensão)';
  return name.slice(d).toLowerCase();
}

export function isBinExt(name: string): boolean {
  return BINARY_EXTS.has(getExt(name));
}

export function fnMatch(name: string, pat: string): boolean {
  const re = '^' + pat.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$';
  return new RegExp(re, 'i').test(name);
}

export function shouldIgnoreGlobal(name: string, activePatterns: string[]): boolean {
  if (!activePatterns.length) return false;
  return activePatterns.some((p) => (p.includes('*') ? fnMatch(name, p) : name === p));
}

/** Caminho relativo de um File (diretório real ou extraído de ZIP). */
export function getRelPath(file: File): string {
  return (file as CopierFile)._relPath || file.webkitRelativePath || file.name;
}

/** Estimativa simples de tokens para LLMs (~4 caracteres por token). */
export function estimateTokens(chars: number): number {
  return Math.ceil(chars / 4);
}

/**
 * Extrai um arquivo .zip em memória e retorna uma lista de File com
 * caminho relativo sintético (_relPath), imitando um diretório real.
 * O nome do zip (sem extensão) vira a pasta raiz.
 */
export function extractZip(zipFile: File): Promise<CopierFile[]> {
  return new Promise((resolve, reject) => {
    const rootName = zipFile.name.replace(/\.zip$/i, '') || 'zip';
    zipFile.arrayBuffer().then((buf) => {
      unzip(new Uint8Array(buf), (err, data) => {
        if (err) {
          reject(err);
          return;
        }
        const out: CopierFile[] = [];
        for (const [path, bytes] of Object.entries(data)) {
          // Ignora entradas de diretório (terminam com "/") e vazias.
          if (path.endsWith('/')) continue;
          const cleanPath = path.replace(/^\.?\//, '');
          if (!cleanPath) continue;
          const name = cleanPath.split('/').pop() as string;
          const relPath = `${rootName}/${cleanPath}`;
          // Copia para um ArrayBuffer novo para evitar problemas com SharedArrayBuffer.
          const copy = bytes.slice();
          const f = new File([copy], name) as CopierFile;
          f._relPath = relPath;
          out.push(f);
        }
        resolve(out);
      });
    }).catch(reject);
  });
}

export function shouldIgnoreSize(size: number, filterEnabled: boolean, maxKb: number): boolean {
  if (!filterEnabled) return false;
  return size > maxKb * 1024;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function formatSize(bytes: number): string {
  return (bytes / 1024).toFixed(0) + 'KB';
}

export function readFileSingle(file: File): Promise<string | null> {
  return new Promise((resolve) => {
    const r = new FileReader();
    r.onload = (e) => resolve(e.target?.result as string);
    r.onerror = () => resolve(null);
    r.readAsText(file, 'UTF-8');
  });
}

export async function readFilesBatch(
  metas: FileMeta[],
  onProgress: (done: number, total: number) => void
): Promise<Map<string, string | null>> {
  const BATCH = 15;
  const results = new Map<string, string | null>();
  for (let i = 0; i < metas.length; i += BATCH) {
    const batch = metas.slice(i, Math.min(i + BATCH, metas.length));
    await Promise.all(
      batch.map((m) => {
        if (m.isBinary) return Promise.resolve(results.set(m.relPath, null));
        return readFileSingle(m.file).then((txt) => results.set(m.relPath, txt));
      })
    );
    onProgress(Math.min(i + BATCH, metas.length), metas.length);
    await sleep(0);
  }
  return results;
}

export function giMatches(
  relPath: string,
  applyGI: boolean,
  giFileRules: string[],
  giManualRules: string[]
): boolean {
  if (!applyGI) return false;
  const rules = [...giFileRules, ...giManualRules].filter((l) => l.trim() && !l.trim().startsWith('#'));
  let ignored = false;
  const norm = relPath.replace(/\\/g, '/');
  for (const raw of rules) {
    let neg = raw.startsWith('!');
    let rule = (neg ? raw.slice(1) : raw).trim();
    if (!rule) continue;
    const dirOnly = rule.endsWith('/');
    if (dirOnly) rule = rule.slice(0, -1);
    let regStr = rule
      .replace(/[.+^${}()|[\]\\]/g, '\\$&')
      .replace(/\*\*/g, '§')
      .replace(/\*/g, '[^/]*')
      .replace(/\?/g, '[^/]')
      .replace(/§/g, '.*');
    const hasSlash = rule.replace(/\/$/, '').includes('/');
    let matched = false;
    if (hasSlash) {
      matched = new RegExp(`^${regStr}(/.*)?$`).test(norm);
    } else {
      const base = norm.split('/').pop() ?? '';
      matched = new RegExp(`^${regStr}$`).test(base) || new RegExp(`(^|/)${regStr}(/|$)`).test(norm);
    }
    if (matched) ignored = !neg;
  }
  return ignored;
}

export function buildHeader(src: string, count: number, filters: string[]): string {
  const now = new Date().toLocaleString('pt-BR');
  let h = '='.repeat(60) + '\n  COPIADOR DE CÓDIGO v2.0\n' + '='.repeat(60) + '\n';
  h += `  Data/Hora     : ${now}\n  Origem        : ${src}\n  Total arquivos: ${count}\n`;
  if (filters.length) h += `  Filtros       : ${filters.join(', ')}\n`;
  h += '='.repeat(60) + '\n\n';
  return h;
}

export function buildTreeTxt(metas: FileMeta[], rootName: string): string {
  const root: TreeNode = { name: rootName, ch: {}, files: [] };
  metas.forEach((m) => {
    const parts = m.relPath.split('/');
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!node.ch[parts[i]]) node.ch[parts[i]] = { name: parts[i], ch: {}, files: [] };
      node = node.ch[parts[i]];
    }
    node.files.push(m);
  });
  function print(node: TreeNode, prefix: string): string {
    let out = '';
    const keys = Object.keys(node.ch).sort();
    const items = [
      ...keys.map((k) => ({ t: 'd' as const, name: k, node: node.ch[k] })),
      ...node.files.map((f) => ({ t: 'f' as const, name: f.name, node: null as unknown as TreeNode })),
    ];
    items.forEach((c, i) => {
      const last = i === items.length - 1;
      out += prefix + (last ? '`-- ' : '|-- ') + c.name + '\n';
      if (c.t === 'd') out += print(c.node, prefix + (last ? '  ' : '| '));
    });
    return out;
  }
  return root.name + '\n' + print(root, '');
}

export function buildFileOutput(
  metas: FileMeta[],
  contentMap: Map<string, string | null>,
  srcDir: string,
  applyGI: boolean
): { out: string; copied: number; skipped: number } {
  const filters: string[] = [];
  if (applyGI) filters.push('.gitignore');

  let out = buildHeader(srcDir, metas.length, filters);
  let copied = 0;
  let skipped = 0;

  for (const m of metas) {
    const content = contentMap.get(m.relPath);
    if (content == null) {
      skipped++;
      continue;
    }
    const sep = '='.repeat(42) + '\n';
    out += sep + `Conteúdo de ${m.name} (caminho: ${m.relPath}) [enc: utf-8]:\n` + sep + content + '\n\n';
    copied++;
  }

  out += '\n' + '='.repeat(42) + '\nEstrutura de pastas:\n' + '='.repeat(42) + '\n';
  out += buildTreeTxt(metas, srcDir);

  return { out, copied, skipped };
}

export function buildArbOutput(files: { name: string; content: string | null; size: number }[]): {
  out: string;
  n: number;
} {
  let out = buildHeader('Arquivos Avulsos', files.length, []);
  let n = 0;
  files.forEach((f) => {
    if (!f.content) return;
    out += '='.repeat(42) + '\n' + `Conteúdo de ${f.name}:\n` + '='.repeat(42) + '\n' + f.content + '\n\n';
    n++;
  });
  out += '\n' + '='.repeat(42) + '\nArquivos:\n' + '='.repeat(42) + '\n';
  files.forEach((f) => (out += `- ${f.name}\n`));
  return { out, n };
}

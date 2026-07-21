import { PatternGroup } from './types';

/**
 * Padrões globais organizados por categoria, cada um com descrição legível.
 * O usuário gerencia individualmente pelo modal de padrões globais.
 */
export const PATTERN_GROUPS: PatternGroup[] = [
  {
    id: 'vcs',
    label: 'Controle de versão',
    patterns: [
      { pattern: '.git', desc: 'Metadados do repositório Git' },
    ],
  },
  {
    id: 'node',
    label: 'Node.js / JavaScript',
    patterns: [
      { pattern: 'node_modules', desc: 'Dependências do Node.js' },
      { pattern: 'dist', desc: 'Saída de build compilada' },
      { pattern: 'build', desc: 'Diretório de build' },
      { pattern: '*.log', desc: 'Arquivos de log' },
    ],
  },
  {
    id: 'python',
    label: 'Python',
    patterns: [
      { pattern: '__pycache__', desc: 'Cache de bytecode do Python' },
      { pattern: 'venv', desc: 'Ambiente virtual Python' },
      { pattern: '.venv', desc: 'Ambiente virtual Python (oculto)' },
      { pattern: 'env', desc: 'Ambiente virtual Python' },
      { pattern: '.env', desc: 'Ambiente / variáveis de ambiente' },
      { pattern: '.tox', desc: 'Cache do Tox' },
      { pattern: '.mypy_cache', desc: 'Cache do MyPy' },
      { pattern: '.pytest_cache', desc: 'Cache do Pytest' },
      { pattern: '*.pyc', desc: 'Bytecode Python compilado' },
      { pattern: '*.pyo', desc: 'Bytecode Python otimizado' },
      { pattern: '*.egg-info', desc: 'Metadados de pacote Python' },
    ],
  },
  {
    id: 'os',
    label: 'Sistema operacional',
    patterns: [
      { pattern: '.DS_Store', desc: 'Metadados de pasta do macOS' },
      { pattern: 'Thumbs.db', desc: 'Cache de miniaturas do Windows' },
    ],
  },
];

/** Lista achatada de todos os padrões disponíveis. */
export const ALL_IGNORE_PATTERNS: string[] = PATTERN_GROUPS.flatMap((g) =>
  g.patterns.map((p) => p.pattern)
);

/** Mapa padrão → descrição, para exibição rápida. */
export const PATTERN_DESC: Record<string, string> = Object.fromEntries(
  PATTERN_GROUPS.flatMap((g) => g.patterns.map((p) => [p.pattern, p.desc]))
);

/** Chave usada para persistir os padrões ativos no localStorage. */
export const IGNORE_STORAGE_KEY = 'copier:ignorePatterns:v1';

export const BINARY_EXTS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg', '.webp',
  '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.wav', '.ogg',
  '.zip', '.tar', '.gz', '.rar', '.7z',
  '.exe', '.dll', '.so', '.dylib', '.bin', '.dat',
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.ttf', '.woff', '.woff2', '.eot',
  '.db', '.sqlite', '.sqlite3',
]);

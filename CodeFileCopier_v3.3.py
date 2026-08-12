#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==================================================================
 COPIADOR DE CÓDIGO — Python Edition (v3.0)
==================================================================
Conversão integral do "Copiador de Código v2.1" (HTML/JS) para uma
aplicação desktop em Python usando apenas a biblioteca padrão
(tkinter). Nenhuma dependência externa é necessária — basta ter o
Python 3 instalado.

Por que Python é mais rápido em pastas grandes?
------------------------------------------------
No navegador, o <input webkitdirectory> precisa enumerar TODOS os
arquivos da árvore (inclusive node_modules, .git, venv, etc.) antes
mesmo do JavaScript poder filtrar qualquer coisa. Em Python usamos
os.walk() e "podamos" (pruning) os diretórios ignorados em tempo
real, ANTES de descer neles — ou seja, pastas como node_modules,
.git, __pycache__, venv, dist, build etc. nunca chegam a ser
percorridas quando os padrões globais correspondentes estão
ativos. Isso é o que torna a varredura de pastas grandes muito mais
rápida por aqui.

Todas as funcionalidades da versão HTML foram preservadas:
  • Seleção de pasta de entrada (ou importação de .zip)
  • Aba Extensões (seleção por extensão, com ordenação por coluna)
  • Aba Arquivos (checklist com busca)
  • Aba Buscar Nome (cola texto tipo "git status" e localiza arquivos)
  • Aba Explorador (árvore de pastas com seleção em cascata)
  • Aba Avulsos (arquivos soltos de qualquer lugar)
  • Aba Gitignore (aplica regras do .gitignore do projeto + regras manuais)
  • Padrões globais a ignorar (.git, node_modules, __pycache__, venv, etc.)
  • Filtro por tamanho máximo de arquivo
  • Geração de saída com cabeçalho, conteúdo dos arquivos e árvore de pastas
  • Cópia para a área de transferência e download (salvar) do .txt
  • Log de atividades, barra de progresso, modo escuro persistente
==================================================================
"""

"""
==================================================================
 AJUSTES DE RESPONSIVIDADE (v3.2)
==================================================================
- Alturas fixas removidas de Treeviews, Listboxes e campos de texto
  para permitir expansão dinâmica conforme o tamanho da janela.
- O layout agora distribui o espaço vertical de forma inteligente:
  o Notebook (abas) ocupa todo o espaço disponível, enquanto os
  painéis de configuração, ações e log mantêm proporções mínimas.
- Layout principal em pack: notebook (único expand=True) absorve todo espaço extra.
- Frames fixos (header, config, counter, actions, log, status) drasticamente compactados.
- Reduzido minsize para 640x400, permitindo uso em telas menores.
- Todos os componentes internos acompanham o redimensionamento
  sem necessidade de scrollbars.
==================================================================
"""


import os
import re
import io
import sys
import json
import time
import queue
import shutil
import zipfile
import fnmatch
import tempfile
import threading
import traceback
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ------------------------------------------------------------------
# Suporte a arrastar-e-soltar (drag & drop) — OPCIONAL.
# O Tkinter puro não suporta arrastar arquivos do sistema operacional
# para dentro da janela. Para isso usamos a biblioteca "tkinterdnd2"
# (pip install tkinterdnd2). Se ela não estiver instalada, o programa
# continua funcionando normalmente — apenas sem o recurso de
# arrastar-e-soltar (os botões "Pasta…", "ZIP…" e "Adicionar…"
# continuam funcionando de qualquer forma).
# ------------------------------------------------------------------
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None
    TkinterDnD = None

_BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk

# ==================================================================
# CONSTANTES
# ==================================================================
APP_TITLE = "📁 Copiador de Código — Python Edition v3.0"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".code_copier_config.json")

CHECK_ON = "☑"
CHECK_OFF = "☐"
CHECK_PARTIAL = "⊟"

PATTERN_GROUPS = [
    {"id": "vcs", "label": "Controle de versão",
     "patterns": [(".git", "Metadados do repositório Git")]},
    {"id": "node", "label": "Node.js / JavaScript",
     "patterns": [
         ("node_modules", "Dependências do Node.js"),
         ("dist", "Saída de build compilada"),
         ("build", "Diretório de build"),
         ("*.log", "Arquivos de log"),
     ]},
    {"id": "python", "label": "Python",
     "patterns": [
         ("__pycache__", "Cache de bytecode do Python"),
         ("venv", "Ambiente virtual Python"),
         (".venv", "Ambiente virtual Python (oculto)"),
         ("env", "Ambiente virtual Python"),
         (".env", "Ambiente / variáveis de ambiente"),
         (".tox", "Cache do Tox"),
         (".mypy_cache", "Cache do MyPy"),
         (".pytest_cache", "Cache do Pytest"),
         ("*.pyc", "Bytecode Python compilado"),
         ("*.pyo", "Bytecode Python otimizado"),
         ("*.egg-info", "Metadados de pacote Python"),
     ]},
    {"id": "os", "label": "Sistema operacional",
     "patterns": [
         (".DS_Store", "Metadados de pasta do macOS"),
         ("Thumbs.db", "Cache de miniaturas do Windows"),
     ]},
]
ALL_IGNORE_PATTERNS = [p for g in PATTERN_GROUPS for p, _ in g["patterns"]]

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".ogg",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".ttf", ".woff", ".woff2", ".eot",
    ".db", ".sqlite", ".sqlite3",
}

_REGEX_ESCAPE = re.compile(r'[.+^${}()|\[\]\\]')


# ==================================================================
# UTILITÁRIOS
# ==================================================================
def nat_key(s):
    """Chave de ordenação 'natural' (números tratados por valor, não por dígito)."""
    return re.sub(r'\d+', lambda m: m.group().zfill(20), s)


def sort_list(items, natural=True):
    if natural:
        return sorted(items, key=lambda x: nat_key(x))
    return sorted(items, key=lambda x: x.lower())


def sort_list_by(items, keyfn, natural=True):
    if natural:
        return sorted(items, key=lambda x: nat_key(keyfn(x)))
    return sorted(items, key=lambda x: keyfn(x).lower())


def get_ext(name):
    d = name.rfind('.')
    if d <= 0:
        return name if name.startswith('.') else '(sem extensão)'
    return name[d:].lower()


def is_bin_ext(name):
    return get_ext(name) in BINARY_EXTS


def fn_match(name, pattern):
    """Equivalente ao fnMatch do JS: glob simples (* e ?) case-insensitive."""
    escaped = _REGEX_ESCAPE.sub(lambda m: '\\' + m.group(), pattern)
    regex = '^' + escaped.replace('*', '.*').replace('?', '.') + '$'
    return re.match(regex, name, re.IGNORECASE) is not None


def should_ignore_global(name, ignore_patterns):
    for p in ignore_patterns:
        if '*' in p:
            if fn_match(name, p):
                return True
        else:
            if name == p:
                return True
    return False


def estimate_tokens(chars):
    return -(-chars // 4)  # ceil division


def fmt_size(b):
    if b < 1024:
        return f"{b} B"
    if b < 1048576:
        return f"{b/1024:.1f} KB"
    if b < 1073741824:
        return f"{b/1048576:.1f} MB"
    return f"{b/1073741824:.1f} GB"


def gi_matches(rel_path, rules, apply_gi):
    """Porta fiel do motor de .gitignore (giMatches) da versão HTML."""
    if not apply_gi:
        return False
    active = [l for l in rules if l.strip() and not l.strip().startswith('#')]
    ignored = False
    norm = rel_path.replace('\\', '/')
    for raw in active:
        neg = raw.startswith('!')
        rule = (raw[1:] if neg else raw).strip()
        if not rule:
            continue
        dir_only = rule.endswith('/')
        if dir_only:
            rule = rule[:-1]
        escaped = _REGEX_ESCAPE.sub(lambda m: '\\' + m.group(), rule)
        reg_str = (escaped.replace('**', '§')
                           .replace('*', '[^/]*')
                           .replace('?', '[^/]')
                           .replace('§', '.*'))
        has_slash = '/' in rule.rstrip('/')
        if has_slash:
            matched = re.match(f'^{reg_str}(/.*)?$', norm) is not None
        else:
            base = norm.split('/')[-1]
            matched = (re.match(f'^{reg_str}$', base) is not None or
                       re.search(f'(^|/){reg_str}(/|$)', norm) is not None)
        if matched:
            ignored = not neg
    return ignored


def build_header(src, count, filters):
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    h = '=' * 60 + '\n  COPIADOR DE CÓDIGO — Python Edition\n' + '=' * 60 + '\n'
    h += f'  Data/Hora     : {now}\n  Origem        : {src}\n  Total arquivos: {count}\n'
    if filters:
        h += f'  Filtros       : {", ".join(filters)}\n'
    h += '=' * 60 + '\n\n'
    return h


def build_tree_txt(metas, root_name):
    root = {'name': root_name, 'ch': {}, 'files': []}
    for m in metas:
        parts = m['rel_path'].split('/')
        node = root
        for p in parts[:-1]:
            node = node['ch'].setdefault(p, {'name': p, 'ch': {}, 'files': []})
        node['files'].append(m)

    def _print(node, prefix):
        out = ''
        keys = sorted(node['ch'].keys())
        items = [('d', k, node['ch'][k]) for k in keys]
        items += [('f', f['name'], None) for f in node['files']]
        for i, (t, name, child) in enumerate(items):
            last = (i == len(items) - 1)
            out += prefix + ('`-- ' if last else '|-- ') + name + '\n'
            if t == 'd':
                out += _print(child, prefix + ('  ' if last else '| '))
        return out

    return root['name'] + '\n' + _print(root, '')


def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ==================================================================
# VARREDURA DE DIRETÓRIO (rápida — poda diretórios ignorados)
# ==================================================================
def scan_directory(root_path, ignore_patterns, size_limit_kb, progress_cb, cancel_event):
    """
    Varre root_path recursivamente construindo apenas METADADOS
    (sem ler conteúdo — leitura é feita depois, sob demanda, igual
    à versão original). A poda de diretórios ignorados acontece
    ANTES de entrar neles, o que evita percorrer node_modules,
    .git, venv etc. — esse é o ganho de velocidade real em relação
    à versão de navegador.
    """
    root_path = Path(root_path)
    root_name = root_path.name or str(root_path)
    base_dir = root_path.parent
    metas = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_path):
        if cancel_event.is_set():
            break
        dirnames[:] = [d for d in dirnames if not should_ignore_global(d, ignore_patterns)]
        dirnames.sort()
        for fname in sorted(filenames):
            if cancel_event.is_set():
                break
            if should_ignore_global(fname, ignore_patterns):
                continue
            abs_path = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                continue
            if size_limit_kb and size > size_limit_kb * 1024:
                continue
            try:
                rel_path = os.path.relpath(abs_path, base_dir).replace(os.sep, '/')
            except ValueError:
                rel_path = fname
            ext = get_ext(fname)
            is_bin = ext in BINARY_EXTS
            est_lines = 0 if is_bin else max(1, round(size / 45))
            metas.append({
                'name': fname, 'rel_path': rel_path, 'ext': ext, 'size': size,
                'is_binary': is_bin, 'lines': est_lines, 'abs_path': abs_path,
                'zip_path': None, 'zip_member': None,
            })
            count += 1
            if count % 50 == 0:
                progress_cb(count)
    progress_cb(count)
    return metas, root_name


def scan_zip(zip_path, ignore_patterns, size_limit_kb, progress_cb, cancel_event):
    """Lê os metadados de um .zip direto do índice central do arquivo,
    SEM extrair nada para disco. Muito mais rápido que extrair tudo antes
    de saber quais arquivos serão realmente usados."""
    root_name = re.sub(r'\.zip$', '', os.path.basename(zip_path), flags=re.IGNORECASE) or 'zip'
    metas = []
    count = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if cancel_event.is_set():
                break
            if info.is_dir():
                continue
            clean = info.filename.lstrip('./')
            if not clean:
                continue
            parts = clean.split('/')
            fname = parts[-1]
            if any(should_ignore_global(p, ignore_patterns) for p in parts):
                continue
            size = info.file_size
            if size_limit_kb and size > size_limit_kb * 1024:
                continue
            rel_path = f'{root_name}/{clean}'
            ext = get_ext(fname)
            is_bin = ext in BINARY_EXTS
            est_lines = 0 if is_bin else max(1, round(size / 45))
            metas.append({
                'name': fname, 'rel_path': rel_path, 'ext': ext, 'size': size,
                'is_binary': is_bin, 'lines': est_lines, 'abs_path': None,
                'zip_path': zip_path, 'zip_member': info.filename,
            })
            count += 1
            if count % 50 == 0:
                progress_cb(count)
    progress_cb(count)
    return metas, root_name


def read_file_content(meta):
    """Leitura avulsa de UM arquivo (usado fora do laço principal, ex:
    detectar o .gitignore). Funciona tanto para arquivo em disco quanto
    para membro de .zip."""
    try:
        if meta.get('zip_path'):
            with zipfile.ZipFile(meta['zip_path']) as zf:
                data = zf.read(meta['zip_member'])
        else:
            with open(meta['abs_path'], 'rb') as f:
                data = f.read()
        return data.decode('utf-8', errors='replace')
    except Exception:
        return None


def read_contents_bulk(metas):
    """Lê o conteúdo de VÁRIOS arquivos de uma vez (usado na geração da
    saída). Agrupa os arquivos por .zip de origem e abre cada .zip UMA
    única vez para ler todos os membros necessários — bem mais eficiente
    do que reabrir o .zip a cada arquivo."""
    content_map = {}
    zip_groups = {}
    disk_metas = []
    for m in metas:
        if m.get('zip_path'):
            zip_groups.setdefault(m['zip_path'], []).append(m)
        else:
            disk_metas.append(m)

    for zip_path, group in zip_groups.items():
        try:
            with zipfile.ZipFile(zip_path) as zf:
                for m in group:
                    try:
                        data = zf.read(m['zip_member'])
                        content_map[m['rel_path']] = data.decode('utf-8', errors='replace')
                    except Exception:
                        content_map[m['rel_path']] = None
        except Exception:
            for m in group:
                content_map[m['rel_path']] = None

    for m in disk_metas:
        try:
            with open(m['abs_path'], 'r', encoding='utf-8', errors='replace') as f:
                content_map[m['rel_path']] = f.read()
        except OSError:
            content_map[m['rel_path']] = None

    return content_map


def center_on_parent(win, master, width, height):
    """Centraliza uma janela Toplevel sobre a janela principal (master),
    em vez de deixar o gerenciador de janelas jogá-la no canto superior
    esquerdo da tela."""
    master.update_idletasks()
    px = master.winfo_rootx()
    py = master.winfo_rooty()
    pw = master.winfo_width()
    ph = master.winfo_height()
    x = px + (pw - width) // 2
    y = py + (ph - height) // 2
    # Garante que a janela não nasça fora da tela visível.
    x = max(x, 0)
    y = max(y, 0)
    win.geometry(f"{width}x{height}+{x}+{y}")


# ==================================================================
# DIÁLOGO: PADRÕES GLOBAIS A IGNORAR
# ==================================================================
class IgnorePatternsDialog(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Padrões globais a ignorar")
        center_on_parent(self, master, 520, 520)
        self.transient(master)
        self.grab_set()
        self.vars = {}

        head = ttk.Frame(self, padding=10)
        head.pack(fill='x')
        ttk.Label(head, text="Padrões globais a ignorar", font=('', 12, 'bold')).pack(anchor='w')
        ttk.Label(head, text="Itens marcados não serão incluídos na cópia",
                  foreground='#64748b').pack(anchor='w')

        toolbar = ttk.Frame(self, padding=(10, 0))
        toolbar.pack(fill='x')
        ttk.Button(toolbar, text="Marcar tudo", command=self.mark_all).pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text="Desmarcar tudo", command=self.unmark_all).pack(side='left')
        self.count_lbl = ttk.Label(toolbar, text="")
        self.count_lbl.pack(side='right')

        body_wrap = ttk.Frame(self)
        body_wrap.pack(fill='both', expand=True, padx=10, pady=10)
        canvas = tk.Canvas(body_wrap, highlightthickness=0)
        scroll = ttk.Scrollbar(body_wrap, orient='vertical', command=canvas.yview)
        self.body = ttk.Frame(canvas)
        self.body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.body, anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        ttk.Button(self, text="Concluído", command=self.destroy).pack(pady=(0, 10))

        self._build_groups()
        self.update_count()

    def _build_groups(self):
        for widget in self.body.winfo_children():
            widget.destroy()
        active = self.app.ignore_patterns
        for g in PATTERN_GROUPS:
            frame = ttk.LabelFrame(self.body, text=g['label'], padding=8)
            frame.pack(fill='x', pady=6, padx=2)
            for pattern, desc in g['patterns']:
                var = tk.BooleanVar(value=pattern in active)
                self.vars[pattern] = var
                row = ttk.Frame(frame)
                row.pack(fill='x', pady=1)
                cb = ttk.Checkbutton(row, variable=var, command=self.on_change)
                cb.pack(side='left')
                ttk.Label(row, text=pattern, width=16, font=('Courier New', 9, 'bold')).pack(side='left')
                ttk.Label(row, text=desc, foreground='#64748b').pack(side='left')

    def on_change(self):
        selected = [p for p, v in self.vars.items() if v.get()]
        self.app.set_ignore_patterns(selected)
        self.update_count()

    def mark_all(self):
        for v in self.vars.values():
            v.set(True)
        self.on_change()

    def unmark_all(self):
        for v in self.vars.values():
            v.set(False)
        self.on_change()

    def update_count(self):
        n = sum(1 for v in self.vars.values() if v.get())
        self.count_lbl.config(text=f"{n}/{len(ALL_IGNORE_PATTERNS)} ativos")


# ==================================================================
# DIÁLOGO: SAÍDA GERADA
# ==================================================================
class OutputDialog(tk.Toplevel):
    def __init__(self, master, app, content, filename, count, chars):
        super().__init__(master)
        self.app = app
        self.content = content
        self.filename = filename
        self.title(f"📄 {filename}")
        center_on_parent(self, master, 820, 600)
        self.transient(master)

        head = ttk.Frame(self, padding=10)
        head.pack(fill='x')
        ttk.Label(head, text=f"📄 {filename}", font=('', 12, 'bold')).pack(side='left')
        tokens = estimate_tokens(chars)
        ttk.Label(
            head,
            text=f"{count} arq. | {chars:,} chars | ~{tokens:,} tokens".replace(',', '.'),
            foreground='#64748b'
        ).pack(side='right')

        body = ttk.Frame(self)
        body.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self.text = scrolledtext.ScrolledText(body, wrap='none', font=('Courier New', 9))
        self.text.pack(fill='both', expand=True)
        self.text.insert('1.0', content)
        self.text.configure(state='disabled')

        foot = ttk.Frame(self, padding=10)
        foot.pack(fill='x')
        ttk.Button(foot, text="📋 Copiar tudo", command=self.copy_all).pack(side='left', padx=(0, 6))
        ttk.Button(foot, text="⬇ Baixar .txt", command=self.download).pack(side='left', padx=(0, 6))
        ttk.Button(foot, text="Fechar", command=self.destroy).pack(side='right')

    def copy_all(self):
        self.app.copy_to_clipboard(self.content)

    def download(self):
        path = filedialog.asksaveasfilename(
            initialfile=self.filename,
            defaultextension='.txt',
            filetypes=[('Arquivo de texto', '*.txt'), ('Todos os arquivos', '*.*')],
        )
        if not path:
            return
        try:
            # newline='\n' força LF puro na saída, independente do SO,
            # evitando que o Windows converta para \r\n e quebre o
            # casamento de padrões dos restauradores.
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(self.content)
            self.app.toast('Download concluído!', 'ok')
            self.app.log(f"Download: {path}", 'ok')
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))


# ==================================================================
# APLICAÇÃO PRINCIPAL
# ==================================================================
class CodeCopierApp(_BaseTk):
    TAB_IDS = ['ext', 'files', 'search', 'explorer', 'arb', 'gi']
    TAB_LABELS = ['Extensões', 'Arquivos', 'Buscar Nome', 'Explorador', 'Avulsos', 'Gitignore']

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)

        # Tamanho inicial adaptado à tela do usuário: nunca abre maior do
        # que a tela disponível (com uma margem para a barra de tarefas e
        # bordas da janela), evitando que botões como "INICIAR CÓPIA"
        # fiquem fora da área visível em telas pequenas. Em telas grandes,
        # continua abrindo no tamanho padrão de sempre (1180x820).
        default_w, default_h = 640, 820
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(default_w, max(640, screen_w - 60))
        win_h = min(default_h, max(480, screen_h - 100))
        x = max((screen_w - win_w) // 2, 0)
        y = max((screen_h - win_h) // 2 - 20, 0)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # minsize também reduzido, para permitir redimensionar a janela
        # manualmente para baixo em telas pequenas sem travar num tamanho
        # que já não cabe.
        self.minsize(640, 400)

        # ---------------- ESTADO ----------------
        cfg = load_config()
        self.ignore_patterns = [p for p in cfg.get('ignore_patterns', ALL_IGNORE_PATTERNS)
                                 if p in ALL_IGNORE_PATTERNS] or list(ALL_IGNORE_PATTERNS)
        self.dark_mode = bool(cfg.get('dark_mode', False))

        self.all_meta = []          # [{name, rel_path, ext, size, is_binary, lines, abs_path}]
        self.all_exts = []
        self.selected_files = set()
        self.selected_exts = set()
        self.arb_files = []         # [{name, abs_path, size, is_binary}]
        self.arb_checked = set()    # índices marcados
        self.gi_file_rules = []
        self.gi_manual_rules = []
        self.gi_sel_idx = -1
        self.apply_gi = False
        self.last_output = ''
        self.active_tab = 'ext'
        self.search_results = []
        self.tree_data = None
        self.log_count = 0
        self.ext_sort = {'col': None, 'dir': 'asc'}
        self.cancel_event = threading.Event()
        self.src_root = ''
        self.src_dir_label = ''

        self.task_queue = queue.Queue()

        self._build_style()
        self._build_ui()
        self._setup_dnd()
        self._poll_queue()
        self.update_ignore_summary()
        self.log("Bem-vindo ao Copiador de Código — Python Edition.", 'info')
        self.log("Selecione uma pasta de entrada para começar.", 'info')
        self.apply_theme()
        self.update_counter()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------------------------------------------------
    # ESTILO / TEMA
    # ---------------------------------------------------------
    def _build_style(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

    def apply_theme(self):
        if self.dark_mode:
            bg, surface, surface2, text, text2, border = '#0f172a', '#1e293b', '#334155', '#e2e8f0', '#94a3b8', '#475569'
            select_bg, select_fg = '#2563eb', '#ffffff'
        else:
            bg, surface, surface2, text, text2, border = '#f1f5f9', '#ffffff', '#eef2f7', '#1e293b', '#475569', '#94a3b8'
            select_bg, select_fg = '#2563eb', '#ffffff'
        primary = '#3b82f6' if self.dark_mode else '#2563eb'

        s = self.style
        self.configure(bg=bg)

        # Paleta "retrô" pros botões ttk: cinza neutro com relevo 3D
        # (borda clara de um lado / escura do outro + afunda ao clicar),
        # igual ao visual padrão do tema clam sem cor nenhuma por cima —
        # só que recalculada pro modo escuro também, pra não "quebrar"
        # como acontece quando simplesmente não se estiliza o TButton.
        if self.dark_mode:
            btn_bg, btn_active, btn_pressed = '#334155', '#3b4a5e', '#25324a'
            btn_light, btn_dark, btn_fg = '#47566b', '#0f172a', '#e2e8f0'
            entry_border = '#475569'
        else:
            btn_bg, btn_active, btn_pressed = '#e6e6e6', '#d9d9d9', '#c2c2c2'
            btn_light, btn_dark, btn_fg = '#f5f5f5', '#a6a6a6', '#1e293b'
            entry_border = '#64748b'

        s.configure('.', background=surface, foreground=text, fieldbackground=surface2)
        s.configure('TFrame', background=surface)
        s.configure('TLabel', background=surface, foreground=text)
        s.configure('TLabelframe', background=surface, foreground=text, bordercolor=border, relief='groove')
        s.configure('TLabelframe.Label', background=surface, foreground=text2)
        s.configure('TCheckbutton', background=surface, foreground=text)

        # Campos de texto e combobox: borda bem visível, pra não se
        # confundir com o fundo (era um dos pontos das setas na imagem).
        s.configure('TEntry', fieldbackground=surface2, foreground=text,
                    bordercolor=entry_border, lightcolor=entry_border, darkcolor=entry_border,
                    borderwidth=1, relief='solid', padding=4)
        s.map('TEntry', bordercolor=[('focus', primary)])
        s.configure('TCombobox', fieldbackground=surface2, foreground=text, background=surface2,
                    bordercolor=entry_border, lightcolor=entry_border, darkcolor=entry_border,
                    arrowcolor=text2, borderwidth=1, relief='solid', padding=4)
        s.map('TCombobox',
              bordercolor=[('focus', primary)],
              fieldbackground=[('readonly', surface2)],
              arrowcolor=[('active', primary)])

        # Abas: contorno visível na aba ativa, pra parecer pasta/aba de
        # verdade em vez de um texto flutuando.
        s.configure('TNotebook', background=bg, bordercolor=border)
        s.configure('TNotebook.Tab', background=surface2, foreground=text2, padding=(12, 6),
                    bordercolor=border)
        s.map('TNotebook.Tab',
              background=[('selected', primary)],
              foreground=[('selected', '#ffffff')],
              bordercolor=[('selected', primary)])

        # Árvore/lista: cabeçalho com borda e cor de seleção nítida (azul
        # "de sistema"), em vez do cinza apagado padrão.
        s.configure('Treeview', background=surface2, fieldbackground=surface2, foreground=text,
                    bordercolor=border, borderwidth=1, relief='solid')
        s.map('Treeview', background=[('selected', select_bg)], foreground=[('selected', select_fg)])
        s.configure('Treeview.Heading', background=surface, foreground=text2,
                    bordercolor=border, relief='raised', padding=(6, 4))
        s.map('Treeview.Heading', background=[('active', surface2)])

        # Botões padrão (ttk.Button): visual retrô com relevo 3D — o
        # mesmo estilo "clam puro" da v2.1, só que recolorido pro modo
        # escuro em vez de ficar cinza-claro fixo.
        s.configure('TButton', background=btn_bg, foreground=btn_fg,
                    bordercolor=btn_dark, lightcolor=btn_light, darkcolor=btn_dark,
                    borderwidth=2, relief='raised', focuscolor=btn_bg, padding=(10, 6))
        s.map('TButton',
              background=[('pressed', btn_pressed), ('active', btn_active)],
              relief=[('pressed', 'sunken')],
              foreground=[('disabled', text2)])

        # Ok.TButton/Warn.TButton continuam existindo (não quebra nenhuma
        # chamada no código), mas agora seguem o mesmo cinza retrô — igual
        # à v2.1, onde "Tudo"/"Nenhum"/"Remover"/"Limpar" não têm cor
        # diferenciada, só o relevo 3D padrão.
        s.configure('Ok.TButton', background=btn_bg, foreground=btn_fg,
                    bordercolor=btn_dark, lightcolor=btn_light, darkcolor=btn_dark,
                    borderwidth=2, relief='raised', focuscolor=btn_bg, padding=(10, 6))
        s.map('Ok.TButton',
              background=[('pressed', btn_pressed), ('active', btn_active)],
              relief=[('pressed', 'sunken')])
        s.configure('Warn.TButton', background=btn_bg, foreground=btn_fg,
                    bordercolor=btn_dark, lightcolor=btn_light, darkcolor=btn_dark,
                    borderwidth=2, relief='raised', focuscolor=btn_bg, padding=(10, 6))
        s.map('Warn.TButton',
              background=[('pressed', btn_pressed), ('active', btn_active)],
              relief=[('pressed', 'sunken')])

        s.configure('Header.TFrame', background=primary)
        s.configure('Header.TLabel', background=primary, foreground='#ffffff')

        self.body_bg = bg
        self.surface = surface
        self.surface2 = surface2
        self.text_color = text
        self.text2_color = text2
        self.primary_color = primary

        if hasattr(self, 'header_frame'):
            self.header_frame.configure(style='Header.TFrame')
            self.theme_btn.configure(text='☀️' if self.dark_mode else '🌙')
        if hasattr(self, 'log_text'):
            self.log_text.configure(bg='#0f172a', fg='#94a3b8', insertbackground='#94a3b8')
        if getattr(self, 'src_drop_zone', None) is not None:
            self.src_drop_zone.configure(bg=surface2, fg=text2)
        if getattr(self, 'arb_drop_zone', None) is not None:
            self.arb_drop_zone.configure(bg=surface2, fg=text2)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        cfg = load_config()
        cfg['dark_mode'] = self.dark_mode
        save_config(cfg)
        self.log(f"Tema alterado para {'escuro' if self.dark_mode else 'claro'}.", 'info')

    def on_close(self):
        self.cancel_event.set()
        self.destroy()

    # ---------------------------------------------------------
    # CONSTRUÇÃO DA UI
    # ---------------------------------------------------------
    def _build_ui(self):
        outer = ttk.Frame(self, padding=4)
        outer.pack(fill='both', expand=True)

        self._build_header(outer)
        self._build_config(outer)
        self._build_tabs(outer)      # notebook: fill='both', expand=True
        self._build_counter(outer)
        self._build_progress(outer)
        self._build_actions(outer)
        self._build_log(outer)
        self._build_statusbar(outer)

    def _build_header(self, parent):
        self.header_frame = ttk.Frame(parent, style='Header.TFrame', padding=(8, 4))
        self.header_frame.pack(fill='x', pady=(0, 2))
        # retornar para posicionamento no grid principal
        ttk.Label(self.header_frame, text="📁 Copiador de Código — Python Edition",
                  style='Header.TLabel', font=('', 12, 'bold')).pack(side='left')
        right = ttk.Frame(self.header_frame, style='Header.TFrame')
        right.pack(side='right')
        self.theme_btn = tk.Button(right, text='🌙', command=self.toggle_theme,
                                    relief='flat', bg='#3b6fd6', fg='#ffffff', bd=0,
                                    activebackground='#5a86e0', padx=8)
        self.theme_btn.pack(side='left', padx=(0, 10))
        self.file_count_badge = ttk.Label(right, text="0 arquivos", style='Header.TLabel')
        self.file_count_badge.pack(side='left', padx=(0, 10))
        self.header_status = ttk.Label(right, text="Pronto", style='Header.TLabel')
        self.header_status.pack(side='left')
        return self.header_frame

    def _build_config(self, parent):
        cfgf = ttk.LabelFrame(parent, text="⚙ Configurações", padding=4)
        cfgf.pack(fill='x', pady=(0, 2))

        # Zona de arrastar-e-soltar: arraste uma pasta ou um .zip aqui.
        if DND_AVAILABLE:
            self.src_drop_zone = tk.Label(
                cfgf, text="⬇  Arraste uma pasta ou um arquivo .zip aqui  ⬇",
                relief='ridge', bd=1, padx=8, pady=6, foreground='#64748b')
            self.src_drop_zone.pack(fill='x', pady=(2, 4))
        else:
            self.src_drop_zone = None
            ttk.Label(cfgf, text="💡 Instale 'tkinterdnd2' (pip install tkinterdnd2) para "
                                  "habilitar arrastar-e-soltar. Os botões acima funcionam normalmente.",
                      foreground='#d97706').pack(fill='x', pady=(2, 4))

        row1 = ttk.Frame(cfgf)
        row1.pack(fill='x', pady=1)
        ttk.Label(row1, text="📂 Entrada:", width=12).pack(side='left')
        self.src_input_var = tk.StringVar()
        self.src_input_entry = ttk.Entry(row1, textvariable=self.src_input_var, state='readonly')
        self.src_input_entry.pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(row1, text="Pasta…", command=self.pick_source_dir).pack(side='left', padx=2)
        ttk.Button(row1, text="ZIP…", command=self.pick_zip).pack(side='left', padx=2)

        row2 = ttk.Frame(cfgf)
        row2.pack(fill='x', pady=1)
        ttk.Label(row2, text="💾 Saída:", width=12).pack(side='left')
        self.out_name_var = tk.StringVar(value="codigo_completo.txt")
        ttk.Entry(row2, textvariable=self.out_name_var).pack(side='left', fill='x', expand=True, padx=6)

        row3 = ttk.Frame(cfgf)
        row3.pack(fill='x', pady=1)
        ttk.Label(row3, text="Ordem:").pack(side='left')
        self.sort_var = tk.StringVar(value='Natural')
        sort_combo = ttk.Combobox(row3, textvariable=self.sort_var, state='readonly',
                                   values=['Natural', 'Alfabética'], width=12)
        sort_combo.pack(side='left', padx=(4, 14))
        sort_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_all_lists())

        ttk.Button(row3, text="Padrões globais…", command=self.open_ignore_dialog).pack(side='left')
        self.ignore_summary_lbl = ttk.Label(row3, text="", foreground='#64748b')
        self.ignore_summary_lbl.pack(side='left', padx=(8, 14))

        self.size_filter_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Ignorar >", variable=self.size_filter_var).pack(side='left')
        self.max_size_var = tk.StringVar(value="500")
        ttk.Entry(row3, textvariable=self.max_size_var, width=6).pack(side='left', padx=4)
        ttk.Label(row3, text="KB").pack(side='left')

        self.config_frame = cfgf
        return self.config_frame

    def _build_tabs(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True, pady=(0, 2))
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        self.tab_frames = {}
        for tab_id, label in zip(self.TAB_IDS, self.TAB_LABELS):
            frame = ttk.Frame(self.notebook, padding=8)
            self.notebook.add(frame, text=label)
            self.tab_frames[tab_id] = frame

        self._build_tab_ext(self.tab_frames['ext'])
        self._build_tab_files(self.tab_frames['files'])
        self._build_tab_search(self.tab_frames['search'])
        self._build_tab_explorer(self.tab_frames['explorer'])
        self._build_tab_arb(self.tab_frames['arb'])
        self._build_tab_gi(self.tab_frames['gi'])
        return self.notebook

    def _on_tab_changed(self, event):
        idx = self.notebook.index(self.notebook.select())
        self.active_tab = self.TAB_IDS[idx]
        if self.active_tab == 'explorer':
            self.populate_explorer()

    # ---------------------------------------------------------
    # ABA: EXTENSÕES
    # ---------------------------------------------------------
    def _build_tab_ext(self, parent):
        search_row = ttk.Frame(parent)
        search_row.pack(fill='x', pady=(0, 4))
        ttk.Label(search_row, text="🔍").pack(side='left')
        self.ext_search_var = tk.StringVar()
        self.ext_search_var.trace_add('write', lambda *a: self.render_ext_list())
        ttk.Entry(search_row, textvariable=self.ext_search_var).pack(side='left', fill='x', expand=True, padx=6)

        cols = ('sel', 'ext', 'size', 'count')
        self.ext_tree = ttk.Treeview(parent, columns=cols, show='headings', selectmode='none')
        self.ext_tree.heading('sel', text='')
        self.ext_tree.heading('ext', text='Extensão', command=lambda: self.sort_ext_by('ext'))
        self.ext_tree.heading('size', text='Tamanho', command=lambda: self.sort_ext_by('size'))
        self.ext_tree.heading('count', text='Arquivos', command=lambda: self.sort_ext_by('count'))
        self.ext_tree.column('sel', width=32, anchor='center', stretch=False)
        self.ext_tree.column('ext', width=220, anchor='w')
        self.ext_tree.column('size', width=110, anchor='e')
        self.ext_tree.column('count', width=90, anchor='e')
        self.ext_tree.pack(fill='both', expand=True)
        self.ext_tree.bind('<Button-1>', self._on_ext_click)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill='x', pady=(4, 0))
        ttk.Button(btn_row, text="✅ Tudo", command=self.sel_all_ext, style='Ok.TButton').pack(side='left', padx=(0, 4))
        ttk.Button(btn_row, text="⬜ Nenhum", command=self.desel_all_ext).pack(side='left')
        self.ext_counter_lbl = ttk.Label(btn_row, text="")
        self.ext_counter_lbl.pack(side='right')

    def sort_ext_by(self, col):
        if self.ext_sort['col'] == col:
            self.ext_sort['dir'] = 'desc' if self.ext_sort['dir'] == 'asc' else 'asc'
        else:
            self.ext_sort['col'] = col
            self.ext_sort['dir'] = 'asc'
        self.render_ext_list()

    def render_ext_list(self):
        natural = self.sort_var.get() == 'Natural'
        q = self.ext_search_var.get().lower()
        exts = list(self.all_exts)
        col, direc = self.ext_sort['col'], self.ext_sort['dir']
        if col:
            def size_of(e):
                return sum(m['size'] for m in self.all_meta if m['ext'] == e)

            def count_of(e):
                return sum(1 for m in self.all_meta if m['ext'] == e)

            if col == 'ext':
                exts.sort(key=lambda e: e.lower())
            elif col == 'size':
                exts.sort(key=size_of)
            elif col == 'count':
                exts.sort(key=count_of)
            if direc == 'desc':
                exts.reverse()
        else:
            exts = sort_list(exts, natural)

        filtered = [e for e in exts if q in e.lower()]
        self.ext_tree.delete(*self.ext_tree.get_children())
        for ext in filtered:
            group = [m for m in self.all_meta if m['ext'] == ext]
            count = len(group)
            total_size = sum(m['size'] for m in group)
            sel = ext in self.selected_exts
            label = ext + (' (binário)' if ext in BINARY_EXTS else '')
            self.ext_tree.insert('', 'end', iid=f'ext::{ext}',
                                  values=(CHECK_ON if sel else CHECK_OFF, label,
                                          fmt_size(total_size), f'{count} arq.'))
        self.ext_counter_lbl.config(text=f"{len(self.selected_exts)} sel.")

    def _on_ext_click(self, event):
        iid = self.ext_tree.identify_row(event.y)
        if not iid:
            return
        ext = iid.split('::', 1)[1]
        if ext in self.selected_exts:
            self.selected_exts.discard(ext)
        else:
            self.selected_exts.add(ext)
        vals = list(self.ext_tree.item(iid, 'values'))
        vals[0] = CHECK_ON if ext in self.selected_exts else CHECK_OFF
        self.ext_tree.item(iid, values=vals)
        self.ext_counter_lbl.config(text=f"{len(self.selected_exts)} sel.")

    def sel_all_ext(self):
        self.selected_exts.update(self.all_exts)
        self.render_ext_list()

    def desel_all_ext(self):
        self.selected_exts.clear()
        self.render_ext_list()

    # ---------------------------------------------------------
    # ABA: ARQUIVOS
    # ---------------------------------------------------------
    def _build_tab_files(self, parent):
        search_row = ttk.Frame(parent)
        search_row.pack(fill='x', pady=(0, 4))
        ttk.Label(search_row, text="🔍").pack(side='left')
        self.file_search_var = tk.StringVar()
        self.file_search_var.trace_add('write', lambda *a: self.render_file_list())
        ttk.Entry(search_row, textvariable=self.file_search_var).pack(side='left', fill='x', expand=True, padx=6)

        cols = ('sel', 'name', 'dir', 'size')
        self.file_tree = ttk.Treeview(parent, columns=cols, show='headings', selectmode='none')
        self.file_tree.heading('sel', text='')
        self.file_tree.heading('name', text='Arquivo')
        self.file_tree.heading('dir', text='Pasta')
        self.file_tree.heading('size', text='Tamanho')
        self.file_tree.column('sel', width=32, anchor='center', stretch=False)
        self.file_tree.column('name', width=260, anchor='w')
        self.file_tree.column('dir', width=280, anchor='w')
        self.file_tree.column('size', width=90, anchor='e')
        self.file_tree.pack(fill='both', expand=True)
        self.file_tree.bind('<Button-1>', lambda e: self._on_checklist_click(e, self.file_tree, self.selected_files, self.update_counter))

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill='x', pady=(4, 0))
        ttk.Button(btn_row, text="✅ Tudo", command=self.sel_all_files, style='Ok.TButton').pack(side='left', padx=(0, 4))
        ttk.Button(btn_row, text="⬜ Nenhum", command=self.desel_all_files).pack(side='left')
        self.file_counter_lbl = ttk.Label(btn_row, text="")
        self.file_counter_lbl.pack(side='right')

    def render_file_list(self):
        q = self.file_search_var.get().lower()
        filtered = [m for m in self.all_meta if q in m['rel_path'].lower()] if q else self.all_meta
        self.file_tree.delete(*self.file_tree.get_children())
        for m in filtered:
            sel = m['rel_path'] in self.selected_files
            parts = m['rel_path'].split('/')
            directory = '/'.join(parts[:-1])
            name = m['name'] + (' (binário)' if m['is_binary'] else '')
            self.file_tree.insert('', 'end', iid=f"f::{m['rel_path']}",
                                   values=(CHECK_ON if sel else CHECK_OFF, name, directory,
                                           f"{m['size']/1024:.0f}KB"))
        self.file_counter_lbl.config(text=f"{len(filtered)} vis. / {len(self.selected_files)} sel.")

    def _on_checklist_click(self, event, tree, sel_set, after_cb=None):
        iid = tree.identify_row(event.y)
        if not iid:
            return
        key = iid.split('::', 1)[1]
        if key in sel_set:
            sel_set.discard(key)
        else:
            sel_set.add(key)
        vals = list(tree.item(iid, 'values'))
        vals[0] = CHECK_ON if key in sel_set else CHECK_OFF
        tree.item(iid, values=vals)
        if after_cb:
            after_cb()

    def sel_all_files(self):
        self.selected_files.update(m['rel_path'] for m in self.all_meta)
        self.render_file_list()
        self.update_counter()

    def desel_all_files(self):
        for m in self.all_meta:
            self.selected_files.discard(m['rel_path'])
        self.render_file_list()
        self.update_counter()

    # ---------------------------------------------------------
    # ABA: BUSCAR NOME
    # ---------------------------------------------------------
    def _build_tab_search(self, parent):
        ttk.Label(parent, text="Cole nomes, caminhos ou saída de git status:",
                  foreground='#64748b').pack(anchor='w', pady=(0, 4))
        self.txt_search = tk.Text(parent, height=2)
        self.txt_search.pack(fill='x', pady=(0, 4))

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill='x', pady=(0, 4))
        ttk.Button(btn_row, text="🔍 Buscar", command=self.do_search).pack(side='left', padx=(0, 4))
        ttk.Button(btn_row, text="✅ Tudo", command=self.sel_all_search, style='Ok.TButton').pack(side='left', padx=(0, 4))
        ttk.Button(btn_row, text="⬜ Nenhum", command=self.desel_all_search).pack(side='left')

        cols = ('sel', 'path')
        self.search_tree = ttk.Treeview(parent, columns=cols, show='headings', selectmode='none')
        self.search_tree.heading('sel', text='')
        self.search_tree.heading('path', text='Caminho')
        self.search_tree.column('sel', width=32, anchor='center', stretch=False)
        self.search_tree.column('path', width=600, anchor='w')
        self.search_tree.pack(fill='both', expand=True)
        self.search_tree.bind('<Button-1>', lambda e: self._on_checklist_click(e, self.search_tree, self.selected_files, self.update_counter))

    def do_search(self):
        raw = self.txt_search.get('1.0', 'end').strip()
        if not raw:
            self.search_results = [m['rel_path'] for m in self.all_meta]
            self.render_search_list()
            return
        terms = []
        for t in re.split(r'[\s,]+', raw):
            if not t:
                continue
            t = re.sub(r'^(modified:|new file:|deleted:|renamed:)\s*', '', t, flags=re.IGNORECASE).strip()
            if '->' in t:
                t = t.split('->')[-1].strip()
            if t:
                terms.append(t)
        found = set()
        for m in self.all_meta:
            rp = m['rel_path'].replace('\\', '/')
            no_ext = re.sub(r'\.[^.]+$', '', m['name'])
            for term in terms:
                tl = term.lower().replace('\\', '/')
                has_slash = '/' in tl
                if has_slash:
                    if rp.lower().endswith(tl):
                        found.add(m['rel_path'])
                        break
                else:
                    if m['name'].lower() == tl or no_ext.lower() == tl:
                        found.add(m['rel_path'])
                        break
        self.search_results = list(found)
        self.render_search_list()
        if not found:
            self.toast('Nenhum arquivo encontrado.', 'warn')
        else:
            self.log(f"✓ {len(found)} arquivo(s) encontrado(s).", 'ok')

    def render_search_list(self):
        self.search_tree.delete(*self.search_tree.get_children())
        for rp in self.search_results:
            sel = rp in self.selected_files
            self.search_tree.insert('', 'end', iid=f"s::{rp}", values=(CHECK_ON if sel else CHECK_OFF, rp))

    def sel_all_search(self):
        self.selected_files.update(self.search_results)
        self.render_search_list()
        self.update_counter()

    def desel_all_search(self):
        for rp in self.search_results:
            self.selected_files.discard(rp)
        self.render_search_list()
        self.update_counter()

    # ---------------------------------------------------------
    # ABA: EXPLORADOR (árvore)
    # ---------------------------------------------------------
    def _build_tab_explorer(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill='x', pady=(0, 4))
        ttk.Label(top, text="Toque/clique para marcar arquivos e pastas:",
                  foreground='#64748b').pack(side='left')
        ttk.Button(top, text="Expandir tudo", command=self.expand_all_tree).pack(side='right', padx=(4, 0))
        ttk.Button(top, text="Recolher tudo", command=self.collapse_all_tree).pack(side='right')

        self.explorer_tree = ttk.Treeview(parent, show='tree', selectmode='none')
        self.explorer_tree.pack(fill='both', expand=True)
        self.explorer_tree.bind('<Button-1>', self._on_explorer_click)

    def _build_tree_data(self):
        root = {'name': '', 'ch': {}, 'files': []}
        for m in self.all_meta:
            parts = m['rel_path'].split('/')
            node = root
            for p in parts[:-1]:
                node = node['ch'].setdefault(p, {'name': p, 'ch': {}, 'files': []})
            node['files'].append(m)
        self.tree_data = root

    def _all_files_in_node(self, node):
        files = list(node['files'])
        for c in node['ch'].values():
            files.extend(self._all_files_in_node(c))
        return files

    def _find_node(self, dir_path):
        node = self.tree_data
        if not dir_path:
            return node
        for part in dir_path.strip('/').split('/'):
            if part not in node['ch']:
                return node
            node = node['ch'][part]
        return node

    def _get_open_dirs(self):
        open_dirs = set()

        def walk(iid):
            if iid.startswith('D::') and self.explorer_tree.item(iid, 'open'):
                open_dirs.add(iid)
            for c in self.explorer_tree.get_children(iid):
                walk(c)

        for c in self.explorer_tree.get_children(''):
            walk(c)
        return open_dirs

    def populate_explorer(self):
        if self.tree_data is None:
            self._build_tree_data()
        open_dirs = self._get_open_dirs() if self.explorer_tree.get_children('') else set()
        self.explorer_tree.delete(*self.explorer_tree.get_children())
        if not self.all_meta:
            self.explorer_tree.insert('', 'end', iid='empty', text='Selecione uma pasta de entrada.')
            return
        self._render_tree_node(self.tree_data, '', '')
        for iid in open_dirs:
            if self.explorer_tree.exists(iid):
                self.explorer_tree.item(iid, open=True)

    def _render_tree_node(self, node, parent_iid, path_prefix):
        natural = self.sort_var.get() == 'Natural'
        dirs = sorted(node['ch'].keys(), key=nat_key if natural else str.lower)
        for dk in dirs:
            if should_ignore_global(dk, self.ignore_patterns):
                continue
            child = node['ch'][dk]
            full_path = f'{path_prefix}{dk}/'
            iid = 'D::' + full_path
            all_f = self._all_files_in_node(child)
            sel_c = sum(1 for m in all_f if m['rel_path'] in self.selected_files)
            icon = CHECK_OFF if sel_c == 0 else (CHECK_ON if sel_c == len(all_f) else CHECK_PARTIAL)
            self.explorer_tree.insert(parent_iid, 'end', iid=iid, text=f'{icon} 📁 {dk}', open=False)
            self._render_tree_node(child, iid, full_path)

        files = sort_list_by(node['files'], lambda m: m['name'], natural)
        for m in files:
            if should_ignore_global(m['name'], self.ignore_patterns):
                continue
            sel = m['rel_path'] in self.selected_files
            icon = CHECK_ON if sel else CHECK_OFF
            label = f"{icon} {m['name']}" + (' (binário)' if m['is_binary'] else '') + f"  —  {m['size']/1024:.0f}KB"
            iid = 'F::' + m['rel_path']
            self.explorer_tree.insert(parent_iid, 'end', iid=iid, text=label)

    def _on_explorer_click(self, event):
        iid = self.explorer_tree.identify_row(event.y)
        if not iid or iid == 'empty':
            return
        # Clique na seta de abrir/fechar não deve alternar seleção.
        elem = self.explorer_tree.identify_element(event.x, event.y)
        if 'indicator' in elem:
            return
        if iid.startswith('F::'):
            rp = iid[3:]
            if rp in self.selected_files:
                self.selected_files.discard(rp)
            else:
                self.selected_files.add(rp)
        elif iid.startswith('D::'):
            dir_path = iid[3:]
            node = self._find_node(dir_path)
            all_f = self._all_files_in_node(node)
            sel_c = sum(1 for m in all_f if m['rel_path'] in self.selected_files)
            all_selected = len(all_f) > 0 and sel_c == len(all_f)
            for m in all_f:
                if all_selected:
                    self.selected_files.discard(m['rel_path'])
                else:
                    self.selected_files.add(m['rel_path'])
            self.log(f"Pasta {'desmarcada' if all_selected else 'marcada'}: {dir_path.rstrip('/')}")
        self.populate_explorer()
        self.update_counter()

    def expand_all_tree(self):
        def walk(iid):
            self.explorer_tree.item(iid, open=True)
            for c in self.explorer_tree.get_children(iid):
                walk(c)
        for c in self.explorer_tree.get_children(''):
            walk(c)

    def collapse_all_tree(self):
        def walk(iid):
            self.explorer_tree.item(iid, open=False)
            for c in self.explorer_tree.get_children(iid):
                walk(c)
        for c in self.explorer_tree.get_children(''):
            walk(c)

    # ---------------------------------------------------------
    # ABA: AVULSOS
    # ---------------------------------------------------------
    def _build_tab_arb(self, parent):
        ttk.Label(parent, text="Adicione arquivos avulsos de qualquer local:",
                  foreground='#64748b').pack(anchor='w', pady=(0, 4))

        if DND_AVAILABLE:
            self.arb_drop_zone = tk.Label(
                parent, text="⬆  Arraste arquivos ou pastas aqui  ⬆",
                relief='ridge', bd=1, padx=8, pady=10, foreground='#64748b')
            self.arb_drop_zone.pack(fill='x', pady=(0, 6))
        else:
            self.arb_drop_zone = None
            ttk.Label(parent, text="💡 Instale 'tkinterdnd2' (pip install tkinterdnd2) para arrastar "
                                    "arquivos até aqui. O botão \"Adicionar…\" funciona normalmente.",
                      foreground='#d97706').pack(fill='x', pady=(0, 6))

        cols = ('sel', 'name', 'size')
        self.arb_tree = ttk.Treeview(parent, columns=cols, show='headings', selectmode='none')
        self.arb_tree.heading('sel', text='')
        self.arb_tree.heading('name', text='Arquivo')
        self.arb_tree.heading('size', text='Tamanho')
        self.arb_tree.column('sel', width=32, anchor='center', stretch=False)
        self.arb_tree.column('name', width=520, anchor='w')
        self.arb_tree.column('size', width=100, anchor='e')
        self.arb_tree.pack(fill='both', expand=True)
        self.arb_tree.bind('<Button-1>', self._on_arb_click)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill='x', pady=(4, 0))
        ttk.Button(btn_row, text="➕ Adicionar…", command=self.add_arb_files).pack(side='left', padx=(0, 4))
        ttk.Button(btn_row, text="➖ Remover marcados", command=self.rem_checked_arb, style='Warn.TButton').pack(side='left', padx=(0, 4))
        ttk.Button(btn_row, text="🗑 Limpar", command=self.clear_arb, style='Warn.TButton').pack(side='left')

    def add_arb_files(self):
        paths = filedialog.askopenfilenames(title="Selecione arquivos avulsos")
        if not paths:
            return
        added = 0
        for p in paths:
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            name = os.path.basename(p)
            if any(a['name'] == name and a['size'] == size for a in self.arb_files):
                continue
            self.arb_files.append({'name': name, 'abs_path': p, 'size': size, 'is_binary': is_bin_ext(name)})
            added += 1
        self.render_arb_list()
        self.log(f"{added} arquivo(s) avulso(s) adicionado(s).", 'ok')

    def render_arb_list(self):
        self.arb_tree.delete(*self.arb_tree.get_children())
        for i, f in enumerate(self.arb_files):
            if i not in self.arb_checked:
                self.arb_checked.add(i)  # por padrão, vem marcado (igual à versão original)
            sel = i in self.arb_checked
            name = f['name'] + (' (binário)' if f['is_binary'] else '')
            self.arb_tree.insert('', 'end', iid=f'arb::{i}',
                                  values=(CHECK_ON if sel else CHECK_OFF, name, f"{f['size']/1024:.1f}KB"))

    def _on_arb_click(self, event):
        iid = self.arb_tree.identify_row(event.y)
        if not iid:
            return
        idx = int(iid.split('::', 1)[1])
        if idx in self.arb_checked:
            self.arb_checked.discard(idx)
        else:
            self.arb_checked.add(idx)
        vals = list(self.arb_tree.item(iid, 'values'))
        vals[0] = CHECK_ON if idx in self.arb_checked else CHECK_OFF
        self.arb_tree.item(iid, values=vals)

    def rem_checked_arb(self):
        idxs = sorted(self.arb_checked, reverse=True)
        for i in idxs:
            if 0 <= i < len(self.arb_files):
                del self.arb_files[i]
        self.arb_checked.clear()
        self.render_arb_list()
        self.log(f"{len(idxs)} removido(s).", 'ok')

    def clear_arb(self):
        self.arb_files = []
        self.arb_checked.clear()
        self.render_arb_list()
        self.log('Lista avulsa limpa.', 'ok')

    # ---------------------------------------------------------
    # ABA: GITIGNORE
    # ---------------------------------------------------------
    def _build_tab_gi(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill='x', pady=(0, 6))
        self.gi_cb_var = tk.BooleanVar(value=False)
        self.gi_checkbutton = ttk.Checkbutton(top, text="Aplicar regras .gitignore",
                                               variable=self.gi_cb_var, command=self.toggle_gi,
                                               state='disabled')
        self.gi_checkbutton.pack(side='left')
        self.gi_status_lbl = ttk.Label(top, text="⚠ Nenhum diretório selecionado.", foreground='#64748b')
        self.gi_status_lbl.pack(side='left', padx=10)

        split = ttk.Frame(parent)
        split.pack(fill='both', expand=True)

        left = ttk.Frame(split)
        left.pack(side='left', fill='both', expand=True, padx=(0, 6))
        ttk.Label(left, text="Regras:", font=('', 9, 'bold')).pack(anchor='w')
        self.gi_rules_list = tk.Listbox(left, exportselection=False)
        self.gi_rules_list.pack(fill='both', expand=True, pady=(2, 4))
        self.gi_rules_list.bind('<<ListboxSelect>>', self._on_gi_rule_select)
        add_row = ttk.Frame(left)
        add_row.pack(fill='x')
        self.gi_input_var = tk.StringVar()
        gi_entry = ttk.Entry(add_row, textvariable=self.gi_input_var)
        gi_entry.pack(side='left', fill='x', expand=True)
        gi_entry.bind('<Return>', lambda e: self.add_gi_rule())
        ttk.Button(add_row, text="+", width=3, command=self.add_gi_rule, style='Ok.TButton').pack(side='left', padx=2)
        ttk.Button(add_row, text="−", width=3, command=self.rem_gi_rule, style='Warn.TButton').pack(side='left')

        right = ttk.Frame(split)
        right.pack(side='left', fill='both', expand=True)
        ttk.Label(right, text="Preview:", font=('', 9, 'bold')).pack(anchor='w')
        self.gi_preview = tk.Listbox(right)
        self.gi_preview.pack(fill='both', expand=True, pady=(2, 4))
        ttk.Button(right, text="🔄 Atualizar", command=self.refresh_gi_preview).pack(anchor='w')

    def toggle_gi(self):
        self.apply_gi = self.gi_cb_var.get()
        self.log(f"Gitignore {'ativado' if self.apply_gi else 'desativado'}.", 'info')

    def render_gi_rules(self):
        self.gi_rules_list.delete(0, 'end')
        all_rules = list(self.gi_file_rules) + [f"[manual] {r}" for r in self.gi_manual_rules]
        for r in all_rules:
            self.gi_rules_list.insert('end', r)

    def _on_gi_rule_select(self, event):
        sel = self.gi_rules_list.curselection()
        self.gi_sel_idx = sel[0] if sel else -1

    def add_gi_rule(self):
        v = self.gi_input_var.get().strip()
        if not v or v in self.gi_manual_rules:
            self.toast('Regra já existe ou vazia.', 'warn')
            return
        self.gi_manual_rules.append(v)
        self.gi_input_var.set('')
        self.render_gi_rules()
        self.log(f"Regra adicionada: {v}", 'ok')
        self.refresh_gi_preview()

    def rem_gi_rule(self):
        if self.gi_sel_idx < 0:
            return
        fl = len(self.gi_file_rules)
        if self.gi_sel_idx < fl:
            self.toast('Apenas regras manuais podem ser removidas.', 'warn')
            return
        r = self.gi_manual_rules.pop(self.gi_sel_idx - fl)
        self.gi_sel_idx = -1
        self.render_gi_rules()
        self.log(f"Regra removida: {r}", 'ok')
        self.refresh_gi_preview()

    def refresh_gi_preview(self):
        self.gi_preview.delete(0, 'end')
        if not self.all_meta:
            self.toast('Carregue os arquivos primeiro.', 'warn')
            return
        rules = self.gi_file_rules + self.gi_manual_rules
        preview = self.all_meta[:400]
        for m in preview:
            ign = gi_matches(m['rel_path'], rules, True)
            mark = '🚫' if ign else '✅'
            label = m['rel_path'] + (' (binário)' if m['is_binary'] else '')
            self.gi_preview.insert('end', f'{mark} {label}')
        self.log(f"Preview: {len(preview)} item(s).", 'ok')

    # ---------------------------------------------------------
    # CONTADOR / PROGRESSO / AÇÕES / LOG / STATUS
    # ---------------------------------------------------------
    def _build_counter(self, parent):
        bar = ttk.Frame(parent, padding=(4, 2))
        bar.pack(fill='x')
        self.counter_frame = bar
        self.counter_text_lbl = ttk.Label(bar, text="0 arquivo(s) selecionado(s) | ~0 linhas",
                                           foreground='#16a34a', font=('', 9, 'bold'))
        self.counter_text_lbl.pack(side='left')
        self.token_estimate_lbl = ttk.Label(bar, text="~0 tokens estimados", foreground='#16a34a')
        self.token_estimate_lbl.pack(side='right')
        return bar

    def _build_progress(self, parent):
        self.progress_wrap = ttk.Frame(parent)
        info = ttk.Frame(self.progress_wrap)
        info.pack(fill='x')
        self.prog_label_lbl = ttk.Label(info, text="Processando…")
        self.prog_label_lbl.pack(side='left')
        self.prog_pct_lbl = ttk.Label(info, text="0%")
        self.prog_pct_lbl.pack(side='right')
        self.progressbar = ttk.Progressbar(self.progress_wrap, mode='determinate')
        self.progressbar.pack(fill='x', pady=(2, 4))
        return self.progress_wrap

    def _build_actions(self, parent):
        row = ttk.Frame(parent, padding=(0, 2))
        row.pack(fill='x')
        self.actions_frame = row
        self.btn_start = tk.Button(row, text="▶ INICIAR CÓPIA", command=self.start_copy,
                                    bg='#dcfce7', fg='#15803d', relief='flat', font=('', 10, 'bold'),
                                    activebackground='#bbf7d0', padx=10, pady=6)
        self.btn_start.pack(side='left', fill='x', expand=True, padx=(0, 4))
        self.btn_clear = tk.Button(row, text="🗑 Limpar", command=self.clear_all,
                                    bg='#fef3c7', fg='#b45309', relief='flat', padx=10, pady=6)
        self.btn_clear.pack(side='left', padx=4)
        self.btn_clip = tk.Button(row, text="📋 Clipboard", command=self.clipboard_copy_last,
                                   bg='#dbeafe', fg='#1d4ed8', relief='flat', padx=10, pady=6)
        self.btn_clip.pack(side='left', padx=(4, 0))
        return row

    def _build_log(self, parent):
        self.log_frame = ttk.LabelFrame(parent, text="📋 Log")
        self.log_frame.pack(fill='x', pady=(0, 1))
        head = ttk.Frame(self.log_frame)
        head.pack(fill='x')
        self.log_badge_lbl = ttk.Label(head, text="0", background='#2563eb', foreground='white',
                                        padding=(6, 0))
        self.log_badge_lbl.pack(side='left', padx=(4, 4), pady=2)
        ttk.Button(head, text="limpar", command=self.clear_log).pack(side='right', padx=2)
        self.log_visible = tk.BooleanVar(value=True)
        ttk.Checkbutton(head, text="mostrar", variable=self.log_visible,
                         command=self._toggle_log_visibility).pack(side='right', padx=2)

        self.log_text = tk.Text(self.log_frame, height=2, bg='#0f172a', fg='#94a3b8',
                                 font=('Courier New', 9), state='disabled')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_configure('ok', foreground='#4ade80')
        self.log_text.tag_configure('warn', foreground='#fbbf24')
        self.log_text.tag_configure('err', foreground='#f87171')
        self.log_text.tag_configure('info', foreground='#60a5fa')
        return self.log_frame

    def _toggle_log_visibility(self):
        if self.log_visible.get():
            self.log_frame.pack(fill='x', pady=(0, 1), before=self.statusbar_frame)
        else:
            self.log_frame.pack_forget()

    def _build_statusbar(self, parent):
        self.statusbar_frame = ttk.Frame(parent, padding=(2, 1))
        self.statusbar_frame.pack(fill='x')
        self.st_left_lbl = ttk.Label(self.statusbar_frame, text="Pronto", foreground='#64748b')
        self.st_left_lbl.pack(side='left')
        self.st_right_lbl = ttk.Label(self.statusbar_frame, text="v3.0 — Python Edition", foreground='#64748b')
        self.st_right_lbl.pack(side='right')
        return self.statusbar_frame

    # ---------------------------------------------------------
    # LOG / TOAST / STATUS
    # ---------------------------------------------------------
    def log(self, msg, kind=''):
        self.log_count += 1
        self.log_badge_lbl.config(text=str(self.log_count) if self.log_count <= 99 else '99+')
        self.log_text.configure(state='normal')
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert('end', f'[{ts}] {msg}\n', kind if kind else ())
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
        self.log_count = 0
        self.log_badge_lbl.config(text='0')

    def toast(self, msg, kind='ok'):
        colors = {'ok': '#16a34a', 'warn': '#d97706', 'err': '#dc2626'}
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        frame = tk.Frame(win, bg='#1e293b', padx=14, pady=8,
                          highlightbackground=colors.get(kind, '#16a34a'), highlightthickness=0)
        frame.pack()
        tk.Frame(frame, bg=colors.get(kind, '#16a34a'), width=3).pack(side='left', fill='y')
        tk.Label(frame, text=msg, bg='#1e293b', fg='white', font=('', 9)).pack(side='left', padx=(8, 0))
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() - win.winfo_reqwidth() - 24
        y = self.winfo_y() + self.winfo_height() - win.winfo_reqheight() - 40
        win.geometry(f'+{max(x,0)}+{max(y,0)}')
        win.after(2600, win.destroy)

    def set_status(self, left, right=None):
        self.st_left_lbl.config(text=left)
        self.header_status.config(text=left)
        if right:
            self.st_right_lbl.config(text=right)

    def set_progress(self, val, maximum=100, label=''):
        if val is None:
            self.progress_wrap.pack_forget()
            self.progressbar.stop()
            return
        if not self.progress_wrap.winfo_ismapped():
            self.progress_wrap.pack(fill='x', pady=(0, 2), before=self.actions_frame)
        if val == 'pulse':
            self.progressbar.configure(mode='indeterminate')
            self.progressbar.start(12)
            self.prog_label_lbl.config(text=label or 'Processando…')
            self.prog_pct_lbl.config(text='')
            return
        self.progressbar.stop()
        self.progressbar.configure(mode='determinate', maximum=max(maximum, 1), value=val)
        pct = round((val / max(maximum, 1)) * 100)
        self.prog_pct_lbl.config(text=f'{pct}%')
        self.prog_label_lbl.config(text=label or f'{val} / {maximum}')

    # ---------------------------------------------------------
    # CONTADOR
    # ---------------------------------------------------------
    def update_counter(self):
        count = len(self.selected_files)
        lines = 0
        chars = 0
        meta_by_path = {m['rel_path']: m for m in self.all_meta}
        for rp in self.selected_files:
            m = meta_by_path.get(rp)
            if m:
                lines += m.get('lines', 0)
                chars += m.get('size', 0)
        tokens = estimate_tokens(chars)
        self.counter_text_lbl.config(text=f"{count} arquivo(s) selecionado(s) | ~{lines:,} linhas".replace(',', '.'))
        self.token_estimate_lbl.config(text=f"~{tokens:,} tokens est.".replace(',', '.'))
        self.file_count_badge.config(text=f"{len(self.all_meta)} arq.")
        self.st_right_lbl.config(text=f"{count} sel. | {len(self.all_meta)} total")

    # ---------------------------------------------------------
    # PADRÕES GLOBAIS DE IGNORE
    # ---------------------------------------------------------
    def update_ignore_summary(self):
        self.ignore_summary_lbl.config(text=f"{len(self.ignore_patterns)}/{len(ALL_IGNORE_PATTERNS)} padrões ativos")

    def open_ignore_dialog(self):
        IgnorePatternsDialog(self, self)

    def set_ignore_patterns(self, patterns):
        self.ignore_patterns = [p for p in ALL_IGNORE_PATTERNS if p in patterns]
        cfg = load_config()
        cfg['ignore_patterns'] = self.ignore_patterns
        save_config(cfg)
        self.update_ignore_summary()
        self.render_all_after_pattern_change()

    def render_all_after_pattern_change(self):
        to_remove = [rp for rp in self.selected_files
                     if any(should_ignore_global(part, self.ignore_patterns) for part in rp.split('/'))]
        for rp in to_remove:
            self.selected_files.discard(rp)
        self.refresh_all_lists()

    def refresh_all_lists(self):
        self.render_ext_list()
        self.render_file_list()
        self.render_search_list()
        self.tree_data = None
        if self.active_tab == 'explorer':
            self.populate_explorer()
        self.update_counter()

    # ---------------------------------------------------------
    # ARRASTAR-E-SOLTAR (drag & drop) — opcional, via tkinterdnd2
    # ---------------------------------------------------------
    def _setup_dnd(self):
        if not DND_AVAILABLE:
            self.log("Arrastar-e-soltar desabilitado (biblioteca 'tkinterdnd2' não instalada). "
                      "Use os botões normalmente, ou instale com: pip install tkinterdnd2", 'warn')
            return
        try:
            # Entrada principal: pasta ou .zip
            for w in (self.src_drop_zone, self.src_input_entry):
                if w is None:
                    continue
                w.drop_target_register(DND_FILES)
                w.dnd_bind('<<Drop>>', self._on_source_drop)
                w.dnd_bind('<<DropEnter>>', lambda e: self._on_dnd_hover(self.src_drop_zone, True))
                w.dnd_bind('<<DropLeave>>', lambda e: self._on_dnd_hover(self.src_drop_zone, False))

            # Avulsos
            for w in (self.arb_drop_zone, self.arb_tree):
                if w is None:
                    continue
                w.drop_target_register(DND_FILES)
                w.dnd_bind('<<Drop>>', self._on_arb_drop)
                w.dnd_bind('<<DropEnter>>', lambda e: self._on_dnd_hover(self.arb_drop_zone, True))
                w.dnd_bind('<<DropLeave>>', lambda e: self._on_dnd_hover(self.arb_drop_zone, False))

            self.log("Arrastar-e-soltar habilitado (pasta/.zip na entrada, arquivos na aba Avulsos).", 'ok')
        except Exception as e:
            self.log(f"[AVISO] Não foi possível habilitar arrastar-e-soltar: {e}", 'warn')

    def _on_dnd_hover(self, widget, entering):
        if widget is None:
            return
        if entering:
            widget.configure(background=self.primary_color, foreground='#ffffff')
        else:
            widget.configure(background=self.surface2, foreground=self.text2_color)

    def _parse_dnd_paths(self, data):
        """Converte a string bruta recebida no evento <<Drop>> em uma lista de
        caminhos, respeitando chaves {} usadas para caminhos com espaços."""
        try:
            paths = self.tk.splitlist(data)
        except Exception:
            paths = [p for p in re.split(r'\s+', data.strip()) if p]
        # Remove eventuais prefixos file:// (alguns gerenciadores de arquivo enviam assim)
        cleaned = []
        for p in paths:
            if p.lower().startswith('file://'):
                p = p[7:]
            cleaned.append(p)
        return [p for p in cleaned if p]

    def _on_source_drop(self, event):
        self._on_dnd_hover(self.src_drop_zone, False)
        paths = self._parse_dnd_paths(event.data)
        if not paths:
            return
        path = paths[0]
        if len(paths) > 1:
            self.toast('Apenas o primeiro item foi usado (arraste 1 pasta ou 1 .zip por vez).', 'warn')
        if os.path.isdir(path):
            self._start_scan(path, is_zip=False)
        elif os.path.isfile(path) and path.lower().endswith('.zip'):
            self._start_scan(path, is_zip=True)
        else:
            self.toast('Arraste uma pasta ou um arquivo .zip.', 'warn')

    def _on_arb_drop(self, event):
        self._on_dnd_hover(self.arb_drop_zone, False)
        paths = self._parse_dnd_paths(event.data)
        if not paths:
            return
        found = []
        for p in paths:
            if os.path.isdir(p):
                for dirpath, dirnames, filenames in os.walk(p):
                    for fn in filenames:
                        found.append(os.path.join(dirpath, fn))
            elif os.path.isfile(p):
                found.append(p)
        added = 0
        for fp in found:
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue
            name = os.path.basename(fp)
            if any(a['name'] == name and a['size'] == size for a in self.arb_files):
                continue
            self.arb_files.append({'name': name, 'abs_path': fp, 'size': size,
                                    'is_binary': is_bin_ext(name)})
            added += 1
        self.render_arb_list()
        self.log(f"{added} arquivo(s) avulso(s) adicionado(s) via arrastar-e-soltar.", 'ok')
        self.toast(f"✓ {added} arquivo(s) adicionados!", 'ok')

    # ---------------------------------------------------------
    # CARREGAMENTO DE PASTA / ZIP (em thread de fundo)
    # ---------------------------------------------------------
    def pick_source_dir(self):
        path = filedialog.askdirectory(title="Selecione a pasta de entrada")
        if not path:
            return
        self._start_scan(path, is_zip=False)

    def pick_zip(self):
        path = filedialog.askopenfilename(title="Selecione um arquivo ZIP",
                                           filetypes=[('Arquivo ZIP', '*.zip'), ('Todos os arquivos', '*.*')])
        if not path:
            return
        self._start_scan(path, is_zip=True)

    def _start_scan(self, path, is_zip):
        self.cancel_event = threading.Event()
        self.btn_start.config(state='disabled')
        self.set_progress('pulse', 100, 'Lendo índice do ZIP…' if is_zip else 'Lendo metadados…')
        self.set_status('Lendo metadados…')
        self.log('⟳ Iniciando varredura (apenas metadados)…', 'info')

        # IMPORTANTE: variáveis do Tkinter (StringVar/BooleanVar) só podem ser
        # lidas com segurança na thread principal. Por isso resolvemos todos os
        # valores necessários AQUI antes de disparar a thread de segundo plano.
        ignore_patterns = list(self.ignore_patterns)
        size_limit_kb = self._get_size_limit_kb()
        cancel_event = self.cancel_event

        def worker():
            try:
                def progress_cb(n):
                    self.task_queue.put(('scan_progress', n))

                if is_zip:
                    # Lê os metadados direto do índice do .zip, sem
                    # extrair nada para disco — muito mais rápido.
                    metas, root_name = scan_zip(path, ignore_patterns,
                                                 size_limit_kb, progress_cb,
                                                 cancel_event)
                else:
                    metas, root_name = scan_directory(path, ignore_patterns,
                                                        size_limit_kb, progress_cb,
                                                        cancel_event)
                self.task_queue.put(('scan_done', metas, root_name))
            except Exception as e:
                self.task_queue.put(('scan_error', str(e), traceback.format_exc()))

        threading.Thread(target=worker, daemon=True).start()

    def _get_size_limit_kb(self):
        if not self.size_filter_var.get():
            return None
        try:
            return float(self.max_size_var.get())
        except ValueError:
            return None

    def _poll_queue(self):
        try:
            while True:
                item = self.task_queue.get_nowait()
                kind = item[0]
                if kind == 'scan_progress':
                    n = item[1]
                    self.set_progress('pulse', 100, f'Analisando… {n} arquivo(s) encontrados')
                elif kind == 'scan_done':
                    self._on_scan_done(item[1], item[2])
                elif kind == 'scan_error':
                    self.set_progress(None)
                    self.btn_start.config(state='normal')
                    self.toast('Não foi possível ler a pasta/ZIP.', 'err')
                    self.log(f"[ERRO] {item[1]}", 'err')
                elif kind == 'output_progress':
                    done, total = item[1], item[2]
                    self.set_progress(done, total, f'Lendo {done}/{total}…')
                elif kind == 'output_done':
                    self._on_output_done(item[1], item[2], item[3], item[4])
                elif kind == 'output_error':
                    self.set_progress(None)
                    self.btn_start.config(state='normal')
                    self.toast('Erro ao gerar a saída.', 'err')
                    self.log(f"[ERRO] {item[1]}", 'err')
        except queue.Empty:
            pass
        self.after(60, self._poll_queue)

    def _on_scan_done(self, metas, root_name):
        self.all_meta = sort_list_by(metas, lambda m: m['rel_path'], self.sort_var.get() == 'Natural')
        self.src_input_var.set(root_name)
        self.src_root = root_name

        ext_set = sorted(set(m['ext'] for m in self.all_meta))
        self.all_exts = ext_set

        # Detecta .gitignore
        gi_meta = next((m for m in self.all_meta if m['name'] == '.gitignore'), None)
        if gi_meta:
            content = read_file_content(gi_meta)
            self.gi_file_rules = content.splitlines() if content is not None else []
            self.gi_status_lbl.config(text=f"✅ .gitignore: {len(self.gi_file_rules)} linha(s).")
            self.gi_checkbutton.config(state='normal')
        else:
            self.gi_file_rules = []
            self.gi_status_lbl.config(text="⚠ Nenhum .gitignore encontrado.")
            self.gi_checkbutton.config(state='disabled')
            self.gi_cb_var.set(False)
            self.apply_gi = False
        self.render_gi_rules()

        self.tree_data = None
        self.render_ext_list()
        self.render_file_list()
        if self.active_tab == 'explorer':
            self.populate_explorer()

        self.set_progress(None)
        self.btn_start.config(state='normal')
        self.set_status(f"✓ {len(self.all_meta)} arquivo(s) prontos")
        self.log(f"✓ {len(self.all_meta)} arquivo(s), {len(self.all_exts)} extensão(ões).", 'ok')
        self.update_counter()

    # ---------------------------------------------------------
    # CÓPIA / GERAÇÃO DE SAÍDA
    # ---------------------------------------------------------
    def start_copy(self):
        tab = self.active_tab
        src = self.src_input_var.get() or 'Entrada'
        out_name = self.out_name_var.get().strip() or 'codigo_completo.txt'
        gi_rules = self.gi_file_rules + self.gi_manual_rules
        metas = []

        if tab == 'ext':
            if not self.selected_exts:
                self.toast('Selecione ao menos uma extensão.', 'warn')
                return
            metas = [m for m in self.all_meta
                     if m['ext'] in self.selected_exts
                     and not gi_matches(m['rel_path'], gi_rules, self.apply_gi)
                     and not m['is_binary']]
        elif tab in ('files', 'search', 'explorer'):
            metas = [m for m in self.all_meta
                     if m['rel_path'] in self.selected_files
                     and not gi_matches(m['rel_path'], gi_rules, self.apply_gi)
                     and not m['is_binary']]
        elif tab == 'arb':
            checked = [self.arb_files[i] for i in sorted(self.arb_checked) if i < len(self.arb_files)]
            if not checked:
                self.toast('Nenhum avulso selecionado.', 'warn')
                return
            self.gen_arbitrary_output(checked, out_name)
            return
        elif tab == 'gi':
            if not self.all_meta:
                self.toast('Carregue os arquivos primeiro.', 'warn')
                return
            metas = [m for m in self.all_meta
                     if not gi_matches(m['rel_path'], gi_rules, self.apply_gi)
                     and not should_ignore_global(m['name'], self.ignore_patterns)
                     and not m['is_binary']]

        if not metas:
            self.toast('Nenhum arquivo para copiar.', 'warn')
            return

        total_size = sum(m['size'] for m in metas)
        if total_size > 10 * 1024 * 1024:
            if not messagebox.askyesno(
                    "Confirmar",
                    f"⚠ Estimativa: {total_size/1024/1024:.1f} MB. Continuar?"):
                return

        self.gen_output(metas, src, out_name)

    def gen_output(self, metas, src_dir, out_name):
        self.log(f"Gerando output: {len(metas)} arquivo(s)…", 'info')
        self.btn_start.config(state='disabled')
        self.set_progress(0, len(metas), 'Lendo arquivos…')

        def worker():
            try:
                total = len(metas)
                self.task_queue.put(('output_progress', 0, total))
                # Lê tudo de uma vez: agrupa por .zip de origem e abre cada
                # .zip só uma vez, em vez de reabrir por arquivo.
                text_metas = [m for m in metas if not m['is_binary']]
                content_map = read_contents_bulk(text_metas)
                self.task_queue.put(('output_progress', total, total))

                filters = []
                if self.ignore_patterns:
                    filters.append('padrões globais')
                if self.apply_gi:
                    filters.append('.gitignore')

                out = build_header(src_dir, len(metas), filters)
                copied = 0
                skipped = 0
                # Salvaguarda preventiva: garante que cada arquivo (por
                # caminho relativo) entre no loop no máximo uma vez, mesmo
                # que `metas` contenha entradas duplicadas por algum motivo
                # upstream (evita cabeçalhos repetidos no .txt gerado).
                seen_rel_paths = set()
                for m in metas:
                    if m['rel_path'] in seen_rel_paths:
                        continue
                    seen_rel_paths.add(m['rel_path'])
                    content = content_map.get(m['rel_path'])
                    if content is None:
                        skipped += 1
                        continue
                    # Normaliza (sem descartar) newlines finais do conteúdo
                    # antes de acrescentar o separador fixo '\n\n'. O
                    # restaurador assume que a fronteira entre blocos tem NO
                    # MÁXIMO 2 '\n' de "sujeira" adicionados por ele (e
                    # preserva 1 '\n' se o conteúdo original já terminava
                    # nele) — por isso colapsamos runs de 2+ '\n' finais para
                    # exatamente 1, em vez de usar rstrip puro, que apagaria
                    # a quebra de linha final de praticamente todo arquivo de
                    # texto bem formado (POSIX) e quebraria o round-trip.
                    clean_content = re.sub(r'\n{2,}$', '\n', content)
                    sep = '=' * 42 + '\n'
                    out += sep + f"Conteúdo de {m['name']} (caminho: {m['rel_path']}) [enc: utf-8]:\n" + sep
                    out += clean_content + '\n\n'
                    copied += 1

                out += '\n' + '=' * 42 + '\nEstrutura de pastas:\n' + '=' * 42 + '\n'
                out += build_tree_txt(metas, src_dir)

                self.task_queue.put(('output_done', out, out_name, copied, skipped))
            except Exception:
                self.task_queue.put(('output_error', traceback.format_exc()))

        threading.Thread(target=worker, daemon=True).start()

    def _on_output_done(self, out, out_name, copied, skipped):
        self.last_output = out
        self.set_progress(None)
        self.btn_start.config(state='normal')
        self.log(f"✓ {copied} arquivo(s) gerado(s). {skipped} ignorado(s).", 'ok')
        self.toast(f"✓ {copied} arquivo(s) prontos!", 'ok')
        OutputDialog(self, self, out, out_name, copied, len(out))
        self.update_counter()

    def gen_arbitrary_output(self, files, out_name):
        self.log(f"Unindo {len(files)} avulso(s)…", 'info')
        out = build_header('Arquivos Avulsos', len(files), [])
        n = 0
        for f in files:
            if f['is_binary']:
                self.log(f"[IGNORADO] {f['name']}", 'warn')
                continue
            try:
                with open(f['abs_path'], 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
            except OSError:
                self.log(f"[IGNORADO] {f['name']}", 'warn')
                continue
            clean_content = re.sub(r'\n{2,}$', '\n', content)
            out += '=' * 42 + '\n' + f"Conteúdo de {f['name']}:\n" + '=' * 42 + '\n' + clean_content + '\n\n'
            n += 1
        out += '\n' + '=' * 42 + '\nArquivos:\n' + '=' * 42 + '\n'
        for f in files:
            out += f"- {f['name']}\n"
        self.last_output = out
        self.toast(f"✓ {n} avulso(s) prontos!", 'ok')
        OutputDialog(self, self, out, out_name, n, len(out))

    # ---------------------------------------------------------
    # CLIPBOARD
    # ---------------------------------------------------------
    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.toast(f"✓ Copiado ({len(text):,} chars)".replace(',', '.'), 'ok')
        self.log(f"Copiado: {len(text):,} caracteres.".replace(',', '.'), 'ok')

    def clipboard_copy_last(self):
        if not self.last_output:
            self.toast('Execute a cópia primeiro.', 'warn')
            return
        self.copy_to_clipboard(self.last_output)

    # ---------------------------------------------------------
    # LIMPAR TUDO
    # ---------------------------------------------------------
    def clear_all(self):
        self.all_meta = []
        self.all_exts = []
        self.selected_files.clear()
        self.selected_exts.clear()
        self.arb_files = []
        self.arb_checked.clear()
        self.gi_file_rules = []
        self.gi_manual_rules = []
        self.apply_gi = False
        self.last_output = ''
        self.search_results = []
        self.gi_sel_idx = -1
        self.tree_data = None
        self.cancel_event.set()

        self.src_input_var.set('')
        self.out_name_var.set('codigo_completo.txt')
        self.ext_search_var.set('')
        self.file_search_var.set('')
        self.txt_search.delete('1.0', 'end')
        self.gi_input_var.set('')
        self.gi_cb_var.set(False)
        self.gi_checkbutton.config(state='disabled')

        self.ext_tree.delete(*self.ext_tree.get_children())
        self.file_tree.delete(*self.file_tree.get_children())
        self.search_tree.delete(*self.search_tree.get_children())
        self.explorer_tree.delete(*self.explorer_tree.get_children())
        self.arb_tree.delete(*self.arb_tree.get_children())
        self.gi_rules_list.delete(0, 'end')
        self.gi_preview.delete(0, 'end')
        self.gi_status_lbl.config(text="⚠ Nenhum diretório selecionado.")

        self.update_counter()
        self.set_status('Pronto', 'v3.0 — Python Edition')
        self.log('✓ Tudo limpo.', 'ok')
        self.toast('Limpo!', 'ok')
        self.set_progress(None)


# ==================================================================
# PONTO DE ENTRADA
# ==================================================================
def main():
    app = CodeCopierApp()
    app.mainloop()


if __name__ == '__main__':
    main()

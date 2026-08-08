#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copiador de Código v2.1 — Python / Tkinter Edition
=====================================================
Porte monolítico (arquivo único) da versão HTML/JS do "Copiador de Código".
Todas as funcionalidades da versão original foram preservadas:

  - Seleção de pasta de entrada (via os.walk — rápido mesmo em pastas grandes)
  - Importação de arquivo ZIP
  - Leitura "lazy" de conteúdo (metadados primeiro, conteúdo só na hora de gerar)
  - Aba Extensões (seleção por extensão, ordenável por nome/tamanho/qtde)
  - Aba Arquivos (checklist com busca)
  - Aba Buscar Nome (cola nomes/paths/saída de git status)
  - Aba Explorador (árvore de pastas com seleção em cascata)
  - Aba Avulsos (arquivos soltos de qualquer lugar)
  - Aba Gitignore (regras do .gitignore do projeto + regras manuais + preview)
  - Padrões globais de ignore (git, node, python, SO) configuráveis e persistidos
  - Filtro por tamanho máximo de arquivo
  - Geração de saída em texto único (cabeçalho + conteúdo + árvore de pastas)
  - Cópia para a área de transferência e download (salvar) do .txt
  - Log de atividades colapsável
  - Alternância de tema claro/escuro

A única funcionalidade que não tem equivalente nativo no Tkinter é o
"arrastar e soltar" de arquivos avulsos (exigiria uma dependência externa).
Em vez disso, a aba "Avulsos" usa um seletor de arquivos múltiplo, que
cumpre a mesma função.
"""

import os
import re
import io
import sys
import json
import math
import zipfile
import threading
import queue
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ============================================================
# CONSTANTES
# ============================================================
APP_TITLE = "Copiador de Código v2.1 — Python Edition"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".copiador_de_codigo_config.json")

PATTERN_GROUPS = [
    {"id": "vcs", "label": "Controle de versão",
     "patterns": [(".git", "Metadados do repositório Git")]},
    {"id": "node", "label": "Node.js / JavaScript",
     "patterns": [("node_modules", "Dependências do Node.js"),
                  ("dist", "Saída de build compilada"),
                  ("build", "Diretório de build"),
                  ("*.log", "Arquivos de log")]},
    {"id": "python", "label": "Python",
     "patterns": [("__pycache__", "Cache de bytecode do Python"),
                  ("venv", "Ambiente virtual Python"),
                  (".venv", "Ambiente virtual Python (oculto)"),
                  ("env", "Ambiente virtual Python"),
                  (".env", "Ambiente / variáveis de ambiente"),
                  (".tox", "Cache do Tox"),
                  (".mypy_cache", "Cache do MyPy"),
                  (".pytest_cache", "Cache do Pytest"),
                  ("*.pyc", "Bytecode Python compilado"),
                  ("*.pyo", "Bytecode Python otimizado"),
                  ("*.egg-info", "Metadados de pacote Python")]},
    {"id": "os", "label": "Sistema operacional",
     "patterns": [(".DS_Store", "Metadados de pasta do macOS"),
                  ("Thumbs.db", "Cache de miniaturas do Windows")]},
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

THEMES = {
    "light": dict(bg="#f1f5f9", surface="#ffffff", surface2="#f8fafc",
                   border="#e2e8f0", text="#1e293b", text2="#64748b",
                   primary="#2563eb", primary_dark="#1d4ed8", primary_light="#dbeafe",
                   success="#16a34a", success_light="#dcfce7",
                   warn="#d97706", warn_light="#fef3c7",
                   danger="#dc2626", danger_light="#fee2e2",
                   log_bg="#0f172a", log_fg="#94a3b8"),
    "dark": dict(bg="#0f172a", surface="#1e293b", surface2="#334155",
                  border="#475569", text="#e2e8f0", text2="#94a3b8",
                  primary="#3b82f6", primary_dark="#2563eb", primary_light="#1e3a8a",
                  success="#22c55e", success_light="#14532d",
                  warn="#f59e0b", warn_light="#78350f",
                  danger="#ef4444", danger_light="#7f1d1d",
                  log_bg="#0f172a", log_fg="#94a3b8"),
}


# ============================================================
# UTILITÁRIOS (equivalentes às funções JS `esc/natKey/sortArr/getExt/...`)
# ============================================================
def nat_key(s):
    """Chave de ordenação 'natural' — zero-pad nos números, como no JS original."""
    return re.sub(r"(\d+)", lambda m: m.group(1).zfill(20), s)


def sort_key(s, natural):
    return nat_key(s) if natural else s.lower()


def sort_strings(items, natural):
    return sorted(items, key=lambda s: sort_key(s, natural))


def sort_by(items, keyfn, natural):
    return sorted(items, key=lambda it: sort_key(keyfn(it), natural))


def get_ext(name):
    d = name.rfind(".")
    if d <= 0:
        return name if name.startswith(".") else "(sem extensão)"
    return name[d:].lower()


def is_bin_ext(name):
    return get_ext(name) in BINARY_EXTS


def fn_match(name, pat):
    """Equivalente ao fnMatch do JS: glob simples (* e ?) case-insensitive, match total."""
    esc = re.escape(pat)
    regex = "^" + esc.replace(r"\*", ".*").replace(r"\?", ".") + "$"
    return re.match(regex, name, re.IGNORECASE) is not None


def should_ignore_global(name, ignore_patterns):
    for p in ignore_patterns:
        if "*" in p:
            if fn_match(name, p):
                return True
        else:
            if name == p:
                return True
    return False


def fmt_size(b):
    if b < 1024:
        return f"{b} B"
    if b < 1048576:
        return f"{b/1024:.1f} KB"
    if b < 1073741824:
        return f"{b/1048576:.1f} MB"
    return f"{b/1073741824:.1f} GB"


def estimate_tokens(chars):
    return math.ceil(chars / 4)


# ============================================================
# MOTOR DE GITIGNORE (equivalente à função JS giMatches)
# ============================================================
def _gitignore_rule_to_regex(rule):
    escaped = re.escape(rule)
    s = escaped.replace(r"\*\*", "\u00a7").replace(r"\*", "[^/]*")
    s = s.replace(r"\?", "[^/]").replace("\u00a7", ".*")
    return s


def gi_matches(rel_path, rules, apply_gi):
    if not apply_gi:
        return False
    ignored = False
    norm = rel_path.replace("\\", "/")
    for raw in rules:
        raw_stripped = raw.strip()
        if not raw_stripped or raw_stripped.startswith("#"):
            continue
        neg = raw_stripped.startswith("!")
        rule = raw_stripped[1:].strip() if neg else raw_stripped
        if not rule:
            continue
        if rule.endswith("/"):
            rule = rule[:-1]
        reg_str = _gitignore_rule_to_regex(rule)
        has_slash = "/" in rule.rstrip("/")
        matched = False
        if has_slash:
            matched = re.match(f"^{reg_str}(/.*)?$", norm) is not None
        else:
            base = norm.split("/")[-1]
            matched = (re.match(f"^{reg_str}$", base) is not None or
                       re.search(f"(^|/){reg_str}(/|$)", norm) is not None)
        if matched:
            ignored = not neg
    return ignored


# ============================================================
# LEITURA DE DIRETÓRIO / ZIP (rápido — via os.walk / zipfile)
# ============================================================
def scan_directory(root_dir, ignore_patterns, size_filter_enabled, max_size_kb,
                    progress_cb=None, cancel_event=None):
    metas = []
    root_name = os.path.basename(os.path.normpath(root_dir)) or root_dir
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        if cancel_event is not None and cancel_event.is_set():
            break
        dirnames[:] = [d for d in dirnames if not should_ignore_global(d, ignore_patterns)]
        rel_dir = os.path.relpath(dirpath, root_dir)
        for fname in filenames:
            if should_ignore_global(fname, ignore_patterns):
                continue
            abspath = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(abspath)
            except OSError:
                continue
            if size_filter_enabled and size > max_size_kb * 1024:
                continue
            rel = fname if rel_dir == "." else f"{rel_dir.replace(os.sep, '/')}/{fname}"
            rel_path = f"{root_name}/{rel}"
            ext = get_ext(fname)
            binf = is_bin_ext(fname)
            est_lines = 0 if binf else round(size / 45)
            metas.append({"name": fname, "rel_path": rel_path, "ext": ext, "size": size,
                          "is_binary": binf, "lines": est_lines, "abs_path": abspath,
                          "zip_path": None, "zip_member": None})
            count += 1
            if progress_cb and count % 150 == 0:
                progress_cb(count)
    if progress_cb:
        progress_cb(count)
    return metas, root_name


def scan_zip(zip_path, ignore_patterns, size_filter_enabled, max_size_kb, progress_cb=None):
    metas = []
    root_name = os.path.splitext(os.path.basename(zip_path))[0] or "zip"
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            clean = info.filename.lstrip("./")
            if not clean:
                continue
            parts = clean.split("/")
            fname = parts[-1]
            if any(should_ignore_global(p, ignore_patterns) for p in parts):
                continue
            size = info.file_size
            if size_filter_enabled and size > max_size_kb * 1024:
                continue
            rel_path = f"{root_name}/{clean}"
            ext = get_ext(fname)
            binf = is_bin_ext(fname)
            est_lines = 0 if binf else round(size / 45)
            metas.append({"name": fname, "rel_path": rel_path, "ext": ext, "size": size,
                          "is_binary": binf, "lines": est_lines, "abs_path": None,
                          "zip_path": zip_path, "zip_member": info.filename})
            count += 1
            if progress_cb and count % 150 == 0:
                progress_cb(count)
    if progress_cb:
        progress_cb(count)
    return metas, root_name


def read_file_content(meta):
    """Leitura lazy — só é chamada na hora de gerar a saída."""
    try:
        if meta.get("zip_path"):
            with zipfile.ZipFile(meta["zip_path"]) as zf:
                data = zf.read(meta["zip_member"])
        else:
            with open(meta["abs_path"], "rb") as f:
                data = f.read()
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None


# ============================================================
# CONSTRUÇÃO DE ÁRVORE / CABEÇALHO / SAÍDA FINAL
# ============================================================
def build_tree_txt(metas, root_name):
    root = {"ch": {}, "files": []}
    for m in metas:
        parts = m["rel_path"].split("/")
        node = root
        for p in parts[:-1]:
            node = node["ch"].setdefault(p, {"ch": {}, "files": []})
        node["files"].append(m)

    def _print(node, prefix):
        out = ""
        keys = sorted(node["ch"].keys())
        items = [("d", k, node["ch"][k]) for k in keys] + [("f", f["name"], None) for f in node["files"]]
        for i, (t, name, child) in enumerate(items):
            last = i == len(items) - 1
            out += prefix + ("`-- " if last else "|-- ") + name + "\n"
            if t == "d":
                out += _print(child, prefix + ("  " if last else "| "))
        return out

    return root_name + "\n" + _print(root, "")


def build_header(src, count, filters):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    h = "=" * 60 + "\n  COPIADOR DE CÓDIGO v2.1 — Python Edition\n" + "=" * 60 + "\n"
    h += f"  Data/Hora     : {now}\n  Origem        : {src}\n  Total arquivos: {count}\n"
    if filters:
        h += f"  Filtros       : {', '.join(filters)}\n"
    h += "=" * 60 + "\n\n"
    return h


def generate_output(metas, src_dir, filters, progress_cb=None, cancel_event=None):
    out_parts = [build_header(src_dir, len(metas), filters)]
    copied = 0
    skipped = 0
    total = len(metas)
    for i, m in enumerate(metas):
        if cancel_event is not None and cancel_event.is_set():
            break
        content = None if m["is_binary"] else read_file_content(m)
        if content is None:
            skipped += 1
        else:
            sep = "=" * 42 + "\n"
            out_parts.append(sep + f"Conteúdo de {m['name']} (caminho: {m['rel_path']}) [enc: utf-8]:\n" +
                              sep + content + "\n\n")
            copied += 1
        if progress_cb and (i % 25 == 0 or i == total - 1):
            progress_cb(i + 1, total)
    out_parts.append("\n" + "=" * 42 + "\nEstrutura de pastas:\n" + "=" * 42 + "\n")
    out_parts.append(build_tree_txt(metas, src_dir))
    return "".join(out_parts), copied, skipped


def generate_arbitrary_output(files):
    out_parts = [build_header("Arquivos Avulsos", len(files), [])]
    n = 0
    for f in files:
        if not f["content"]:
            continue
        out_parts.append("=" * 42 + "\n" + f"Conteúdo de {f['name']}:\n" + "=" * 42 + "\n" +
                          f["content"] + "\n\n")
        n += 1
    out_parts.append("\n" + "=" * 42 + "\nArquivos:\n" + "=" * 42 + "\n")
    for f in files:
        out_parts.append(f"- {f['name']}\n")
    return "".join(out_parts), n


# ============================================================
# ESTADO DA APLICAÇÃO (equivalente ao objeto `S` do JS)
# ============================================================
class State:
    def __init__(self):
        self.all_meta = []          # [{name, rel_path, ext, size, is_binary, lines, abs_path/zip...}]
        self.all_exts = []          # list[str]
        self.selected_files = set() # rel_path
        self.selected_exts = set()
        self.arb_files = []         # [{name, content, size, is_binary, checked}]
        self.gi_file_rules = []
        self.gi_manual_rules = []
        self.gi_sel_index = -1
        self.apply_gi = False
        self.ignore_patterns = list(ALL_IGNORE_PATTERNS)
        self.last_output = ""
        self.last_output_name = "codigo_completo.txt"
        self.active_tab = "ext"
        self.search_results = []
        self.log_count = 0
        self.cancel_event = threading.Event()
        self.ext_sort = {"col": None, "dir": "asc"}
        self.theme = "light"
        self.root_dir_label = ""


# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================
class CopiadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.S = State()
        self._load_config()

        self.title(APP_TITLE)
        self.geometry("1000x760")
        self.minsize(760, 560)

        self.natural_var = tk.StringVar(value="natural")
        self.out_name_var = tk.StringVar(value="codigo_completo.txt")
        self.src_label_var = tk.StringVar(value="")
        self.size_filter_var = tk.BooleanVar(value=False)
        self.max_kb_var = tk.StringVar(value="500")
        self.gi_apply_var = tk.BooleanVar(value=False)
        self.ext_search_var = tk.StringVar()
        self.file_search_var = tk.StringVar()

        self.queue = queue.Queue()
        self.explorer_dir_files = {}

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._build_ui()
        self._apply_theme(self.S.theme)
        self._update_ignore_summary()
        self.log("Bem-vindo ao Copiador de Código v2.1 — Python Edition.", "info")
        self.log("Selecione uma pasta de entrada para começar.", "info")
        self.update_counter()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._poll_queue)

    # --------------------------------------------------------
    # CONFIG (persistência local — equivalente ao localStorage)
    # --------------------------------------------------------
    def _load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            stored = data.get("ignorePatterns")
            if isinstance(stored, list):
                self.S.ignore_patterns = [p for p in ALL_IGNORE_PATTERNS if p in stored]
            self.S.theme = data.get("theme", "light")
        except Exception:
            self.S.ignore_patterns = list(ALL_IGNORE_PATTERNS)
            self.S.theme = "light"

    def _save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"ignorePatterns": self.S.ignore_patterns, "theme": self.S.theme}, f)
        except Exception:
            pass

    def _on_close(self):
        self._save_config()
        self.destroy()

    # --------------------------------------------------------
    # CONSTRUÇÃO DA UI
    # --------------------------------------------------------
    def _build_ui(self):
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)
        self.outer = outer

        self._build_header(outer)
        self._build_config(outer)
        self._build_tabs(outer)
        self._build_counter(outer)
        self._build_progress(outer)
        self._build_actions(outer)
        self._build_log(outer)
        self._build_statusbar(outer)

    def _build_header(self, parent):
        bar = tk.Frame(parent, height=44)
        bar.pack(fill="x", pady=(0, 6))
        self.header_frame = bar
        title = tk.Label(bar, text="📄 Copiador de Código", font=("Segoe UI", 13, "bold"))
        title.pack(side="left", padx=10, pady=8)
        self.header_title_lbl = title

        right = tk.Frame(bar)
        right.pack(side="right", padx=10)
        self.theme_btn = tk.Button(right, text="🌙", relief="flat", command=self.toggle_theme, bd=0)
        self.theme_btn.pack(side="right", padx=4)
        self.file_count_badge = tk.Label(right, text="0 arq.", font=("Segoe UI", 9, "bold"))
        self.file_count_badge.pack(side="right", padx=6)
        self.header_status_lbl = tk.Label(right, text="Pronto", font=("Segoe UI", 9))
        self.header_status_lbl.pack(side="right", padx=6)

    def _build_config(self, parent):
        cfg = ttk.LabelFrame(parent, text="⚙ Configurações")
        cfg.pack(fill="x", pady=(0, 6))

        row1 = ttk.Frame(cfg)
        row1.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(row1, text="📂 Entrada:", width=12).pack(side="left")
        entry_src = ttk.Entry(row1, textvariable=self.src_label_var, state="readonly")
        entry_src.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row1, text="Pasta…", command=self.pick_source_dir).pack(side="left", padx=2)
        ttk.Button(row1, text="ZIP…", command=self.pick_zip).pack(side="left", padx=2)

        row2 = ttk.Frame(cfg)
        row2.pack(fill="x", padx=8, pady=2)
        ttk.Label(row2, text="💾 Saída:", width=12).pack(side="left")
        ttk.Entry(row2, textvariable=self.out_name_var).pack(side="left", fill="x", expand=True, padx=4)

        row3 = ttk.Frame(cfg)
        row3.pack(fill="x", padx=8, pady=(2, 8))
        ttk.Label(row3, text="Ordem:").pack(side="left")
        combo = ttk.Combobox(row3, textvariable=self.natural_var, state="readonly", width=12,
                              values=["natural", "alpha"])
        combo.pack(side="left", padx=4)
        combo.bind("<<ComboboxSelected>>", lambda e: self._on_sort_mode_change())
        ttk.Button(row3, text="Padrões globais…", command=self.open_ignore_modal).pack(side="left", padx=8)
        self.ignore_summary_lbl = ttk.Label(row3, text="Carregando padrões…")
        self.ignore_summary_lbl.pack(side="left", padx=4)

        ttk.Checkbutton(row3, text="Ignorar >", variable=self.size_filter_var).pack(side="left", padx=(14, 2))
        ttk.Entry(row3, textvariable=self.max_kb_var, width=6).pack(side="left")
        ttk.Label(row3, text="KB").pack(side="left", padx=(2, 0))

    def _build_tabs(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True, pady=(0, 6))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.tab_ext = ttk.Frame(self.notebook)
        self.tab_files = ttk.Frame(self.notebook)
        self.tab_search = ttk.Frame(self.notebook)
        self.tab_explorer = ttk.Frame(self.notebook)
        self.tab_arb = ttk.Frame(self.notebook)
        self.tab_gi = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_ext, text="Extensões")
        self.notebook.add(self.tab_files, text="Arquivos")
        self.notebook.add(self.tab_search, text="Buscar Nome")
        self.notebook.add(self.tab_explorer, text="Explorador")
        self.notebook.add(self.tab_arb, text="Avulsos")
        self.notebook.add(self.tab_gi, text="Gitignore")

        self._tab_ids = {self.tab_ext: "ext", self.tab_files: "files", self.tab_search: "search",
                          self.tab_explorer: "explorer", self.tab_arb: "arb", self.tab_gi: "gi"}

        self._build_tab_ext()
        self._build_tab_files()
        self._build_tab_search()
        self._build_tab_explorer()
        self._build_tab_arb()
        self._build_tab_gi()

    def _on_tab_changed(self, event):
        idx = self.notebook.index(self.notebook.select())
        tab_widget = self.notebook.winfo_children()[idx] if False else None
        # map by tab id ordering
        ids = ["ext", "files", "search", "explorer", "arb", "gi"]
        self.S.active_tab = ids[idx]

    # ---- ABA EXTENSÕES ----
    def _build_tab_ext(self):
        f = self.tab_ext
        search_row = ttk.Frame(f)
        search_row.pack(fill="x", padx=6, pady=4)
        ttk.Label(search_row, text="🔍").pack(side="left")
        e = ttk.Entry(search_row, textvariable=self.ext_search_var)
        e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<KeyRelease>", lambda ev: self.render_ext_list())

        cols = [("sel", "✓", 34, "center"), ("ext", "Extensão", 200, "w"),
                ("size", "Tamanho", 100, "e"), ("count", "Arquivos", 90, "e")]
        self.ext_tree = ttk.Treeview(f, columns=[c[0] for c in cols], show="headings",
                                      selectmode="none", height=14)
        for cid, heading, width, anchor in cols:
            if cid != "sel":
                self.ext_tree.heading(cid, text=heading, command=lambda c=cid: self.sort_ext_by(c))
            else:
                self.ext_tree.heading(cid, text=heading)
            self.ext_tree.column(cid, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(f, orient="vertical", command=self.ext_tree.yview)
        self.ext_tree.configure(yscrollcommand=vsb.set)
        self.ext_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)
        self.ext_tree.bind("<Button-1>", self._on_ext_click)
        self.ext_tree.tag_configure("binfile", foreground="#b45309")

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=6, pady=2)
        ttk.Button(btn_row, text="✅ Tudo", command=self.select_all_ext).pack(side="left", padx=2)
        ttk.Button(btn_row, text="⬜ Nenhum", command=self.deselect_all_ext).pack(side="left", padx=2)
        self.ext_counter_lbl = ttk.Label(btn_row, text="0 sel.")
        self.ext_counter_lbl.pack(side="right", padx=4)

    # ---- ABA ARQUIVOS ----
    def _build_tab_files(self):
        f = self.tab_files
        search_row = ttk.Frame(f)
        search_row.pack(fill="x", padx=6, pady=4)
        ttk.Label(search_row, text="🔍").pack(side="left")
        e = ttk.Entry(search_row, textvariable=self.file_search_var)
        e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<KeyRelease>", lambda ev: self.render_file_list())

        cols = [("sel", "✓", 34, "center"), ("name", "Nome", 260, "w"),
                ("dir", "Pasta", 300, "w"), ("size", "Tamanho", 90, "e")]
        self.file_tree = ttk.Treeview(f, columns=[c[0] for c in cols], show="headings",
                                       selectmode="none", height=14)
        for cid, heading, width, anchor in cols:
            self.file_tree.heading(cid, text=heading)
            self.file_tree.column(cid, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(f, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=vsb.set)
        self.file_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)
        self.file_tree.bind("<Button-1>", self._on_file_click)
        self.file_tree.tag_configure("binfile", foreground="#b45309")

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=6, pady=2)
        ttk.Button(btn_row, text="✅ Tudo", command=self.select_all_files).pack(side="left", padx=2)
        ttk.Button(btn_row, text="⬜ Nenhum", command=self.deselect_all_files).pack(side="left", padx=2)
        self.file_counter_lbl = ttk.Label(btn_row, text="")
        self.file_counter_lbl.pack(side="right", padx=4)

    # ---- ABA BUSCAR NOME ----
    def _build_tab_search(self):
        f = self.tab_search
        ttk.Label(f, text="Cole nomes, caminhos ou saída de git status:").pack(
            anchor="w", padx=6, pady=(6, 2))
        self.search_text = tk.Text(f, height=4, wrap="word")
        self.search_text.pack(fill="x", padx=6, pady=2)

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=6, pady=4)
        ttk.Button(btn_row, text="🔍 Buscar", command=self.do_search).pack(side="left", padx=2)
        ttk.Button(btn_row, text="✅ Tudo", command=self.select_all_search).pack(side="left", padx=2)
        ttk.Button(btn_row, text="⬜ Nenhum", command=self.deselect_all_search).pack(side="left", padx=2)

        cols = [("sel", "✓", 34, "center"), ("path", "Caminho", 500, "w")]
        self.search_tree = ttk.Treeview(f, columns=[c[0] for c in cols], show="headings",
                                         selectmode="none", height=12)
        for cid, heading, width, anchor in cols:
            self.search_tree.heading(cid, text=heading)
            self.search_tree.column(cid, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(f, orient="vertical", command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=vsb.set)
        self.search_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)
        self.search_tree.bind("<Button-1>", self._on_search_click)
        self.search_tree.tag_configure("binfile", foreground="#b45309")

    # ---- ABA EXPLORADOR ----
    def _build_tab_explorer(self):
        f = self.tab_explorer
        top = ttk.Frame(f)
        top.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(top, text="Clique para marcar arquivos e pastas:").pack(side="left")
        ttk.Button(top, text="Expandir tudo", command=self.expand_all_tree).pack(side="right", padx=2)
        ttk.Button(top, text="Recolher tudo", command=self.collapse_all_tree).pack(side="right", padx=2)

        self.tree_explorer = ttk.Treeview(f, show="tree", selectmode="none", height=16)
        vsb = ttk.Scrollbar(f, orient="vertical", command=self.tree_explorer.yview)
        self.tree_explorer.configure(yscrollcommand=vsb.set)
        self.tree_explorer.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)
        self.tree_explorer.bind("<Button-1>", self._on_explorer_click)
        self.tree_explorer.insert("", "end", iid="EMPTY", text="Selecione uma pasta de entrada.")

    # ---- ABA AVULSOS ----
    def _build_tab_arb(self):
        f = self.tab_arb
        ttk.Label(f, text="Arquivos avulsos de qualquer local (use o botão abaixo para adicionar):").pack(
            anchor="w", padx=6, pady=(6, 2))

        cols = [("sel", "✓", 34, "center"), ("name", "Nome", 320, "w"), ("size", "Tamanho", 90, "e")]
        self.arb_tree = ttk.Treeview(f, columns=[c[0] for c in cols], show="headings",
                                      selectmode="none", height=13)
        for cid, heading, width, anchor in cols:
            self.arb_tree.heading(cid, text=heading)
            self.arb_tree.column(cid, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(f, orient="vertical", command=self.arb_tree.yview)
        self.arb_tree.configure(yscrollcommand=vsb.set)
        self.arb_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)
        self.arb_tree.bind("<Button-1>", self._on_arb_click)
        self.arb_tree.tag_configure("binfile", foreground="#b45309")

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=6, pady=4)
        ttk.Button(btn_row, text="➕ Adicionar…", command=self.pick_arb_files).pack(side="left", padx=2)
        ttk.Button(btn_row, text="➖ Remover marcados", command=self.remove_checked_arb).pack(side="left", padx=2)
        ttk.Button(btn_row, text="🗑 Limpar", command=self.clear_arb).pack(side="left", padx=2)

    # ---- ABA GITIGNORE ----
    def _build_tab_gi(self):
        f = self.tab_gi
        top = ttk.Frame(f)
        top.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Checkbutton(top, text="Aplicar regras .gitignore", variable=self.gi_apply_var,
                         command=self.toggle_gi).pack(side="left")
        self.gi_status_lbl = ttk.Label(top, text="⚠ Nenhum diretório selecionado.")
        self.gi_status_lbl.pack(side="left", padx=10)

        split = ttk.Frame(f)
        split.pack(fill="both", expand=True, padx=6, pady=4)

        left = ttk.Frame(split)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        ttk.Label(left, text="Regras:").pack(anchor="w")
        self.gi_listbox = tk.Listbox(left, height=12, exportselection=False)
        self.gi_listbox.pack(fill="both", expand=True, pady=2)
        self.gi_listbox.bind("<<ListboxSelect>>", self._on_gi_select)
        add_row = ttk.Frame(left)
        add_row.pack(fill="x", pady=2)
        self.gi_input_var = tk.StringVar()
        gi_entry = ttk.Entry(add_row, textvariable=self.gi_input_var)
        gi_entry.pack(side="left", fill="x", expand=True)
        gi_entry.bind("<Return>", lambda e: self.add_gi_rule())
        ttk.Button(add_row, text="+", width=3, command=self.add_gi_rule).pack(side="left", padx=2)
        ttk.Button(add_row, text="−", width=3, command=self.remove_gi_rule).pack(side="left")

        right = ttk.Frame(split)
        right.pack(side="left", fill="both", expand=True, padx=(4, 0))
        ttk.Label(right, text="Preview:").pack(anchor="w")
        self.gi_preview_list = tk.Listbox(right, height=12, exportselection=False)
        self.gi_preview_list.pack(fill="both", expand=True, pady=2)
        ttk.Button(right, text="🔄 Atualizar", command=self.refresh_gi_preview).pack(anchor="w")

    # ---- CONTADOR / PROGRESSO / AÇÕES / LOG / STATUS ----
    def _build_counter(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 4))
        self.counter_text_lbl = ttk.Label(bar, text="0 arquivo(s) selecionado(s) | ~0 linhas",
                                           font=("Consolas", 9, "bold"))
        self.counter_text_lbl.pack(side="left", padx=4)
        self.token_estimate_lbl = ttk.Label(bar, text="~0 tokens estimados")
        self.token_estimate_lbl.pack(side="right", padx=4)

    def _build_progress(self, parent):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="x", pady=(0, 4))
        info = ttk.Frame(wrap)
        info.pack(fill="x")
        self.prog_label_lbl = ttk.Label(info, text="")
        self.prog_label_lbl.pack(side="left")
        self.prog_pct_lbl = ttk.Label(info, text="")
        self.prog_pct_lbl.pack(side="right")
        self.progress_bar = ttk.Progressbar(wrap, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x")
        self.progress_wrap = wrap

    def _build_actions(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 6))
        self.btn_start = tk.Button(row, text="▶ INICIAR CÓPIA", command=self.start_copy,
                                    bg="#dcfce7", fg="#166534", font=("Segoe UI", 10, "bold"),
                                    relief="ridge", height=2)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_clear = tk.Button(row, text="🗑 Limpar", command=self.clear_all,
                                    bg="#fef3c7", fg="#92400e", relief="ridge")
        self.btn_clear.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_clip = tk.Button(row, text="📋 Clipboard", command=self.clipboard_copy,
                                   bg="#dbeafe", fg="#1d4ed8", relief="ridge")
        self.btn_clip.pack(side="left", fill="x", expand=True, padx=2)

    def _build_log(self, parent):
        section = ttk.LabelFrame(parent, text="")
        section.pack(fill="x", pady=(0, 4))
        header = ttk.Frame(section)
        header.pack(fill="x")
        self.log_title_lbl = ttk.Label(header, text="📋 Log")
        self.log_title_lbl.pack(side="left", padx=4)
        self.log_badge_lbl = ttk.Label(header, text="0")
        self.log_badge_lbl.pack(side="left", padx=4)
        ttk.Button(header, text="limpar", command=self.clear_log, width=8).pack(side="right", padx=2)
        self.log_toggle_btn = ttk.Button(header, text="▲ recolher", command=self.toggle_log, width=12)
        self.log_toggle_btn.pack(side="right", padx=2)
        self.log_expand_btn = ttk.Button(header, text="⛶ expandir", command=self.expand_log, width=12)
        self.log_expand_btn.pack(side="right", padx=2)

        self.log_text = tk.Text(section, height=4, bg="#0f172a", fg="#94a3b8",
                                 font=("Consolas", 9), state="disabled")
        self.log_text.pack(fill="x")
        for tag, color in (("ok", "#4ade80"), ("warn", "#fbbf24"), ("err", "#f87171"), ("info", "#60a5fa")):
            self.log_text.tag_configure(tag, foreground=color)
        self._log_collapsed = False
        self._log_expanded = False

    def _build_statusbar(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x")
        self.st_left_lbl = ttk.Label(bar, text="Pronto")
        self.st_left_lbl.pack(side="left", padx=4)
        self.st_right_lbl = ttk.Label(bar, text="v2.1 — Python Edition")
        self.st_right_lbl.pack(side="right", padx=4)

    # --------------------------------------------------------
    # LOG / TOAST / STATUS
    # --------------------------------------------------------
    def log(self, msg, kind=""):
        self.S.log_count += 1
        self.log_badge_lbl.config(text=str(self.S.log_count) if self.S.log_count <= 99 else "99+")
        if self._log_collapsed:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n", (kind,) if kind else ())
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self.S.log_count = 0
        self.log_badge_lbl.config(text="0")

    def toggle_log(self):
        self._log_collapsed = not self._log_collapsed
        if self._log_collapsed:
            self.log_text.pack_forget()
            self.log_toggle_btn.config(text="▼ expandir")
        else:
            self.log_text.pack(fill="x")
            self.log_toggle_btn.config(text="▲ recolher")

    def expand_log(self):
        self._log_expanded = not self._log_expanded
        self.log_text.config(height=12 if self._log_expanded else 4)
        self.log_expand_btn.config(text="⛶ reduzir" if self._log_expanded else "⛶ expandir")

    def toast(self, msg, kind="ok"):
        # Sem overlay dedicado — usamos a barra de status + log como no HTML "toast".
        self.st_left_lbl.config(text=msg)
        self.after(3000, lambda: self.st_left_lbl.config(text="Pronto"))

    def set_status(self, left, right=None):
        self.st_left_lbl.config(text=left)
        self.header_status_lbl.config(text=left)
        if right:
            self.st_right_lbl.config(text=right)

    def set_progress(self, value, maximum=100, label=""):
        if value is None:
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate", value=0)
            self.prog_label_lbl.config(text="")
            self.prog_pct_lbl.config(text="")
            return
        if value == "pulse":
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(12)
            self.prog_label_lbl.config(text=label or "Processando…")
            self.prog_pct_lbl.config(text="")
            return
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", maximum=maximum, value=value)
        pct = round((value / maximum) * 100) if maximum else 0
        self.prog_pct_lbl.config(text=f"{pct}%")
        self.prog_label_lbl.config(text=label or f"{value} / {maximum}")

    # --------------------------------------------------------
    # TEMA
    # --------------------------------------------------------
    def toggle_theme(self):
        self.S.theme = "dark" if self.S.theme == "light" else "light"
        self._apply_theme(self.S.theme)
        self._save_config()
        self.log(f"Tema alterado para {self.S.theme}.", "info")

    def _apply_theme(self, theme):
        t = THEMES[theme]
        self.theme_btn.config(text="☀️" if theme == "dark" else "🌙")
        self.configure(bg=t["bg"])
        self.outer.configure(style="TFrame")
        self.style.configure("TFrame", background=t["bg"])
        self.style.configure("TLabel", background=t["bg"], foreground=t["text"])
        self.style.configure("TLabelframe", background=t["bg"], foreground=t["text"])
        self.style.configure("TLabelframe.Label", background=t["bg"], foreground=t["text"])
        self.style.configure("TNotebook", background=t["bg"])
        self.style.configure("TNotebook.Tab", background=t["surface2"], foreground=t["text"])
        self.style.configure("Treeview", background=t["surface2"], fieldbackground=t["surface2"],
                              foreground=t["text"])
        self.style.configure("Treeview.Heading", background=t["surface"], foreground=t["text"])
        self.header_frame.configure(bg=t["primary"])
        self.header_title_lbl.configure(bg=t["primary"], fg="white")
        for w in self.header_frame.winfo_children():
            try:
                w.configure(bg=t["primary"], fg="white")
            except tk.TclError:
                pass
        try:
            self.theme_btn.configure(bg=t["primary"], fg="white")
        except tk.TclError:
            pass

    # --------------------------------------------------------
    # COUNTER
    # --------------------------------------------------------
    def update_counter(self):
        count = len(self.S.selected_files)
        lines = 0
        chars = 0
        meta_by_rp = {m["rel_path"]: m for m in self.S.all_meta}
        for rp in self.S.selected_files:
            m = meta_by_rp.get(rp)
            if m:
                lines += m["lines"] or 0
                chars += m["size"] or 0
        tokens = estimate_tokens(chars)
        self.counter_text_lbl.config(text=f"{count} arquivo(s) selecionado(s) | ~{lines:,} linhas".replace(",", "."))
        self.token_estimate_lbl.config(text=f"~{tokens:,} tokens est.".replace(",", "."))
        self.file_count_badge.config(text=f"{len(self.S.all_meta)} arq.")
        self.st_right_lbl.config(text=f"{count} sel. | {len(self.S.all_meta)} total")

    def natural(self):
        return self.natural_var.get() == "natural"

    def _on_sort_mode_change(self):
        self.render_ext_list()
        self.render_file_list()
        self.render_search_list()
        self.build_explorer_tree()

    # --------------------------------------------------------
    # CARREGAMENTO DE PASTA / ZIP (em thread separada)
    # --------------------------------------------------------
    def pick_source_dir(self):
        d = filedialog.askdirectory(title="Selecione a pasta de entrada")
        if not d:
            return
        self._start_load(kind="dir", path=d)

    def pick_zip(self):
        p = filedialog.askopenfilename(title="Selecione o arquivo ZIP",
                                        filetypes=[("Arquivos ZIP", "*.zip")])
        if not p:
            return
        self._start_load(kind="zip", path=p)

    def _start_load(self, kind, path):
        self.S.cancel_event = threading.Event()
        self.btn_start.config(state="disabled")
        self.set_progress("pulse", 100, "Analisando arquivos…")
        self.log("⟳ Iniciando varredura (apenas metadados)…", "info")
        self.set_status("Carregando…")

        size_filter = self.size_filter_var.get()
        try:
            max_kb = int(self.max_kb_var.get())
        except ValueError:
            max_kb = 500
        ignore_patterns = list(self.S.ignore_patterns)
        cancel_event = self.S.cancel_event

        def progress_cb(count, total=None):
            self.queue.put(("scan_progress", count))

        def worker():
            try:
                if kind == "dir":
                    metas, root_name = scan_directory(path, ignore_patterns, size_filter, max_kb,
                                                        progress_cb, cancel_event)
                else:
                    metas, root_name = scan_zip(path, ignore_patterns, size_filter, max_kb, progress_cb)
                self.queue.put(("scan_done", metas, root_name))
            except Exception as exc:
                self.queue.put(("scan_error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_done(self, metas, root_name):
        metas = sort_by(metas, lambda m: m["rel_path"], self.natural())
        self.S.all_meta = metas
        self.S.selected_files = set()
        self.S.selected_exts = set()
        self.S.root_dir_label = root_name
        self.src_label_var.set(root_name)

        ext_set = sorted(set(m["ext"] for m in metas))
        self.S.all_exts = sort_strings(ext_set, self.natural())

        gi_meta = next((m for m in metas if m["name"] == ".gitignore"), None)
        if gi_meta:
            content = read_file_content(gi_meta)
            self.S.gi_file_rules = content.splitlines() if content else []
            self.gi_status_lbl.config(text=f"✅ .gitignore: {len(self.S.gi_file_rules)} linha(s).")
        else:
            self.S.gi_file_rules = []
            self.gi_status_lbl.config(text="⚠ Nenhum .gitignore encontrado.")
            self.gi_apply_var.set(False)
            self.S.apply_gi = False
        self.render_gi_rules()

        self.render_ext_list()
        self.render_file_list()
        self.build_explorer_tree()
        self.set_progress(None)
        self.btn_start.config(state="normal")
        self.set_status(f"✓ {len(metas)} arquivo(s) prontos")
        self.log(f"✓ {len(metas)} arquivo(s), {len(self.S.all_exts)} extensão(ões).", "ok")
        self.update_counter()

    # --------------------------------------------------------
    # FILA DE EVENTOS DA THREAD DE FUNDO
    # --------------------------------------------------------
    def _poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]
                if kind == "scan_progress":
                    count = item[1]
                    self.set_progress("pulse", 100, f"Analisando {count} arquivo(s)…")
                elif kind == "scan_done":
                    self._on_scan_done(item[1], item[2])
                elif kind == "scan_error":
                    self.set_progress(None)
                    self.btn_start.config(state="normal")
                    self.toast("Não foi possível ler a pasta/ZIP.", "err")
                    self.log(f"[ERRO] {item[1]}", "err")
                elif kind == "gen_progress":
                    done, total = item[1], item[2]
                    self.set_progress(done, total, f"Lendo {done}/{total}…")
                elif kind == "gen_done":
                    self._on_gen_done(item[1], item[2], item[3], item[4])
                elif kind == "gen_error":
                    self.set_progress(None)
                    self.btn_start.config(state="normal")
                    self.toast("Erro ao gerar a saída.", "err")
                    self.log(f"[ERRO] {item[1]}", "err")
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    # --------------------------------------------------------
    # RENDER: EXTENSÕES
    # --------------------------------------------------------
    def sort_ext_by(self, col):
        if self.S.ext_sort["col"] == col:
            self.S.ext_sort["dir"] = "desc" if self.S.ext_sort["dir"] == "asc" else "asc"
        else:
            self.S.ext_sort["col"] = col
            self.S.ext_sort["dir"] = "asc"
        self.render_ext_list()

    def render_ext_list(self):
        q = self.ext_search_var.get().lower()
        sorted_exts = list(self.S.all_exts)
        col = self.S.ext_sort["col"]
        if col:
            def size_of(e):
                return sum(m["size"] for m in self.S.all_meta if m["ext"] == e)

            def count_of(e):
                return sum(1 for m in self.S.all_meta if m["ext"] == e)

            if col == "ext":
                sorted_exts.sort(key=lambda e: e.lower())
            elif col == "size":
                sorted_exts.sort(key=size_of)
            elif col == "count":
                sorted_exts.sort(key=count_of)
            if self.S.ext_sort["dir"] == "desc":
                sorted_exts.reverse()
        else:
            sorted_exts = sort_strings(sorted_exts, self.natural())

        filtered = [e for e in sorted_exts if q in e.lower()]
        self.ext_tree.delete(*self.ext_tree.get_children())
        for ext in filtered:
            group = [m for m in self.S.all_meta if m["ext"] == ext]
            count = len(group)
            total_size = sum(m["size"] for m in group)
            sel = ext in self.S.selected_exts
            mark = "☑" if sel else "☐"
            label = ext + ("  (binário)" if ext in BINARY_EXTS else "")
            tags = ("binfile",) if ext in BINARY_EXTS else ()
            self.ext_tree.insert("", "end", iid=f"EXT::{ext}",
                                  values=(mark, label, fmt_size(total_size), count), tags=tags)
        self.ext_counter_lbl.config(text=f"{len(self.S.selected_exts)} sel.")
        for cid, heading in (("ext", "Extensão"), ("size", "Tamanho"), ("count", "Arquivos")):
            arrow = ""
            if col == cid:
                arrow = " ▲" if self.S.ext_sort["dir"] == "asc" else " ▼"
            self.ext_tree.heading(cid, text=heading + arrow)

    def _on_ext_click(self, event):
        iid = self.ext_tree.identify_row(event.y)
        if not iid or not iid.startswith("EXT::"):
            return
        ext = iid[5:]
        if ext in self.S.selected_exts:
            self.S.selected_exts.discard(ext)
        else:
            self.S.selected_exts.add(ext)
        self.render_ext_list()

    def select_all_ext(self):
        self.S.selected_exts = set(self.S.all_exts)
        self.render_ext_list()

    def deselect_all_ext(self):
        self.S.selected_exts.clear()
        self.render_ext_list()

    # --------------------------------------------------------
    # RENDER: ARQUIVOS
    # --------------------------------------------------------
    def render_file_list(self):
        q = self.file_search_var.get().lower()
        metas = self.S.all_meta
        filtered = [m for m in metas if q in m["rel_path"].lower()] if q else metas
        self.file_tree.delete(*self.file_tree.get_children())
        for m in filtered:
            sel = m["rel_path"] in self.S.selected_files
            mark = "☑" if sel else "☐"
            parts = m["rel_path"].split("/")
            dirpart = "/".join(parts[:-1])
            name_label = m["name"] + (" (binário)" if m["is_binary"] else "")
            tags = ("binfile",) if m["is_binary"] else ()
            self.file_tree.insert("", "end", iid=m["rel_path"],
                                   values=(mark, name_label, dirpart, f"{m['size']/1024:.0f}KB"), tags=tags)
        self.file_counter_lbl.config(text=f"{len(filtered)} vis. / {len(self.S.selected_files)} sel.")

    def _on_file_click(self, event):
        iid = self.file_tree.identify_row(event.y)
        if not iid:
            return
        if iid in self.S.selected_files:
            self.S.selected_files.discard(iid)
        else:
            self.S.selected_files.add(iid)
        self.render_file_list()
        self.update_counter()

    def select_all_files(self):
        for m in self.S.all_meta:
            self.S.selected_files.add(m["rel_path"])
        self.render_file_list()
        self.update_counter()

    def deselect_all_files(self):
        for m in self.S.all_meta:
            self.S.selected_files.discard(m["rel_path"])
        self.render_file_list()
        self.update_counter()

    # --------------------------------------------------------
    # BUSCAR NOME
    # --------------------------------------------------------
    def do_search(self):
        raw = self.search_text.get("1.0", "end").strip()
        if not raw:
            self.S.search_results = [m["rel_path"] for m in self.S.all_meta]
            self.render_search_list()
            return
        terms = re.split(r"[\s,\n]+", raw)
        cleaned = []
        for t in terms:
            if not t:
                continue
            t = re.sub(r"^(modified:|new file:|deleted:|renamed:)\s*", "", t, flags=re.IGNORECASE).strip()
            if "->" in t:
                t = t.split("->")[-1].strip()
            if t:
                cleaned.append(t)
        found = set()
        for m in self.S.all_meta:
            rp = m["rel_path"].replace("\\", "/")
            no_ext = re.sub(r"\.[^.]+$", "", m["name"])
            for term in cleaned:
                tl = term.lower().replace("\\", "/")
                if "/" in tl:
                    if rp.lower().endswith(tl):
                        found.add(m["rel_path"])
                        break
                else:
                    if m["name"].lower() == tl or no_ext.lower() == tl:
                        found.add(m["rel_path"])
                        break
        self.S.search_results = list(found)
        self.render_search_list()
        if not found:
            self.toast("Nenhum arquivo encontrado.", "warn")
        else:
            self.log(f"✓ {len(found)} arquivo(s) encontrado(s).", "ok")

    def render_search_list(self):
        self.search_tree.delete(*self.search_tree.get_children())
        meta_by_rp = {m["rel_path"]: m for m in self.S.all_meta}
        for rp in self.S.search_results:
            sel = rp in self.S.selected_files
            mark = "☑" if sel else "☐"
            m = meta_by_rp.get(rp, {})
            label = rp + (" (binário)" if m.get("is_binary") else "")
            tags = ("binfile",) if m.get("is_binary") else ()
            self.search_tree.insert("", "end", iid=rp, values=(mark, label), tags=tags)

    def _on_search_click(self, event):
        iid = self.search_tree.identify_row(event.y)
        if not iid:
            return
        if iid in self.S.selected_files:
            self.S.selected_files.discard(iid)
        else:
            self.S.selected_files.add(iid)
        self.render_search_list()
        self.update_counter()

    def select_all_search(self):
        for rp in self.S.search_results:
            self.S.selected_files.add(rp)
        self.render_search_list()
        self.update_counter()

    def deselect_all_search(self):
        for rp in self.S.search_results:
            self.S.selected_files.discard(rp)
        self.render_search_list()
        self.update_counter()

    # --------------------------------------------------------
    # EXPLORADOR (árvore)
    # --------------------------------------------------------
    def _build_tree_data(self, metas):
        root = {"ch": {}, "files": []}
        for m in metas:
            parts = m["rel_path"].split("/")
            node = root
            for p in parts[:-1]:
                node = node["ch"].setdefault(p, {"ch": {}, "files": []})
            node["files"].append(m)
        return root

    def _collect_files(self, node):
        out = list(node["files"])
        for child in node["ch"].values():
            out.extend(self._collect_files(child))
        return out

    def build_explorer_tree(self):
        self.tree_explorer.delete(*self.tree_explorer.get_children())
        self.explorer_dir_files = {}
        if not self.S.all_meta:
            self.tree_explorer.insert("", "end", iid="EMPTY", text="Selecione uma pasta de entrada.")
            return
        root = self._build_tree_data(self.S.all_meta)
        self._insert_tree_node("", root, [], self.natural())

    def _insert_tree_node(self, parent_iid, node, path_prefix, natural):
        dirs = sort_strings(list(node["ch"].keys()), natural)
        for dk in dirs:
            if should_ignore_global(dk, self.S.ignore_patterns):
                continue
            child = node["ch"][dk]
            dir_path = path_prefix + [dk]
            dir_iid = "DIR::" + "/".join(dir_path)
            all_files = self._collect_files(child)
            self.explorer_dir_files[dir_iid] = [f["rel_path"] for f in all_files]
            sel_c = sum(1 for fmeta in all_files if fmeta["rel_path"] in self.S.selected_files)
            total = len(all_files)
            icon = "☐" if sel_c == 0 else ("☑" if sel_c == total else "⊟")
            self.tree_explorer.insert(parent_iid, "end", iid=dir_iid,
                                       text=f"{icon} 📁 {dk}", open=False)
            self._insert_tree_node(dir_iid, child, dir_path, natural)
        files_sorted = sort_by(node["files"], lambda m: m["name"], natural)
        for m in files_sorted:
            if should_ignore_global(m["name"], self.S.ignore_patterns):
                continue
            checked = m["rel_path"] in self.S.selected_files
            icon = "☑" if checked else "☐"
            badge = " (binário)" if m["is_binary"] else ""
            self.tree_explorer.insert(parent_iid, "end", iid=m["rel_path"],
                                       text=f"{icon} {m['name']}{badge}")

    def _on_explorer_click(self, event):
        iid = self.tree_explorer.identify_row(event.y)
        if not iid or iid == "EMPTY":
            return
        if iid.startswith("DIR::"):
            files = self.explorer_dir_files.get(iid, [])
            all_sel = bool(files) and all(fp in self.S.selected_files for fp in files)
            for fp in files:
                if all_sel:
                    self.S.selected_files.discard(fp)
                else:
                    self.S.selected_files.add(fp)
            self.log(f"Pasta {'desmarcada' if all_sel else 'marcada'}: {iid.split('/')[-1]}")
        else:
            if iid in self.S.selected_files:
                self.S.selected_files.discard(iid)
            else:
                self.S.selected_files.add(iid)
        self._rebuild_explorer_preserving_open()
        self.update_counter()

    def _rebuild_explorer_preserving_open(self):
        open_set = set()

        def walk(iid):
            for c in self.tree_explorer.get_children(iid):
                if c.startswith("DIR::") and self.tree_explorer.item(c, "open"):
                    open_set.add(c)
                walk(c)

        walk("")
        self.build_explorer_tree()
        for d in open_set:
            if self.tree_explorer.exists(d):
                self.tree_explorer.item(d, open=True)

    def expand_all_tree(self):
        def walk(iid):
            for c in self.tree_explorer.get_children(iid):
                self.tree_explorer.item(c, open=True)
                walk(c)
        walk("")

    def collapse_all_tree(self):
        def walk(iid):
            for c in self.tree_explorer.get_children(iid):
                self.tree_explorer.item(c, open=False)
                walk(c)
        walk("")

    # --------------------------------------------------------
    # AVULSOS
    # --------------------------------------------------------
    def pick_arb_files(self):
        paths = filedialog.askopenfilenames(title="Adicionar arquivos avulsos")
        if not paths:
            return
        added = 0
        for p in paths:
            name = os.path.basename(p)
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            if any(a["name"] == name and a["size"] == size for a in self.S.arb_files):
                continue
            binf = is_bin_ext(name)
            content = None
            if not binf:
                try:
                    with open(p, "rb") as fh:
                        content = fh.read().decode("utf-8", errors="replace")
                except Exception:
                    content = None
            self.S.arb_files.append({"name": name, "content": content, "size": size,
                                      "is_binary": binf, "checked": True})
            added += 1
        self.render_arb_list()
        self.log(f"{added} arquivo(s) avulso(s) adicionado(s).", "ok")

    def render_arb_list(self):
        self.arb_tree.delete(*self.arb_tree.get_children())
        for i, f in enumerate(self.S.arb_files):
            mark = "☑" if f["checked"] else "☐"
            label = f["name"] + (" (binário)" if f["is_binary"] else "")
            tags = ("binfile",) if f["is_binary"] else ()
            self.arb_tree.insert("", "end", iid=f"ARB::{i}",
                                  values=(mark, label, f"{f['size']/1024:.1f}KB"), tags=tags)

    def _on_arb_click(self, event):
        iid = self.arb_tree.identify_row(event.y)
        if not iid or not iid.startswith("ARB::"):
            return
        idx = int(iid[5:])
        self.S.arb_files[idx]["checked"] = not self.S.arb_files[idx]["checked"]
        self.render_arb_list()

    def remove_checked_arb(self):
        keep = [f for f in self.S.arb_files if not f["checked"]]
        removed = len(self.S.arb_files) - len(keep)
        self.S.arb_files = keep
        self.render_arb_list()
        self.log(f"{removed} removido(s).", "ok")

    def clear_arb(self):
        self.S.arb_files = []
        self.render_arb_list()
        self.log("Lista avulsa limpa.", "ok")

    # --------------------------------------------------------
    # GITIGNORE
    # --------------------------------------------------------
    def toggle_gi(self):
        self.S.apply_gi = self.gi_apply_var.get()
        self.log(f"Gitignore {'ativado' if self.S.apply_gi else 'desativado'}.", "info")

    def render_gi_rules(self):
        self.gi_listbox.delete(0, "end")
        all_rules = list(self.S.gi_file_rules) + [f"[manual] {r}" for r in self.S.gi_manual_rules]
        for i, r in enumerate(all_rules):
            self.gi_listbox.insert("end", r)
            if r.startswith("[manual]"):
                self.gi_listbox.itemconfig(i, foreground="#7c3aed")
        if 0 <= self.S.gi_sel_index < len(all_rules):
            self.gi_listbox.selection_set(self.S.gi_sel_index)

    def _on_gi_select(self, event):
        sel = self.gi_listbox.curselection()
        self.S.gi_sel_index = sel[0] if sel else -1

    def add_gi_rule(self):
        v = self.gi_input_var.get().strip()
        if not v or v in self.S.gi_manual_rules:
            self.toast("Regra já existe ou vazia.", "warn")
            return
        self.S.gi_manual_rules.append(v)
        self.gi_input_var.set("")
        self.render_gi_rules()
        self.log(f"Regra adicionada: {v}", "ok")
        self.refresh_gi_preview()

    def remove_gi_rule(self):
        idx = self.S.gi_sel_index
        if idx < 0:
            return
        fl = len(self.S.gi_file_rules)
        if idx < fl:
            self.toast("Apenas regras manuais podem ser removidas.", "warn")
            return
        r = self.S.gi_manual_rules.pop(idx - fl)
        self.S.gi_sel_index = -1
        self.render_gi_rules()
        self.log(f"Regra removida: {r}", "ok")
        self.refresh_gi_preview()

    def refresh_gi_preview(self):
        self.gi_preview_list.delete(0, "end")
        if not self.S.all_meta:
            self.toast("Carregue os arquivos primeiro.", "warn")
            return
        rules = self.S.gi_file_rules + self.S.gi_manual_rules
        preview = self.S.all_meta[:400]
        for m in preview:
            ign = gi_matches(m["rel_path"], rules, True)  # preview sempre mostra o efeito das regras
            mark = "🚫" if ign else "✅"
            label = f"{mark} {m['rel_path']}" + (" (binário)" if m["is_binary"] else "")
            idx = self.gi_preview_list.size()
            self.gi_preview_list.insert("end", label)
            self.gi_preview_list.itemconfig(idx, foreground="#dc2626" if ign else "#16a34a")
        self.log(f"Preview: {len(preview)} item(s).", "ok")

    # --------------------------------------------------------
    # CÓPIA PRINCIPAL
    # --------------------------------------------------------
    def start_copy(self):
        tab = self.S.active_tab
        src = self.src_label_var.get() or "Entrada"
        out_name = self.out_name_var.get().strip() or "codigo_completo.txt"
        rules = self.S.gi_file_rules + self.S.gi_manual_rules

        metas = []
        if tab == "ext":
            if not self.S.selected_exts:
                self.toast("Selecione ao menos uma extensão.", "warn")
                return
            metas = [m for m in self.S.all_meta if m["ext"] in self.S.selected_exts
                      and not gi_matches(m["rel_path"], rules, self.S.apply_gi) and not m["is_binary"]]
        elif tab in ("files", "search", "explorer"):
            metas = [m for m in self.S.all_meta if m["rel_path"] in self.S.selected_files
                      and not gi_matches(m["rel_path"], rules, self.S.apply_gi) and not m["is_binary"]]
        elif tab == "arb":
            checked = [f for f in self.S.arb_files if f["checked"]]
            if not checked:
                self.toast("Nenhum avulso selecionado.", "warn")
                return
            self._gen_arbitrary_output(checked, out_name)
            return
        elif tab == "gi":
            if not self.S.all_meta:
                self.toast("Carregue os arquivos primeiro.", "warn")
                return
            metas = [m for m in self.S.all_meta
                      if not gi_matches(m["rel_path"], rules, self.S.apply_gi)
                      and not should_ignore_global(m["name"], self.S.ignore_patterns)
                      and not m["is_binary"]]

        if not metas:
            self.toast("Nenhum arquivo para copiar.", "warn")
            return

        total_size = sum(m["size"] for m in metas)
        if total_size > 10 * 1024 * 1024:
            if not messagebox.askyesno(
                    "Aviso de tamanho",
                    f"⚠ Estimativa: {total_size/1024/1024:.1f} MB. Continuar?"):
                return

        self._gen_output(metas, src, out_name)

    def _gen_output(self, metas, src_dir, out_name):
        self.log(f"Gerando output: {len(metas)} arquivo(s)…", "info")
        self.btn_start.config(state="disabled")
        self.set_progress(0, len(metas), "Lendo arquivos…")

        filters = []
        if self.S.ignore_patterns:
            filters.append("padrões globais")
        if self.S.apply_gi:
            filters.append(".gitignore")
        cancel_event = self.S.cancel_event

        def progress_cb(done, total):
            self.queue.put(("gen_progress", done, total))

        def worker():
            try:
                out, copied, skipped = generate_output(metas, src_dir, filters, progress_cb, cancel_event)
                self.queue.put(("gen_done", out, copied, skipped, out_name))
            except Exception as exc:
                self.queue.put(("gen_error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _gen_arbitrary_output(self, files, out_name):
        self.log(f"Unindo {len(files)} avulso(s)…", "info")
        out, n = generate_arbitrary_output(files)
        self.S.last_output = out
        self.S.last_output_name = out_name
        self.toast(f"✓ {n} avulso(s) prontos!", "ok")
        self.show_output_modal(out, out_name, n, len(out))

    def _on_gen_done(self, out, copied, skipped, out_name):
        self.S.last_output = out
        self.S.last_output_name = out_name
        self.set_progress(None)
        self.btn_start.config(state="normal")
        self.log(f"✓ {copied} arquivo(s) gerado(s). {skipped} ignorado(s).", "ok")
        self.toast(f"✓ {copied} arquivo(s) prontos!", "ok")
        self.show_output_modal(out, out_name, copied, len(out))
        self.update_counter()

    # --------------------------------------------------------
    # MODAL DE SAÍDA
    # --------------------------------------------------------
    def show_output_modal(self, content, filename, count, chars):
        top = tk.Toplevel(self)
        top.title(f"📄 {filename}")
        top.geometry("800x600")
        top.transient(self)

        head = ttk.Frame(top)
        head.pack(fill="x", padx=8, pady=6)
        ttk.Label(head, text=f"📄 {filename}", font=("Segoe UI", 11, "bold")).pack(side="left")
        stats = ttk.Label(head, text=f"{count} arq. | {chars:,} chars | ~{estimate_tokens(chars):,} tokens"
                           .replace(",", "."))
        stats.pack(side="right")

        body = tk.Text(top, wrap="none")
        body.insert("1.0", content)
        body.config(state="disabled")
        vsb = ttk.Scrollbar(top, orient="vertical", command=body.yview)
        hsb = ttk.Scrollbar(top, orient="horizontal", command=body.xview)
        body.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        body.pack(side="top", fill="both", expand=True, padx=(8, 0))
        vsb.pack(side="right", fill="y")
        hsb.pack(fill="x", padx=8)

        foot = ttk.Frame(top)
        foot.pack(fill="x", padx=8, pady=6)
        ttk.Button(foot, text="📋 Copiar tudo", command=lambda: self.copy_text(content)).pack(side="left", padx=2)
        ttk.Button(foot, text="⬇ Baixar .txt",
                   command=lambda: self._download_output(content, filename)).pack(side="left", padx=2)
        ttk.Button(foot, text="Fechar", command=top.destroy).pack(side="right", padx=2)

    def _download_output(self, content, filename):
        path = filedialog.asksaveasfilename(initialfile=filename, defaultextension=".txt",
                                             filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.toast("Download concluído!", "ok")
            self.log(f"Download: {path}", "ok")
        except Exception as exc:
            self.toast("Falha ao salvar o arquivo.", "err")
            self.log(f"[ERRO] {exc}", "err")

    # --------------------------------------------------------
    # ÁREA DE TRANSFERÊNCIA
    # --------------------------------------------------------
    def clipboard_copy(self):
        if not self.S.last_output:
            self.toast("Execute a cópia primeiro.", "warn")
            return
        self.copy_text(self.S.last_output)

    def copy_text(self, txt):
        try:
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.update()
            self.toast(f"✓ Copiado ({len(txt):,} chars)".replace(",", "."), "ok")
            self.log(f"Copiado: {len(txt):,} caracteres.".replace(",", "."), "ok")
        except Exception as exc:
            self.toast("Falha ao copiar.", "err")
            self.log(f"[ERRO] {exc}", "err")

    # --------------------------------------------------------
    # LIMPAR TUDO
    # --------------------------------------------------------
    def clear_all(self):
        self.S.cancel_event.set()
        self.S = State()
        self.S.theme = THEMES and self.S.theme  # mantém padrão
        self.src_label_var.set("")
        self.out_name_var.set("codigo_completo.txt")
        self.ext_search_var.set("")
        self.file_search_var.set("")
        self.search_text.delete("1.0", "end")
        self.gi_input_var.set("")
        self.gi_apply_var.set(False)

        self.ext_tree.delete(*self.ext_tree.get_children())
        self.file_tree.delete(*self.file_tree.get_children())
        self.search_tree.delete(*self.search_tree.get_children())
        self.arb_tree.delete(*self.arb_tree.get_children())
        self.gi_listbox.delete(0, "end")
        self.gi_preview_list.delete(0, "end")
        self.tree_explorer.delete(*self.tree_explorer.get_children())
        self.tree_explorer.insert("", "end", iid="EMPTY", text="Selecione uma pasta de entrada.")
        self.gi_status_lbl.config(text="⚠ Nenhum diretório selecionado.")

        self._load_config()
        self._update_ignore_summary()
        self.update_counter()
        self.set_status("Pronto", "v2.1 — Python Edition")
        self.log("✓ Tudo limpo.", "ok")
        self.toast("Limpo!", "ok")
        self.set_progress(None)

    # --------------------------------------------------------
    # PADRÕES GLOBAIS (modal)
    # --------------------------------------------------------
    def _update_ignore_summary(self):
        self.ignore_summary_lbl.config(
            text=f"{len(self.S.ignore_patterns)}/{len(ALL_IGNORE_PATTERNS)} padrões ativos")

    def open_ignore_modal(self):
        top = tk.Toplevel(self)
        top.title("Padrões globais a ignorar")
        top.geometry("520x520")
        top.transient(self)

        head = ttk.Frame(top)
        head.pack(fill="x", padx=8, pady=6)
        ttk.Label(head, text="Padrões globais a ignorar", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(head, text="Itens marcados não serão incluídos na cópia").pack(anchor="w")

        toolbar = ttk.Frame(top)
        toolbar.pack(fill="x", padx=8, pady=4)
        count_lbl = ttk.Label(toolbar, text="")
        count_lbl.pack(side="right")

        canvas = tk.Canvas(top, highlightthickness=0)
        scroll = ttk.Scrollbar(top, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
        scroll.pack(side="left", fill="y", pady=4)

        active = set(self.S.ignore_patterns)
        check_vars = {}

        def refresh_count():
            count_lbl.config(text=f"{len(active)}/{len(ALL_IGNORE_PATTERNS)} ativos")

        def apply_change():
            self.S.ignore_patterns = [p for p in ALL_IGNORE_PATTERNS if p in active]
            self._save_config()
            self._update_ignore_summary()
            self._apply_after_pattern_change()
            refresh_count()

        def toggle_group(patterns):
            all_on = all(p in active for p in patterns)
            for p in patterns:
                if all_on:
                    active.discard(p)
                else:
                    active.add(p)
            for p in patterns:
                check_vars[p].set(p in active)
            apply_change()

        for group in PATTERN_GROUPS:
            gframe = ttk.LabelFrame(body, text=group["label"])
            gframe.pack(fill="x", padx=4, pady=4)
            patterns = [p for p, _ in group["patterns"]]
            ttk.Button(gframe, text="marcar/desmarcar grupo",
                       command=lambda ps=patterns: toggle_group(ps)).pack(anchor="e", padx=4, pady=2)
            for pattern, desc in group["patterns"]:
                var = tk.BooleanVar(value=pattern in active)
                check_vars[pattern] = var

                def on_toggle(p=pattern, v=var):
                    if v.get():
                        active.add(p)
                    else:
                        active.discard(p)
                    apply_change()

                cb = ttk.Checkbutton(gframe, text=f"{pattern}  —  {desc}", variable=var, command=on_toggle)
                cb.pack(anchor="w", padx=12, pady=1)

        refresh_count()

        toolbar_left = ttk.Frame(toolbar)
        toolbar_left.pack(side="left")

        def mark_all(on):
            for p in ALL_IGNORE_PATTERNS:
                if on:
                    active.add(p)
                else:
                    active.discard(p)
                check_vars[p].set(on)
            apply_change()

        ttk.Button(toolbar_left, text="Marcar tudo", command=lambda: mark_all(True)).pack(side="left", padx=2)
        ttk.Button(toolbar_left, text="Desmarcar tudo", command=lambda: mark_all(False)).pack(side="left", padx=2)

        foot = ttk.Frame(top)
        foot.pack(fill="x", padx=8, pady=6)
        ttk.Button(foot, text="Concluído", command=top.destroy).pack(side="right")

    def _apply_after_pattern_change(self):
        self.S.selected_files = {rp for rp in self.S.selected_files
                                  if not any(should_ignore_global(part, self.S.ignore_patterns)
                                             for part in rp.split("/"))}
        self.render_ext_list()
        self.render_file_list()
        self.render_search_list()
        self.build_explorer_tree()
        self.update_counter()


# ============================================================
# PONTO DE ENTRADA
# ============================================================
def main():
    app = CopiadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

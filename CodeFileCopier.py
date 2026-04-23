# CodeFileCopier.py
# Versão 2.0 - Implementação completa com todas as melhorias
# Compatível com Python 3.8+ e wxPython 4.2+
# Dependências opcionais: pathspec (para .gitignore avançado)
#
# Melhorias implementadas:
# - Correção: arquivos sem extensão (_get_ext_label)
# - Nova aba: Conformidade .gitignore
# - Thread de varredura (UI não congela)
# - Detecção de binários
# - Fallback de encoding robusto (utf-8 -> latin-1 -> cp1252)
# - Cabeçalho de metadados no output
# - Contador de seleção em tempo real
# - Barra de progresso (wx.Gauge)
# - Botão copiar para clipboard
# - Fonte monoespaçada no log
# - Padrões de exclusão globais (IGNORE_PATTERNS)
# - Persistência de configuração (config.json)
# - Botões reorganizados horizontalmente

import wx
import os
import re
import threading
import json
import datetime
import fnmatch

# Tentar importar pathspec para suporte avançado a .gitignore
try:
    import pathspec
    HAS_PATHSPEC = True
except ImportError:
    HAS_PATHSPEC = False

# ---------------------------------------------------------------------------
# CONSTANTES GLOBAIS
# ---------------------------------------------------------------------------

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Padrões de exclusão globais aplicados durante a varredura
IGNORE_PATTERNS = [
    ".git", "__pycache__", "node_modules", "venv", ".venv",
    "env", ".env", "dist", "build", ".tox", ".mypy_cache",
    ".pytest_cache", "*.log", "*.pyc", "*.pyo", "*.egg-info",
    ".DS_Store", "Thumbs.db"
]

# Encodings tentados em sequência para leitura de arquivos
ENCODINGS_TO_TRY = ["utf-8", "latin-1", "cp1252"]


# ---------------------------------------------------------------------------
# FUNÇÕES UTILITÁRIAS GLOBAIS
# ---------------------------------------------------------------------------

def natural_sort_key(s):
    """Retorna chave para ordenação natural (ex: 'item2' antes de 'item10')."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def _get_ext_label(filename):
    """
    Retorna a extensão real do arquivo ou '(sem extensão)' para arquivos
    como .gitignore, Makefile, README, etc.
    Correção crítica: os.path.splitext retorna '' para esses casos.
    """
    _, ext = os.path.splitext(filename)
    if ext:
        return ext
    # Arquivo sem extensão (ex: Makefile) ou com nome iniciando por ponto (ex: .gitignore)
    if filename.startswith('.') and '.' not in filename[1:]:
        return filename  # ex: '.gitignore' -> label '.gitignore'
    return "(sem extensão)"


def _read_file_with_fallback(filepath):
    """
    Tenta ler o arquivo com encodings em sequência.
    Retorna (conteúdo, encoding_usado) ou (None, None) se binário/erro.
    """
    # Verificar se é binário lendo os primeiros 1024 bytes
    try:
        with open(filepath, "rb") as f:
            raw = f.read(1024)
        if b'\x00' in raw:
            return None, "binário"
    except OSError:
        return None, "erro_io"

    # Tentar encodings em sequência
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            return content, enc
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            return None, f"erro_io: {e}"

    return None, "encoding_falhou"


def _should_ignore(name, is_dir=False):
    """Verifica se um item deve ser ignorado pelos padrões globais."""
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
        if is_dir and name == pattern:
            return True
    return False


# ---------------------------------------------------------------------------
# CLASSES DE ÁRVORE (OUTPUT)
# ---------------------------------------------------------------------------

class TreeNode:
    """Representa nós da árvore para saída de texto."""

    def __init__(self, name, full_path=None):
        self.name = name
        self.full_path = full_path
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def print_tree(self, level=0, is_last_child=False, parent_prefix=""):
        prefix = parent_prefix
        if level > 0:
            prefix += "  " if is_last_child else "| "
        tree_str = parent_prefix + ("`-- " if is_last_child else "|-- ") + f"{self.name}\n"
        sorted_children = sorted(self.children, key=lambda c: natural_sort_key(c.name))
        num = len(sorted_children)
        for i, child in enumerate(sorted_children):
            tree_str += child.print_tree(level + 1, i == num - 1, prefix)
        return tree_str

    def print_flat_list(self):
        return "".join(f"- {child.name}\n" for child in self.children)


# ---------------------------------------------------------------------------
# DRAG AND DROP
# ---------------------------------------------------------------------------

class DirectoryDropTarget(wx.FileDropTarget):
    def __init__(self, dir_picker, update_callback):
        super().__init__()
        self.dir_picker = dir_picker
        self.update_callback = update_callback

    def OnDropFiles(self, x, y, filenames):
        if filenames and os.path.isdir(filenames[0]):
            self.dir_picker.SetPath(filenames[0])
            if self.update_callback:
                self.update_callback(None)
        return True


class FileListDropTarget(wx.FileDropTarget):
    def __init__(self, list_control, add_files_callback):
        super().__init__()
        self.list_control = list_control
        self.add_files_callback = add_files_callback

    def OnDropFiles(self, x, y, filenames):
        files = [f for f in filenames if os.path.isfile(f)]
        if files:
            self.add_files_callback(files)
        return True


# ---------------------------------------------------------------------------
# PARSER DE .GITIGNORE
# ---------------------------------------------------------------------------

class GitignoreParser:
    """
    Parser robusto de regras .gitignore.
    Suporta: comentários, negações (!), curingas (*, ?, [a-z]),
    diretórios (/), recursividade (**).
    Usa pathspec se disponível, caso contrário implementação própria.
    """

    def __init__(self, gitignore_path, root_dir):
        self.gitignore_path = gitignore_path
        self.root_dir = root_dir
        self.rules = []          # lista de (negated, pattern_str) para fallback
        self.spec = None         # pathspec.PathSpec se disponível
        self._parse()

    def _parse(self):
        """Lê e parseia o arquivo .gitignore."""
        if not os.path.isfile(self.gitignore_path):
            return

        try:
            with open(self.gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            return

        patterns = []
        for line in lines:
            line = line.rstrip('\n').rstrip('\r')
            # Ignorar comentários e linhas vazias
            if not line.strip() or line.strip().startswith('#'):
                continue
            patterns.append(line)
            negated = line.startswith('!')
            pattern = line[1:] if negated else line
            self.rules.append((negated, pattern.strip()))

        if HAS_PATHSPEC:
            try:
                self.spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
            except Exception:
                self.spec = None

    def is_ignored(self, rel_path):
        """
        Verifica se um caminho relativo à raiz deve ser ignorado.
        rel_path deve usar separadores '/' (Unix-style).
        """
        rel_path = rel_path.replace(os.sep, '/')

        if HAS_PATHSPEC and self.spec:
            return self.spec.match_file(rel_path)

        # Implementação própria com fnmatch
        ignored = False
        for negated, pattern in self.rules:
            # Normalizar pattern
            p = pattern.lstrip('/')
            matched = False

            if '/' in p.replace('**/', ''):
                # Pattern com diretório: match no caminho completo
                matched = fnmatch.fnmatch(rel_path, p) or fnmatch.fnmatch(rel_path, f"**/{p}")
            else:
                # Pattern simples: match no nome do arquivo ou qualquer parte do caminho
                basename = rel_path.split('/')[-1]
                matched = fnmatch.fnmatch(basename, p) or fnmatch.fnmatch(rel_path, f"**/{p}")

            if matched:
                ignored = not negated

        return ignored

    def get_rules_list(self):
        """Retorna lista de strings das regras para exibição."""
        if not os.path.isfile(self.gitignore_path):
            return []
        try:
            with open(self.gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                return [l.rstrip() for l in f.readlines()]
        except OSError:
            return []


# ---------------------------------------------------------------------------
# APLICAÇÃO PRINCIPAL
# ---------------------------------------------------------------------------

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame()
        self.frame.Show()
        return True


class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Copiador de Código Avançado v2.0")

        # --- Estado interno ---
        self.all_extensions = []
        self.all_files = []
        self.selected_extensions = set()
        self.selected_files = set()
        self.arbitrary_files_for_union = []
        self.source_dir_last_path = None
        self._scan_thread = None
        self._gitignore_parser = None
        self._gitignore_cache_path = None
        self._last_output_path = None
        self._apply_gitignore = False

        # --- Imagens da árvore ---
        self.IMG_UNCHECKED = 0
        self.IMG_CHECKED = 1
        self.IMG_PARTIAL = 2
        self.file_tree_img_list = wx.ImageList(16, 16)
        self.file_tree_img_list.Add(self._create_checkbox_bitmap(False))
        self.file_tree_img_list.Add(self._create_checkbox_bitmap(True))
        self.file_tree_img_list.Add(self._create_checkbox_bitmap(None))

        # --- Construção da UI ---
        self._build_ui()

        # --- Status Bar ---
        self.CreateStatusBar(2)
        self.SetStatusWidths([-1, 200])
        self.SetStatusText("Pronto", 0)
        self.SetStatusText("0 arquivos | 0 linhas", 1)

        # --- Carregar configuração ---
        self._load_config()

        # --- Acelerador ESC ---
        esc_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_esc_pressed, id=esc_id)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, esc_id)
        ]))

        self.Bind(wx.EVT_CLOSE, self._on_close)

    # -----------------------------------------------------------------------
    # CONSTRUÇÃO DA UI
    # -----------------------------------------------------------------------

    def _build_ui(self):
        panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Diretórios ---
        dir_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dir_input_sizer.Add(wx.StaticText(panel, label="Entrada:"), 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.source_dir_picker = wx.DirPickerCtrl(
            panel, message="Selecione o diretório de Entrada")
        self.source_dir_picker.Bind(wx.EVT_DIRPICKER_CHANGED, self.on_source_dir_changed)
        dir_input_sizer.Add(self.source_dir_picker, 1, wx.ALL | wx.EXPAND, 5)
        self.main_sizer.Add(dir_input_sizer, 0, wx.EXPAND | wx.ALL, 5)

        dir_output_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dir_output_sizer.Add(wx.StaticText(panel, label="Saída:"), 0,
                              wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.output_dir_picker = wx.DirPickerCtrl(
            panel, message="Selecione o diretório de Saída")
        dir_output_sizer.Add(self.output_dir_picker, 1, wx.ALL | wx.EXPAND, 5)
        self.main_sizer.Add(dir_output_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Opções de ordenação e exclusão ---
        opts_sizer = wx.BoxSizer(wx.HORIZONTAL)
        opts_sizer.Add(wx.StaticText(panel, label="Ordem:"), 0,
                       wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.sort_choice = wx.Choice(panel, choices=[
            "Ordenação Natural (Padrão)", "Ordenação Alfabética"])
        self.sort_choice.SetSelection(0)
        opts_sizer.Add(self.sort_choice, 1, wx.ALL | wx.EXPAND, 5)

        self.ignore_patterns_cb = wx.CheckBox(panel, label="Aplicar padrões de exclusão globais")
        self.ignore_patterns_cb.SetValue(True)
        self.ignore_patterns_cb.SetToolTip(
            "Exclui: " + ", ".join(IGNORE_PATTERNS[:8]) + "...")
        opts_sizer.Add(self.ignore_patterns_cb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.main_sizer.Add(opts_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Notebook ---
        self.notebook = wx.Notebook(panel)
        self.main_sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)

        # Aba 1: Extensões
        self.extension_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.extension_panel, "Selecionar Extensões")
        self.setup_extension_panel()

        # Aba 2: Arquivos
        self.file_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.file_panel, "Selecionar Arquivos")
        self.setup_file_panel()

        # Aba 3: Buscar por Nome
        self.text_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.text_panel, "Buscar por Nome")
        self.setup_text_panel()

        # Aba 4: Explorador
        self.tree_explorer_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.tree_explorer_panel, "Explorador de Arquivos")
        self.setup_tree_explorer_panel()

        # Aba 5: Unir Avulsos
        self.random_union_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.random_union_panel, "Unir Arquivos Avulsos")
        self.setup_random_union_panel()

        # Aba 6: .gitignore
        self.gitignore_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.gitignore_panel, "Conformidade .gitignore")
        self.setup_gitignore_panel()

        # --- Contador de seleção ---
        self.selection_label = wx.StaticText(
            panel, label="0 arquivos selecionados | ~0 linhas estimadas")
        font_mono = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL)
        self.selection_label.SetFont(font_mono)
        self.main_sizer.Add(self.selection_label, 0, wx.ALL | wx.EXPAND, 5)

        # --- Barra de progresso ---
        self.progress_gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
        self.progress_gauge.Hide()
        self.main_sizer.Add(self.progress_gauge, 0, wx.EXPAND | wx.ALL, 5)

        # --- Botões de ação (horizontal) ---
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.copy_button = wx.Button(panel, label="▶  INICIAR CÓPIA")
        self.copy_button.SetBackgroundColour(wx.Colour(212, 237, 218))
        font_bold = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_BOLD)
        self.copy_button.SetFont(font_bold)
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.copy_button.SetToolTip("Inicia a cópia dos arquivos selecionados na aba ativa")
        action_sizer.Add(self.copy_button, 2, wx.ALL | wx.EXPAND, 5)

        self.clear_button = wx.Button(panel, label="🗑  Limpar Tudo")
        self.clear_button.Bind(wx.EVT_BUTTON, self.on_clear_all)
        action_sizer.Add(self.clear_button, 1, wx.ALL | wx.EXPAND, 5)

        self.clipboard_button = wx.Button(panel, label="📋  Copiar para Clipboard")
        self.clipboard_button.Bind(wx.EVT_BUTTON, self._on_copy_to_clipboard)
        self.clipboard_button.SetToolTip("Copia o conteúdo do último código_completo.txt gerado")
        action_sizer.Add(self.clipboard_button, 1, wx.ALL | wx.EXPAND, 5)

        self.main_sizer.Add(action_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Log (fonte monoespaçada) ---
        self.output_text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.output_text.SetFont(font_mono)
        self.main_sizer.Add(self.output_text, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.main_sizer)
        self.SetSize((800, 800))
        self.Centre()

        # Drop targets
        self.source_dir_picker.SetDropTarget(
            DirectoryDropTarget(self.source_dir_picker, self.on_source_dir_changed))
        self.output_dir_picker.SetDropTarget(
            DirectoryDropTarget(self.output_dir_picker, None))

    # -----------------------------------------------------------------------
    # SETUP DAS ABAS
    # -----------------------------------------------------------------------

    def setup_extension_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_sizer.Add(wx.StaticText(self.extension_panel, label="Pesquisar:"),
                         0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.extension_search = wx.TextCtrl(self.extension_panel)
        self.extension_search.Bind(wx.EVT_TEXT, self.filter_extensions)
        search_sizer.Add(self.extension_search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(search_sizer, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(wx.StaticText(self.extension_panel,
                                label="Selecione as extensões que deseja copiar:"),
                  0, wx.ALL, 10)
        self.extension_checklist = wx.CheckListBox(self.extension_panel, choices=[])
        self.extension_checklist.Bind(wx.EVT_CHECKLISTBOX, self.on_extension_checked)
        sizer.Add(self.extension_checklist, 1, wx.ALL | wx.EXPAND, 10)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sel = wx.Button(self.extension_panel, label="Selecionar Tudo")
        btn_des = wx.Button(self.extension_panel, label="Desmarcar Tudo")
        btn_sel.Bind(wx.EVT_BUTTON, self.select_all_extensions)
        btn_des.Bind(wx.EVT_BUTTON, self.deselect_all_extensions)
        btn_sizer.Add(btn_sel, 1, wx.ALL, 5)
        btn_sizer.Add(btn_des, 1, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.extension_panel.SetSizer(sizer)

    def setup_file_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_sizer.Add(wx.StaticText(self.file_panel, label="Pesquisar:"),
                         0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.file_search = wx.TextCtrl(self.file_panel)
        self.file_search.Bind(wx.EVT_TEXT, self.filter_files)
        search_sizer.Add(self.file_search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(search_sizer, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(wx.StaticText(self.file_panel,
                                label="Selecione os arquivos que deseja copiar:"),
                  0, wx.ALL, 10)
        self.file_list = wx.CheckListBox(self.file_panel, choices=[])
        self.file_list.Bind(wx.EVT_CHECKLISTBOX, self.on_file_checked)
        self.file_list.SetMinSize((400, 300))
        sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 10)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sel = wx.Button(self.file_panel, label="Selecionar Todos")
        btn_des = wx.Button(self.file_panel, label="Deselecionar Todos")
        btn_sel.Bind(wx.EVT_BUTTON, self.select_all_files_tab)
        btn_des.Bind(wx.EVT_BUTTON, self.deselect_all_files_tab)
        btn_sizer.Add(btn_sel, 1, wx.ALL, 5)
        btn_sizer.Add(btn_des, 1, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.file_panel.SetSizer(sizer)

    def setup_text_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self.text_panel,
                                label="Digite nomes ou caminhos (ex: saída de 'git status'):"),
                  0, wx.ALL, 10)
        self.text_input = wx.TextCtrl(self.text_panel, style=wx.TE_MULTILINE)
        self.text_input.SetMinSize((-1, 100))
        sizer.Add(self.text_input, 0, wx.EXPAND | wx.ALL, 10)
        btn_search = wx.Button(self.text_panel, label="Buscar e Selecionar na Lista Abaixo")
        btn_search.Bind(wx.EVT_BUTTON, self.on_select_from_text_input)
        sizer.Add(btn_search, 0, wx.ALL | wx.CENTER, 5)
        self.text_file_list = wx.CheckListBox(self.text_panel, choices=[])
        self.text_file_list.Bind(wx.EVT_CHECKLISTBOX, self.on_text_file_list_checked)
        self.text_file_list.SetMinSize((-1, 200))
        sizer.Add(self.text_file_list, 1, wx.EXPAND | wx.ALL, 10)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sel = wx.Button(self.text_panel, label="Selecionar Todos na Lista")
        btn_des = wx.Button(self.text_panel, label="Deselecionar Todos na Lista")
        btn_sel.Bind(wx.EVT_BUTTON, self.select_all_text_files_list)
        btn_des.Bind(wx.EVT_BUTTON, self.deselect_all_text_files_list)
        btn_sizer.Add(btn_sel, 1, wx.ALL | wx.EXPAND, 5)
        btn_sizer.Add(btn_des, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.text_panel.SetSizer(sizer)

    def setup_tree_explorer_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self.tree_explorer_panel,
                                label="Selecione arquivos/pastas (duplo clique/Enter para marcar):"),
                  0, wx.ALL, 10)
        self.file_tree = wx.TreeCtrl(
            self.tree_explorer_panel,
            style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT |
                  wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        self.file_tree.AssignImageList(self.file_tree_img_list)
        self.file_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_tree_item_checkbox_activated)
        sizer.Add(self.file_tree, 1, wx.EXPAND | wx.ALL, 10)
        self.tree_explorer_panel.SetSizer(sizer)

    def setup_random_union_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self.random_union_panel,
                                label="Adicione arquivos de qualquer local para uni-los:"),
                  0, wx.ALL, 10)
        self.random_files_checklist = wx.CheckListBox(
            self.random_union_panel, choices=[], style=wx.LB_MULTIPLE)
        self.random_files_checklist.Bind(
            wx.EVT_CHECKLISTBOX, self.on_random_file_checklist_toggled)
        sizer.Add(self.random_files_checklist, 1, wx.EXPAND | wx.ALL, 10)
        drop_target = FileListDropTarget(
            self.random_files_checklist, self.add_arbitrary_files_to_list)
        self.random_files_checklist.SetDropTarget(drop_target)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_add = wx.Button(self.random_union_panel, label="Adicionar Arquivos...")
        btn_rem = wx.Button(self.random_union_panel, label="Remover Selecionados")
        btn_clr = wx.Button(self.random_union_panel, label="Limpar Lista")
        btn_add.Bind(wx.EVT_BUTTON, self.on_add_arbitrary_files_button)
        btn_rem.Bind(wx.EVT_BUTTON, self.on_remove_selected_arbitrary_files)
        btn_clr.Bind(wx.EVT_BUTTON, self.on_clear_arbitrary_files_list)
        btn_sizer.Add(btn_add, 1, wx.ALL | wx.EXPAND, 5)
        btn_sizer.Add(btn_rem, 1, wx.ALL | wx.EXPAND, 5)
        btn_sizer.Add(btn_clr, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.random_union_panel.SetSizer(sizer)

    def setup_gitignore_panel(self):
        """
        Configura a aba de Conformidade .gitignore.
        Mostra regras detectadas e permite ativar/desativar o filtro.
        """
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Checkbox de ativação
        self.gitignore_active_cb = wx.CheckBox(
            self.gitignore_panel,
            label="Aplicar regras do .gitignore durante varredura e cópia")
        self.gitignore_active_cb.SetValue(False)
        self.gitignore_active_cb.Bind(wx.EVT_CHECKBOX, self._on_gitignore_toggle)
        sizer.Add(self.gitignore_active_cb, 0, wx.ALL, 10)

        # Status do .gitignore
        self.gitignore_status_label = wx.StaticText(
            self.gitignore_panel,
            label="⚠ Nenhum diretório de entrada selecionado.")
        sizer.Add(self.gitignore_status_label, 0, wx.ALL, 5)

        # Splitter: regras | preview de arquivos
        splitter = wx.SplitterWindow(self.gitignore_panel)

        # Painel esquerdo: regras
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(wx.StaticText(left_panel, label="Regras detectadas:"),
                       0, wx.ALL, 5)
        self.gitignore_rules_list = wx.ListBox(left_panel, style=wx.LB_SINGLE)
        left_sizer.Add(self.gitignore_rules_list, 1, wx.EXPAND | wx.ALL, 5)

        # Campo para adicionar regra manual
        add_rule_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.gitignore_rule_input = wx.TextCtrl(left_panel)
        btn_add_rule = wx.Button(left_panel, label="+ Adicionar Regra")
        btn_add_rule.Bind(wx.EVT_BUTTON, self._on_add_gitignore_rule)
        btn_rem_rule = wx.Button(left_panel, label="- Remover Selecionada")
        btn_rem_rule.Bind(wx.EVT_BUTTON, self._on_remove_gitignore_rule)
        add_rule_sizer.Add(self.gitignore_rule_input, 1, wx.ALL, 3)
        add_rule_sizer.Add(btn_add_rule, 0, wx.ALL, 3)
        add_rule_sizer.Add(btn_rem_rule, 0, wx.ALL, 3)
        left_sizer.Add(add_rule_sizer, 0, wx.EXPAND | wx.ALL, 5)
        left_panel.SetSizer(left_sizer)

        # Painel direito: preview de arquivos incluídos/ignorados
        right_panel = wx.Panel(splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer.Add(wx.StaticText(right_panel,
                                      label="Preview (✅ incluído | 🚫 ignorado):"),
                        0, wx.ALL, 5)
        self.gitignore_preview_list = wx.ListBox(right_panel, style=wx.LB_SINGLE)
        right_sizer.Add(self.gitignore_preview_list, 1, wx.EXPAND | wx.ALL, 5)

        btn_refresh = wx.Button(right_panel, label="🔄 Atualizar Preview")
        btn_refresh.Bind(wx.EVT_BUTTON, self._on_refresh_gitignore_preview)
        right_sizer.Add(btn_refresh, 0, wx.ALL | wx.CENTER, 5)
        right_panel.SetSizer(right_sizer)

        splitter.SplitVertically(left_panel, right_panel, 300)
        sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 5)

        # Aviso sobre pathspec
        if not HAS_PATHSPEC:
            hint = wx.StaticText(
                self.gitignore_panel,
                label="💡 Instale 'pathspec' (pip install pathspec) para suporte completo ao .gitignore")
            hint.SetForegroundColour(wx.Colour(150, 100, 0))
            sizer.Add(hint, 0, wx.ALL, 5)

        self.gitignore_panel.SetSizer(sizer)
        # Guarda regras manuais adicionadas (override)
        self._gitignore_manual_rules = []

    # -----------------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------------

    def get_sort_key(self):
        """Retorna a função de ordenação conforme seleção do usuário."""
        return natural_sort_key if self.sort_choice.GetSelection() == 0 else None

    def _use_ignore_patterns(self):
        """Retorna True se os padrões globais de exclusão devem ser aplicados."""
        return self.ignore_patterns_cb.GetValue()

    def _should_ignore_item(self, name, is_dir=False):
        """Verifica padrões globais de exclusão se ativados."""
        if self._use_ignore_patterns():
            return _should_ignore(name, is_dir)
        return False

    def _is_gitignored(self, filepath, source_dir):
        """Verifica se um arquivo deve ser ignorado pelo .gitignore."""
        if not self._apply_gitignore or self._gitignore_parser is None:
            return False
        try:
            rel = os.path.relpath(filepath, source_dir)
            return self._gitignore_parser.is_ignored(rel)
        except ValueError:
            return False

    def _update_selection_counter(self):
        """Atualiza o contador de seleção em tempo real."""
        count = len(self.selected_files)
        # Estimativa de linhas: média de 30 linhas por arquivo como heurística rápida
        estimated_lines = count * 30
        wx.CallAfter(self.selection_label.SetLabel,
                     f"{count} arquivo(s) selecionado(s) | ~{estimated_lines} linhas estimadas")
        wx.CallAfter(self.SetStatusText, f"{count} selecionados", 1)

    def _create_checkbox_bitmap(self, checked_state):
        """Cria bitmap 16x16 simulando checkbox."""
        bmp = wx.Bitmap(16, 16)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()
        border_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        dc.SetPen(wx.Pen(border_color, 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(2, 2, 11, 11)
        if checked_state is True:
            dc.SetPen(wx.Pen(wx.BLACK, 2))
            dc.DrawLine(4, 7, 7, 10)
            dc.DrawLine(7, 10, 11, 5)
        elif checked_state is None:
            fill_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            dc.SetBrush(wx.Brush(fill_color))
            dc.SetPen(wx.Pen(fill_color, 1))
            dc.DrawRectangle(5, 5, 5, 5)
        dc.SelectObject(wx.NullBitmap)
        bmp.SetMaskColour(wx.WHITE)
        return bmp

    # -----------------------------------------------------------------------
    # PERSISTÊNCIA DE CONFIGURAÇÃO
    # -----------------------------------------------------------------------

    def _load_config(self):
        """Carrega configuração salva de config.json."""
        if not os.path.isfile(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if "source_dir" in cfg and os.path.isdir(cfg["source_dir"]):
                self.source_dir_picker.SetPath(cfg["source_dir"])
            if "output_dir" in cfg and os.path.isdir(cfg["output_dir"]):
                self.output_dir_picker.SetPath(cfg["output_dir"])
            if "sort_selection" in cfg:
                self.sort_choice.SetSelection(cfg["sort_selection"])
            if "window_size" in cfg:
                w, h = cfg["window_size"]
                self.SetSize((w, h))
            if "window_pos" in cfg:
                x, y = cfg["window_pos"]
                self.SetPosition((x, y))
            if "apply_gitignore" in cfg:
                self.gitignore_active_cb.SetValue(cfg["apply_gitignore"])
                self._apply_gitignore = cfg["apply_gitignore"]
            if "ignore_patterns_active" in cfg:
                self.ignore_patterns_cb.SetValue(cfg["ignore_patterns_active"])
            self.output_text.AppendText("✓ Configuração carregada.\n")
        except Exception as e:
            self.output_text.AppendText(f"⚠ Erro ao carregar config: {e}\n")

    def _save_config(self):
        """Salva configuração atual em config.json."""
        try:
            cfg = {
                "source_dir": self.source_dir_picker.GetPath(),
                "output_dir": self.output_dir_picker.GetPath(),
                "sort_selection": self.sort_choice.GetSelection(),
                "window_size": list(self.GetSize()),
                "window_pos": list(self.GetPosition()),
                "apply_gitignore": self.gitignore_active_cb.GetValue(),
                "ignore_patterns_active": self.ignore_patterns_cb.GetValue(),
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            self.output_text.AppendText(f"⚠ Erro ao salvar config: {e}\n")

    def _on_close(self, event):
        self._save_config()
        event.Skip()

    # -----------------------------------------------------------------------
    # VARREDURA EM THREAD
    # -----------------------------------------------------------------------

    def on_source_dir_changed(self, event):
        current_path = self.source_dir_picker.GetPath()
        if current_path and current_path != self.source_dir_last_path:
            self.source_dir_last_path = current_path
            self._start_scan_thread(current_path)
        if event:
            event.Skip()

    def _start_scan_thread(self, source_dir):
        """Inicia varredura em thread separada para não travar a UI."""
        # Cancelar varredura anterior se ainda em andamento
        if self._scan_thread and self._scan_thread.is_alive():
            self.output_text.AppendText("⟳ Aguardando varredura anterior...\n")
            return

        self.copy_button.Disable()
        self.SetStatusText("Varrendo diretório...", 0)
        wx.CallAfter(self.progress_gauge.Show)
        wx.CallAfter(self.progress_gauge.Pulse)
        wx.CallAfter(self.main_sizer.Layout)

        self._scan_thread = threading.Thread(
            target=self._scan_worker,
            args=(source_dir,),
            daemon=True
        )
        self._scan_thread.start()

    def _scan_worker(self, source_dir):
        """
        Trabalhador de varredura executado em thread.
        Usa os.walk com filtros de padrões globais e .gitignore.
        Todas as atualizações de UI são feitas via wx.CallAfter.
        """
        extensions = set()
        files_list = []
        use_ignore = self.ignore_patterns_cb.GetValue()
        apply_gi = self._apply_gitignore and self._gitignore_parser is not None

        try:
            for root, dirs, files in os.walk(source_dir):
                # Filtrar diretórios in-place para evitar recursão desnecessária
                if use_ignore:
                    dirs[:] = [d for d in dirs if not _should_ignore(d, is_dir=True)]

                # Filtrar pelo .gitignore
                if apply_gi:
                    filtered_dirs = []
                    for d in dirs:
                        rel = os.path.relpath(os.path.join(root, d), source_dir)
                        if not self._gitignore_parser.is_ignored(rel + "/"):
                            filtered_dirs.append(d)
                    dirs[:] = filtered_dirs

                for file in files:
                    # Filtrar pelo padrão global
                    if use_ignore and _should_ignore(file):
                        continue

                    filepath = os.path.join(root, file)

                    # Filtrar pelo .gitignore
                    if apply_gi:
                        rel = os.path.relpath(filepath, source_dir)
                        if self._gitignore_parser.is_ignored(rel):
                            continue

                    # Usar _get_ext_label para capturar arquivos sem extensão
                    ext = _get_ext_label(file)
                    extensions.add(ext)
                    files_list.append(filepath)

        except Exception as e:
            wx.CallAfter(self.output_text.AppendText,
                         f"⚠ Erro durante varredura: {e}\n")

        # Ordenar resultados
        sort_key = self.get_sort_key()
        sorted_extensions = sorted(list(extensions))
        sorted_files = sorted(files_list, key=sort_key)

        # Atualizar UI na thread principal
        wx.CallAfter(self._update_ui_after_scan, sorted_extensions, sorted_files, source_dir)

    def _update_ui_after_scan(self, extensions, files_list, source_dir):
        """Atualiza toda a UI após varredura. Chamado via wx.CallAfter."""
        self.all_extensions = extensions
        self.all_files = files_list

        self.Freeze()
        try:
            self.filter_extensions(None)
            self.filter_files(None)

            if hasattr(self, 'text_file_list'):
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files)
                    self.selected_files.intersection_update(self.all_files)
                    new_checked = [i for i, p in enumerate(self.all_files)
                                   if p in self.selected_files]
                    self.text_file_list.SetCheckedItems(new_checked)
                finally:
                    self.text_file_list.Thaw()

            # Atualizar aba .gitignore
            self._refresh_gitignore_status(source_dir)
            self.populate_file_tree()

        finally:
            self.Thaw()

        self.progress_gauge.SetValue(0)
        self.progress_gauge.Hide()
        self.main_sizer.Layout()
        self.copy_button.Enable()
        self.SetStatusText(f"Varredura concluída: {len(files_list)} arquivo(s)", 0)
        self.output_text.AppendText(
            f"✓ Varredura concluída: {len(files_list)} arquivo(s), "
            f"{len(extensions)} extensão(ões) encontrada(s).\n")
        self._update_selection_counter()

    # -----------------------------------------------------------------------
    # .GITIGNORE — LÓGICA
    # -----------------------------------------------------------------------

    def _refresh_gitignore_status(self, source_dir):
        """
        Atualiza o status da aba .gitignore baseado no diretório de entrada.
        Chamado após varredura.
        """
        gitignore_path = os.path.join(source_dir, ".gitignore")

        if not os.path.isfile(gitignore_path):
            wx.CallAfter(self.gitignore_status_label.SetLabel,
                         "⚠ Nenhum arquivo .gitignore encontrado na raiz do diretório.")
            wx.CallAfter(self.gitignore_active_cb.Disable)
            wx.CallAfter(self.gitignore_rules_list.Set, [])
            self._gitignore_parser = None
            return

        # Evitar re-parsear se o arquivo não mudou
        if self._gitignore_cache_path != gitignore_path:
            self._gitignore_parser = GitignoreParser(gitignore_path, source_dir)
            self._gitignore_cache_path = gitignore_path

        # Atualizar lista de regras na UI
        rules = self._gitignore_parser.get_rules_list()
        # Adicionar regras manuais
        all_rules = rules + [f"[manual] {r}" for r in self._gitignore_manual_rules]

        wx.CallAfter(self.gitignore_status_label.SetLabel,
                     f"✅ .gitignore encontrado: {len(rules)} regra(s) carregada(s).")
        wx.CallAfter(self.gitignore_active_cb.Enable)
        wx.CallAfter(self.gitignore_rules_list.Set, all_rules)

    def _on_gitignore_toggle(self, event):
        """Ativa/desativa conformidade com .gitignore."""
        self._apply_gitignore = self.gitignore_active_cb.GetValue()
        source_dir = self.source_dir_picker.GetPath()
        if source_dir and os.path.isdir(source_dir):
            self.output_text.AppendText(
                f"{'✅' if self._apply_gitignore else '⭕'} Conformidade .gitignore "
                f"{'ativada' if self._apply_gitignore else 'desativada'}. "
                f"Reiniciando varredura...\n")
            self._start_scan_thread(source_dir)

    def _on_add_gitignore_rule(self, event):
        """Adiciona uma regra manual ao parser."""
        rule = self.gitignore_rule_input.GetValue().strip()
        if not rule:
            return
        self._gitignore_manual_rules.append(rule)
        self.gitignore_rule_input.SetValue("")
        # Re-construir parser com regras extras
        source_dir = self.source_dir_picker.GetPath()
        if source_dir and self._gitignore_parser:
            self._gitignore_parser.rules.append((False, rule))
            self._refresh_gitignore_status(source_dir)
        self.output_text.AppendText(f"✓ Regra manual adicionada: {rule}\n")

    def _on_remove_gitignore_rule(self, event):
        """Remove a regra selecionada da lista."""
        idx = self.gitignore_rules_list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        rule_str = self.gitignore_rules_list.GetString(idx)
        if rule_str.startswith("[manual] "):
            manual_rule = rule_str[9:]
            if manual_rule in self._gitignore_manual_rules:
                self._gitignore_manual_rules.remove(manual_rule)
                self.gitignore_rules_list.Delete(idx)
                self.output_text.AppendText(f"✓ Regra manual removida: {manual_rule}\n")
        else:
            wx.MessageBox("Apenas regras manuais podem ser removidas aqui.\n"
                          "Edite o arquivo .gitignore para alterar as regras originais.",
                          "Info", wx.OK | wx.ICON_INFORMATION)

    def _on_refresh_gitignore_preview(self, event):
        """Gera preview de arquivos incluídos/ignorados pelo .gitignore."""
        source_dir = self.source_dir_picker.GetPath()
        if not source_dir or not os.path.isdir(source_dir):
            wx.MessageBox("Selecione o diretório de entrada primeiro.",
                          "Aviso", wx.OK | wx.ICON_WARNING)
            return
        if self._gitignore_parser is None:
            wx.MessageBox("Nenhum .gitignore encontrado ou carregado.",
                          "Aviso", wx.OK | wx.ICON_WARNING)
            return

        self.gitignore_preview_list.Clear()
        items = []
        try:
            for root, dirs, files in os.walk(source_dir):
                if self._use_ignore_patterns():
                    dirs[:] = [d for d in dirs if not _should_ignore(d, is_dir=True)]
                for fname in files[:50]:  # Limitar preview a 50 arquivos por pasta
                    fpath = os.path.join(root, fname)
                    try:
                        rel = os.path.relpath(fpath, source_dir)
                    except ValueError:
                        rel = fname
                    ignored = self._gitignore_parser.is_ignored(rel.replace(os.sep, '/'))
                    prefix = "🚫" if ignored else "✅"
                    items.append(f"{prefix} {rel}")
                    if len(items) >= 500:
                        items.append("... (preview limitado a 500 itens)")
                        break
                if len(items) >= 500:
                    break
        except Exception as e:
            items.append(f"Erro: {e}")

        self.gitignore_preview_list.Set(items)
        self.output_text.AppendText(f"✓ Preview .gitignore: {len(items)} item(s) listados.\n")

    # -----------------------------------------------------------------------
    # VARREDURA E ATUALIZAÇÃO DE LISTAS (legado mantido + melhorado)
    # -----------------------------------------------------------------------

    def update_file_and_extension_lists(self):
        """Dispara varredura assíncrona."""
        source_directory = self.source_dir_picker.GetPath()
        if not source_directory or not os.path.isdir(source_directory):
            self.all_extensions = []
            self.all_files = []
            return
        self._start_scan_thread(source_directory)

    # -----------------------------------------------------------------------
    # ÁRVORE DE ARQUIVOS
    # -----------------------------------------------------------------------

    def populate_file_tree(self):
        """Popula a árvore de arquivos no painel Explorador."""
        self.file_tree.Freeze()
        try:
            self.file_tree.DeleteAllItems()
            source_dir = self.source_dir_picker.GetPath()
            if not source_dir or not os.path.isdir(source_dir):
                return
            invisible_root = self.file_tree.AddRoot("DummyRoot")
            self._populate_tree_recursive(source_dir, invisible_root, is_top_level=True)
            self._update_all_tree_item_images(invisible_root)
        finally:
            self.file_tree.Thaw()

    def _populate_tree_recursive(self, parent_os_path, parent_tree_item, is_top_level=False):
        try:
            sort_key = self.get_sort_key()
            items_in_os = sorted(os.listdir(parent_os_path), key=sort_key)
        except OSError:
            return
        for item_name in items_in_os:
            # Aplicar filtros de exclusão
            is_dir = os.path.isdir(os.path.join(parent_os_path, item_name))
            if self._should_ignore_item(item_name, is_dir):
                continue
            current_os_path = os.path.join(parent_os_path, item_name)
            if self._apply_gitignore and self._gitignore_parser:
                try:
                    rel = os.path.relpath(current_os_path,
                                          self.source_dir_picker.GetPath())
                    if self._gitignore_parser.is_ignored(rel.replace(os.sep, '/')):
                        continue
                except ValueError:
                    pass
            current_tree_item = self.file_tree.AppendItem(parent_tree_item, item_name)
            self.file_tree.SetItemData(current_tree_item, current_os_path)
            if is_dir:
                self.file_tree.SetItemTextColour(current_tree_item, wx.BLUE)
                self._populate_tree_recursive(current_os_path, current_tree_item)

    def _get_all_descendant_files_from_os_path(self, folder_path):
        desc_files = []
        if not os.path.isdir(folder_path):
            return desc_files
        for r, _, fs in os.walk(folder_path):
            for f_name in fs:
                desc_files.append(os.path.join(r, f_name))
        return desc_files

    def _get_tree_item_state(self, tree_item):
        item_path = self.file_tree.GetItemData(tree_item)
        if not item_path:
            return "unchecked"
        if os.path.isfile(item_path):
            return "checked" if item_path in self.selected_files else "unchecked"
        elif os.path.isdir(item_path):
            descendant_files = self._get_all_descendant_files_from_os_path(item_path)
            if not descendant_files:
                return "unchecked"
            num_selected = sum(1 for f in descendant_files if f in self.selected_files)
            if num_selected == 0:
                return "unchecked"
            elif num_selected == len(descendant_files):
                return "checked"
            else:
                return "partial"
        return "unchecked"

    def _update_tree_item_image(self, tree_item):
        if not tree_item.IsOk():
            return
        state = self._get_tree_item_state(tree_item)
        image_index = {
            "checked": self.IMG_CHECKED,
            "partial": self.IMG_PARTIAL,
        }.get(state, self.IMG_UNCHECKED)
        self.file_tree.SetItemImage(tree_item, image_index)

    def _update_all_tree_item_images(self, start_node):
        if not start_node.IsOk():
            return
        self.file_tree.Freeze()
        try:
            self._update_tree_item_image_recursive_worker(start_node)
        finally:
            self.file_tree.Thaw()

    def _update_tree_item_image_recursive_worker(self, current_node):
        if not current_node.IsOk():
            return
        self._update_tree_item_image(current_node)
        child, cookie = self.file_tree.GetFirstChild(current_node)
        while child.IsOk():
            self._update_tree_item_image_recursive_worker(child)
            child, cookie = self.file_tree.GetNextChild(current_node, cookie)

    def _update_parents_images(self, tree_item):
        self.file_tree.Freeze()
        try:
            parent = self.file_tree.GetItemParent(tree_item)
            while parent.IsOk() and parent != self.file_tree.GetRootItem():
                self._update_tree_item_image(parent)
                parent = self.file_tree.GetItemParent(parent)
        finally:
            self.file_tree.Thaw()

    def on_tree_item_checkbox_activated(self, event):
        tree_item = event.GetItem()
        if not tree_item.IsOk():
            return
        item_path = self.file_tree.GetItemData(tree_item)
        if not item_path:
            return
        self.file_tree.Freeze()
        try:
            if os.path.isfile(item_path):
                if item_path in self.selected_files:
                    self.selected_files.discard(item_path)
                    self.output_text.AppendText(
                        f"Desmarcado: {os.path.basename(item_path)}\n")
                else:
                    self.selected_files.add(item_path)
                    self.output_text.AppendText(
                        f"Marcado: {os.path.basename(item_path)}\n")
                self._update_tree_item_image(tree_item)
                self._update_parents_images(tree_item)
            elif os.path.isdir(item_path):
                descendant_files = self._get_all_descendant_files_from_os_path(item_path)
                current_state = self._get_tree_item_state(tree_item)
                if current_state == "checked":
                    for f in descendant_files:
                        self.selected_files.discard(f)
                    self.output_text.AppendText(
                        f"Pasta desmarcada: {os.path.basename(item_path)}\n")
                else:
                    for f in descendant_files:
                        self.selected_files.add(f)
                    self.output_text.AppendText(
                        f"Pasta marcada: {os.path.basename(item_path)}\n")
                self._update_all_tree_item_images(tree_item)
                self._update_parents_images(tree_item)
        finally:
            self.file_tree.Thaw()
        self._update_selection_counter()
        event.Skip()

    # -----------------------------------------------------------------------
    # FILTROS E LISTAS
    # -----------------------------------------------------------------------

    def filter_extensions(self, event):
        search_term = self.extension_search.GetValue().lower()
        filtered = [ext for ext in self.all_extensions if search_term in ext.lower()]
        self.extension_checklist.Freeze()
        try:
            self.extension_checklist.Set(filtered)
            for i, ext in enumerate(filtered):
                self.extension_checklist.Check(i, ext in self.selected_extensions)
        finally:
            self.extension_checklist.Thaw()

    def filter_files(self, event):
        search_term = self.file_search.GetValue().lower() if hasattr(self, 'file_search') else ""
        if not self.all_files:
            self.file_list.Set([])
            return
        filtered = self.all_files if not search_term else [
            f for f in self.all_files
            if search_term in os.path.basename(f).lower()
            or search_term in os.path.dirname(f).lower()
        ]
        self.file_list.Freeze()
        try:
            self.file_list.Set(filtered)
            for i, fp in enumerate(filtered):
                self.file_list.Check(i, fp in self.selected_files)
        finally:
            self.file_list.Thaw()

    # -----------------------------------------------------------------------
    # EVENTOS DE CHECKBOX
    # -----------------------------------------------------------------------

    def on_extension_checked(self, event):
        idx = event.GetInt()
        ext = self.extension_checklist.GetString(idx)
        if self.extension_checklist.IsChecked(idx):
            self.selected_extensions.add(ext)
        else:
            self.selected_extensions.discard(ext)

    def on_file_checked(self, event):
        idx = event.GetInt()
        fp = self.file_list.GetString(idx)
        if self.file_list.IsChecked(idx):
            self.selected_files.add(fp)
        else:
            self.selected_files.discard(fp)
        self._sync_other_uis()
        self._update_selection_counter()

    def on_text_file_list_checked(self, event):
        idx = event.GetInt()
        fp = self.text_file_list.GetString(idx)
        if self.text_file_list.IsChecked(idx):
            self.selected_files.add(fp)
        else:
            self.selected_files.discard(fp)
        self._sync_other_uis()
        self._update_selection_counter()

    def on_random_file_checklist_toggled(self, event):
        pass

    def _sync_other_uis(self):
        """Sincroniza as outras abas após mudança de seleção."""
        self.Freeze()
        try:
            self.filter_extensions(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
            if hasattr(self, 'text_file_list'):
                self.text_file_list.Freeze()
                try:
                    for i, fp in enumerate(self.text_file_list.GetStrings()):
                        if fp in self.all_files:
                            self.text_file_list.Check(i, fp in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
        finally:
            self.Thaw()

    # -----------------------------------------------------------------------
    # BUSCA POR NOME
    # -----------------------------------------------------------------------

    def on_select_from_text_input(self, event):
        source_directory = self.source_dir_picker.GetPath()
        if not source_directory:
            wx.MessageBox("Selecione o diretório de Entrada primeiro.",
                          "Erro", wx.OK | wx.ICON_ERROR)
            return
        input_text = self.text_input.GetValue().strip()
        self.Freeze()
        try:
            if not input_text:
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files)
                    for i, fp in enumerate(self.all_files):
                        self.text_file_list.Check(i, fp in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
                return
            raw_entries = re.split(r'[,\s\n]+', input_text)
            search_terms = []
            for entry in raw_entries:
                entry = entry.strip()
                if not entry:
                    continue
                match = re.match(
                    r'\s*(?:modified:|new file:|deleted:|renamed:)?\s*'
                    r'(?P<filepath>[^\s].*?)(?:\s*->\s*.*)?$', entry)
                term = match.group('filepath').strip() if match else entry
                if "->" in term:
                    term = term.split("->")[-1].strip()
                search_terms.append(term)
            if not search_terms:
                return
            found_files = set()
            for full_path in self.all_files:
                basename = os.path.basename(full_path)
                name_no_ext, _ = os.path.splitext(basename)
                try:
                    rel = os.path.relpath(full_path, source_directory).replace("\\", "/")
                except ValueError:
                    rel = basename.replace("\\", "/")
                for term in search_terms:
                    term_lower = term.lower()
                    term_as_path = term.replace("\\", "/").lower()
                    norm_fp = full_path.replace("\\", "/").lower()
                    matched = False
                    if "/" in term or "\\" in term:
                        if norm_fp.endswith(term_as_path) or rel.lower() == term_as_path:
                            matched = True
                    else:
                        if term_lower in (basename.lower(), name_no_ext.lower()):
                            matched = True
                    if matched:
                        found_files.add(full_path)
                        break
            self.selected_files.clear()
            sort_key = self.get_sort_key()
            paths_to_show = sorted(list(found_files), key=sort_key)
            self.text_file_list.Freeze()
            try:
                self.text_file_list.SetItems(paths_to_show)
                for i, fp in enumerate(paths_to_show):
                    self.text_file_list.Check(i, True)
                    self.selected_files.add(fp)
            finally:
                self.text_file_list.Thaw()
            if not found_files:
                wx.MessageBox("Nenhum arquivo correspondente encontrado.",
                              "Aviso", wx.OK | wx.ICON_WARNING)
            else:
                self.output_text.AppendText(
                    f"{len(self.selected_files)} arquivo(s) encontrado(s).\n")
            self.filter_extensions(None)
            self.filter_files(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
        finally:
            self.Thaw()
        self._update_selection_counter()

    # -----------------------------------------------------------------------
    # ARQUIVOS AVULSOS
    # -----------------------------------------------------------------------

    def on_add_arbitrary_files_button(self, event):
        with wx.FileDialog(self, "Selecione arquivos para unir",
                           wildcard="Todos os arquivos (*.*)|*.*",
                           style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            self.add_arbitrary_files_to_list(dlg.GetPaths())

    def add_arbitrary_files_to_list(self, file_paths):
        self.random_files_checklist.Freeze()
        try:
            added = 0
            for path in file_paths:
                if path not in self.arbitrary_files_for_union:
                    self.arbitrary_files_for_union.append(path)
                    added += 1
            sort_key = self.get_sort_key()
            self.arbitrary_files_for_union.sort(key=sort_key)
            self.random_files_checklist.Set(self.arbitrary_files_for_union)
            for i in range(self.random_files_checklist.GetCount()):
                self.random_files_checklist.Check(i)
            if added > 0:
                self.output_text.AppendText(f"{added} arquivo(s) avulso(s) adicionado(s).\n")
        finally:
            self.random_files_checklist.Thaw()

    def on_remove_selected_arbitrary_files(self, event):
        selected_indices = self.random_files_checklist.GetCheckedItems()
        if not selected_indices:
            return
        self.random_files_checklist.Freeze()
        try:
            removed = 0
            for idx in sorted(selected_indices, reverse=True):
                path = self.random_files_checklist.GetString(idx)
                if path in self.arbitrary_files_for_union:
                    self.arbitrary_files_for_union.remove(path)
                self.random_files_checklist.Delete(idx)
                removed += 1
            if removed:
                self.output_text.AppendText(f"{removed} arquivo(s) removido(s).\n")
        finally:
            self.random_files_checklist.Thaw()

    def on_clear_arbitrary_files_list(self, event):
        self.arbitrary_files_for_union.clear()
        self.random_files_checklist.Freeze()
        try:
            self.random_files_checklist.Clear()
        finally:
            self.random_files_checklist.Thaw()
        self.output_text.AppendText("Lista de arquivos avulsos limpa.\n")

    # -----------------------------------------------------------------------
    # CÓPIA PRINCIPAL
    # -----------------------------------------------------------------------

    def on_copy(self, event):
        source_directory = self.source_dir_picker.GetPath()
        output_directory = self.output_dir_picker.GetPath()

        if not output_directory:
            wx.MessageBox("Selecione o diretório de Saída.", "Erro", wx.OK | wx.ICON_ERROR)
            return
        if not os.path.isdir(output_directory):
            try:
                os.makedirs(output_directory)
            except OSError:
                wx.MessageBox(f"Não foi possível criar: {output_directory}",
                              "Erro", wx.OK | wx.ICON_ERROR)
                return

        current_page_idx = self.notebook.GetSelection()
        page_title = self.notebook.GetPageText(current_page_idx)
        self.output_text.SetValue(f"Iniciando cópia (aba: {page_title})...\n")
        self.output_text.AppendText(f"Saída: {output_directory}\n")

        if page_title == "Selecionar Extensões":
            if not source_directory:
                wx.MessageBox("Selecione o diretório de Entrada.", "Erro", wx.OK | wx.ICON_ERROR)
                return
            if not self.selected_extensions:
                wx.MessageBox("Selecione pelo menos uma extensão.", "Aviso",
                              wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_extensions(source_directory, output_directory,
                                    list(self.selected_extensions))

        elif page_title in ("Selecionar Arquivos", "Buscar por Nome",
                            "Explorador de Arquivos"):
            if not source_directory:
                wx.MessageBox("Selecione o diretório de Entrada.", "Erro", wx.OK | wx.ICON_ERROR)
                return
            if page_title == "Selecionar Arquivos":
                files = [self.file_list.GetString(i)
                         for i in self.file_list.GetCheckedItems()
                         if self.file_list.GetString(i).startswith(source_directory)]
            elif page_title == "Buscar por Nome":
                files = [self.text_file_list.GetString(i)
                         for i in self.text_file_list.GetCheckedItems()
                         if self.text_file_list.GetString(i).startswith(source_directory)]
            else:
                sort_key = self.get_sort_key()
                files = sorted([f for f in self.selected_files
                                 if f.startswith(source_directory)], key=sort_key)
            if not files:
                wx.MessageBox(f"Nenhum arquivo selecionado na aba '{page_title}'.",
                              "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_selected_file_paths(source_directory, output_directory, files)

        elif page_title == "Unir Arquivos Avulsos":
            files = [self.random_files_checklist.GetString(i)
                     for i in self.random_files_checklist.GetCheckedItems()]
            if not files:
                wx.MessageBox("Nenhum arquivo avulso selecionado.", "Aviso",
                              wx.OK | wx.ICON_WARNING)
                return
            self.copy_arbitrary_files(output_directory, files)

        elif page_title == "Conformidade .gitignore":
            wx.MessageBox("Use uma das outras abas para copiar arquivos com o filtro .gitignore ativo.",
                          "Info", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"Lógica não implementada para: {page_title}",
                          "Erro", wx.OK | wx.ICON_ERROR)

    def _build_metadata_header(self, source_dir, files_count, rules_applied=None):
        """Constrói o cabeçalho de metadados para o arquivo de saída."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"{'=' * 60}\n"
            f"  COPIADOR DE CÓDIGO AVANÇADO v2.0\n"
            f"{'=' * 60}\n"
            f"  Data/Hora    : {now}\n"
            f"  Origem       : {source_dir}\n"
            f"  Total arquivos: {files_count}\n"
        )
        if rules_applied:
            header += f"  Filtros ativos: {', '.join(rules_applied)}\n"
        header += f"{'=' * 60}\n\n"
        return header

    def _confirm_large_output(self, files_list):
        """Pede confirmação se o output for muito grande. Retorna True para prosseguir."""
        total_size = sum(os.path.getsize(f) for f in files_list
                         if os.path.isfile(f))
        size_mb = total_size / (1024 * 1024)
        est_tokens = total_size // 4  # ~4 bytes por token

        if size_mb > 20 or est_tokens > 100_000:
            result = wx.MessageBox(
                f"⚠ Output estimado: {size_mb:.1f} MB / ~{est_tokens:,} tokens.\n"
                f"Isso pode ser muito grande. Deseja continuar?",
                "Confirmação", wx.YES_NO | wx.ICON_WARNING)
            return result == wx.YES
        return True

    def copy_by_extensions(self, source_dir, output_dir, sel_extensions):
        output_file_path = os.path.join(output_dir, "codigo_completo.txt")
        self.output_text.AppendText(
            f"Copiando extensões: {sel_extensions}\n")
        files_copied = 0
        sort_key = self.get_sort_key()

        # Coletar arquivos que serão copiados para confirmação
        preview_files = []
        for root, dirs, files in os.walk(source_dir):
            if self._use_ignore_patterns():
                dirs[:] = [d for d in dirs if not _should_ignore(d, is_dir=True)]
            for f in files:
                if _get_ext_label(f) in sel_extensions:
                    preview_files.append(os.path.join(root, f))

        if not self._confirm_large_output(preview_files):
            self.output_text.AppendText("Cópia cancelada pelo usuário.\n")
            return

        # Progresso
        self.progress_gauge.Show()
        self.progress_gauge.SetRange(max(len(preview_files), 1))
        self.progress_gauge.SetValue(0)
        self.main_sizer.Layout()

        rules_applied = []
        if self._use_ignore_patterns():
            rules_applied.append("padrões globais")
        if self._apply_gitignore:
            rules_applied.append(".gitignore")

        with open(output_file_path, "w", encoding="utf-8") as f_out:
            f_out.write(self._build_metadata_header(
                source_dir, len(preview_files), rules_applied))
            root_node = TreeNode(os.path.basename(source_dir) or source_dir)

            def _process_dir(current_dir, current_treenode):
                nonlocal files_copied
                try:
                    items = sorted(os.listdir(current_dir), key=sort_key)
                except OSError as e:
                    self.output_text.AppendText(f"Erro ao listar {current_dir}: {e}\n")
                    return
                for item in items:
                    item_path = os.path.join(current_dir, item)
                    if os.path.isdir(item_path):
                        if self._should_ignore_item(item, is_dir=True):
                            continue
                        child_node = TreeNode(item)
                        current_treenode.add_child(child_node)
                        _process_dir(item_path, child_node)
                    else:
                        # Correção: usar _get_ext_label em vez de splitext direto
                        ext_label = _get_ext_label(item)
                        if ext_label not in sel_extensions:
                            continue
                        if self._should_ignore_item(item):
                            continue
                        if self._is_gitignored(item_path, source_dir):
                            continue
                        content, enc = _read_file_with_fallback(item_path)
                        rel_path = os.path.relpath(item_path, source_dir)
                        if content is None:
                            self.output_text.AppendText(
                                f"[{enc.upper()} IGNORADO] {rel_path}\n")
                            continue
                        f_out.write("=" * 42 + "\n")
                        f_out.write(f"Conteúdo de {item} "
                                    f"(caminho: {rel_path}) [enc: {enc}]:\n")
                        f_out.write("=" * 42 + "\n")
                        f_out.write(content + "\n\n")
                        current_treenode.add_child(TreeNode(item))
                        files_copied += 1
                        self.progress_gauge.SetValue(min(files_copied,
                                                         self.progress_gauge.GetRange()))
                        wx.YieldIfNeeded()

            _process_dir(source_dir, root_node)
            f_out.write("\n" + "=" * 42 + "\n")
            f_out.write("Estrutura de pastas (relativa à Entrada):\n")
            f_out.write("=" * 42 + "\n")
            f_out.write(root_node.print_tree())

        self.progress_gauge.Hide()
        self.main_sizer.Layout()
        self._last_output_path = output_file_path
        self.output_text.AppendText(
            f"\n✓ Cópia concluída: {files_copied} arquivo(s) → {output_file_path}\n")
        if files_copied > 0:
            wx.MessageBox(f"{files_copied} arquivo(s) copiado(s) para:\n{output_file_path}",
                          "Sucesso", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("Nenhum arquivo encontrado com as extensões selecionadas.",
                          "Aviso", wx.OK | wx.ICON_WARNING)

    def copy_by_selected_file_paths(self, source_dir, output_dir, sel_files_paths):
        output_file_path = os.path.join(output_dir, "codigo_completo.txt")
        self.output_text.AppendText(
            f"Copiando {len(sel_files_paths)} arquivo(s)...\n")
        files_copied = 0

        if not self._confirm_large_output(sel_files_paths):
            self.output_text.AppendText("Cópia cancelada pelo usuário.\n")
            return

        sort_key = self.get_sort_key()
        sel_files_paths = sorted(sel_files_paths, key=sort_key)

        # Progresso
        self.progress_gauge.Show()
        self.progress_gauge.SetRange(max(len(sel_files_paths), 1))
        self.progress_gauge.SetValue(0)
        self.main_sizer.Layout()

        # Nó raiz para a árvore de saída
        if not sel_files_paths:
            common_prefix = source_dir
        else:
            common_prefix = os.path.commonpath(sel_files_paths)
            if not os.path.isdir(common_prefix):
                common_prefix = os.path.dirname(common_prefix)
        root_name = (os.path.relpath(common_prefix, os.path.dirname(source_dir))
                     if common_prefix.startswith(source_dir)
                     else os.path.basename(common_prefix or "arquivos_selecionados"))
        root_node = TreeNode(root_name or "Raiz")

        rules_applied = []
        if self._use_ignore_patterns():
            rules_applied.append("padrões globais")
        if self._apply_gitignore:
            rules_applied.append(".gitignore")

        with open(output_file_path, "w", encoding="utf-8") as f_out:
            f_out.write(self._build_metadata_header(
                source_dir, len(sel_files_paths), rules_applied))

            for i, file_path in enumerate(sel_files_paths):
                try:
                    rel_tree = os.path.relpath(file_path, common_prefix)
                except ValueError:
                    rel_tree = os.path.basename(file_path)
                parts = rel_tree.split(os.sep)
                current_node = root_node
                for idx_p, part_name in enumerate(parts):
                    is_last = (idx_p == len(parts) - 1)
                    found = next((c for c in current_node.children
                                  if c.name == part_name), None)
                    if found:
                        current_node = found
                    else:
                        new_node = TreeNode(part_name)
                        current_node.add_child(new_node)
                        current_node = new_node

                try:
                    path_header = os.path.relpath(file_path, source_dir)
                except ValueError:
                    path_header = file_path

                content, enc = _read_file_with_fallback(file_path)
                if content is None:
                    self.output_text.AppendText(
                        f"[{enc.upper()} IGNORADO] {path_header}\n")
                    self.progress_gauge.SetValue(i + 1)
                    continue

                f_out.write("=" * 42 + "\n")
                f_out.write(f"Conteúdo de {os.path.basename(file_path)} "
                            f"(caminho: {path_header}) [enc: {enc}]:\n")
                f_out.write("=" * 42 + "\n")
                f_out.write(content + "\n\n")
                files_copied += 1
                self.progress_gauge.SetValue(i + 1)
                if i % 10 == 0:
                    wx.YieldIfNeeded()

            f_out.write("\n" + "=" * 42 + "\n")
            f_out.write("Estrutura (relativa ao ancestral comum ou Entrada):\n")
            f_out.write("=" * 42 + "\n")
            f_out.write(root_node.print_tree())

        self.progress_gauge.Hide()
        self.main_sizer.Layout()
        self._last_output_path = output_file_path
        self.output_text.AppendText(
            f"\n✓ {files_copied} arquivo(s) copiado(s) → {output_file_path}\n")
        wx.MessageBox(f"{files_copied} arquivo(s) copiado(s) para:\n{output_file_path}",
                      "Sucesso", wx.OK | wx.ICON_INFORMATION)

    def copy_arbitrary_files(self, output_dir, arbitrary_file_paths):
        output_file_path = os.path.join(output_dir, "codigo_completo.txt")
        self.output_text.AppendText(
            f"Unindo {len(arbitrary_file_paths)} arquivo(s) avulso(s)...\n")
        files_copied = 0

        if not self._confirm_large_output(arbitrary_file_paths):
            self.output_text.AppendText("Cópia cancelada pelo usuário.\n")
            return

        sort_key = self.get_sort_key()
        arbitrary_file_paths = sorted(arbitrary_file_paths, key=sort_key)

        self.progress_gauge.Show()
        self.progress_gauge.SetRange(max(len(arbitrary_file_paths), 1))
        self.progress_gauge.SetValue(0)
        self.main_sizer.Layout()

        with open(output_file_path, "w", encoding="utf-8") as f_out:
            f_out.write(self._build_metadata_header(
                "Arquivos Avulsos", len(arbitrary_file_paths)))

            for i, file_path in enumerate(arbitrary_file_paths):
                content, enc = _read_file_with_fallback(file_path)
                if content is None:
                    self.output_text.AppendText(
                        f"[{enc.upper()} IGNORADO] {file_path}\n")
                    self.progress_gauge.SetValue(i + 1)
                    continue
                f_out.write("=" * 42 + "\n")
                f_out.write(f"Conteúdo de {os.path.basename(file_path)} "
                            f"(caminho original: {file_path}) [enc: {enc}]:\n")
                f_out.write("=" * 42 + "\n")
                f_out.write(content + "\n\n")
                files_copied += 1
                self.progress_gauge.SetValue(i + 1)
                if i % 10 == 0:
                    wx.YieldIfNeeded()

            f_out.write("\n" + "=" * 42 + "\n")
            f_out.write("Arquivos Avulsos (Caminhos Originais):\n")
            f_out.write("=" * 42 + "\n")
            for fp in arbitrary_file_paths:
                f_out.write(f"- {fp}\n")

        self.progress_gauge.Hide()
        self.main_sizer.Layout()
        self._last_output_path = output_file_path
        self.output_text.AppendText(
            f"\n✓ {files_copied} arquivo(s) unido(s) → {output_file_path}\n")
        if files_copied > 0:
            wx.MessageBox(f"{files_copied} arquivo(s) unido(s) em:\n{output_file_path}",
                          "Sucesso", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("Nenhum arquivo avulso processado.", "Aviso", wx.OK | wx.ICON_WARNING)

    # -----------------------------------------------------------------------
    # CLIPBOARD
    # -----------------------------------------------------------------------

    def _on_copy_to_clipboard(self, event):
        """Copia o conteúdo do último codigo_completo.txt para a área de transferência."""
        if not self._last_output_path or not os.path.isfile(self._last_output_path):
            # Tentar encontrar no diretório de saída
            output_dir = self.output_dir_picker.GetPath()
            candidate = os.path.join(output_dir, "codigo_completo.txt") if output_dir else None
            if candidate and os.path.isfile(candidate):
                self._last_output_path = candidate
            else:
                wx.MessageBox(
                    "Nenhum arquivo de saída encontrado. Execute a cópia primeiro.",
                    "Aviso", wx.OK | wx.ICON_WARNING)
                return

        content, enc = _read_file_with_fallback(self._last_output_path)
        if content is None:
            wx.MessageBox("Não foi possível ler o arquivo de saída.", "Erro",
                          wx.OK | wx.ICON_ERROR)
            return

        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(content))
                wx.TheClipboard.Flush()
                self.output_text.AppendText(
                    f"✓ Conteúdo copiado para a área de transferência "
                    f"({len(content):,} caracteres).\n")
                self.SetStatusText("Copiado para clipboard!", 0)
            finally:
                wx.TheClipboard.Close()
        else:
            wx.MessageBox("Não foi possível acessar a área de transferência.",
                          "Erro", wx.OK | wx.ICON_ERROR)

    # -----------------------------------------------------------------------
    # LIMPAR TUDO
    # -----------------------------------------------------------------------

    def on_clear_all(self, event):
        self.Freeze()
        try:
            self.source_dir_picker.SetPath("")
            self.output_dir_picker.SetPath("")
            self.source_dir_last_path = None
            self.all_extensions = []
            self.all_files = []
            self.selected_extensions.clear()
            self.selected_files.clear()
            self.arbitrary_files_for_union.clear()
            self._gitignore_parser = None
            self._gitignore_cache_path = None
            self._last_output_path = None

            self.extension_search.SetValue("")
            self.extension_checklist.Freeze()
            try:
                self.extension_checklist.Set([])
            finally:
                self.extension_checklist.Thaw()

            self.file_search.SetValue("")
            self.file_list.Freeze()
            try:
                self.file_list.Set([])
            finally:
                self.file_list.Thaw()

            self.text_input.SetValue("")
            self.text_file_list.Freeze()
            try:
                self.text_file_list.Set([])
            finally:
                self.text_file_list.Thaw()

            if hasattr(self, 'file_tree'):
                self.file_tree.Freeze()
                try:
                    self.file_tree.DeleteAllItems()
                finally:
                    self.file_tree.Thaw()

            if hasattr(self, 'random_files_checklist'):
                self.random_files_checklist.Freeze()
                try:
                    self.random_files_checklist.Clear()
                finally:
                    self.random_files_checklist.Thaw()

            if hasattr(self, 'gitignore_rules_list'):
                self.gitignore_rules_list.Set([])
            if hasattr(self, 'gitignore_preview_list'):
                self.gitignore_preview_list.Set([])
            if hasattr(self, 'gitignore_status_label'):
                self.gitignore_status_label.SetLabel(
                    "⚠ Nenhum diretório de entrada selecionado.")

            self.output_text.Clear()
            self.output_text.AppendText("✓ Todos os campos e seleções foram limpos.\n")
            self._update_selection_counter()
        finally:
            self.Thaw()

    # -----------------------------------------------------------------------
    # ESC — LIMPAR PESQUISA
    # -----------------------------------------------------------------------

    def on_esc_pressed(self, event):
        idx = self.notebook.GetSelection()
        if idx == 0:
            self.extension_search.SetValue("")
            self.filter_extensions(None)
            self.extension_search.SetFocus()
        elif idx == 1:
            self.file_search.SetValue("")
            self.filter_files(None)
            self.file_search.SetFocus()
        elif idx == 2:
            self.text_file_list.Freeze()
            try:
                self.text_file_list.SetItems(self.all_files)
                for i, fp in enumerate(self.all_files):
                    self.text_file_list.Check(i, fp in self.selected_files)
            finally:
                self.text_file_list.Thaw()
            self.text_input.SetFocus()
        elif idx == 3:
            self.file_tree.SetFocus()
        elif idx == 4:
            self.random_files_checklist.SetFocus()

    # -----------------------------------------------------------------------
    # SELECT / DESELECT ALL
    # -----------------------------------------------------------------------

    def select_all_extensions(self, event):
        self.extension_checklist.Freeze()
        try:
            self.selected_extensions.clear()
            for i in range(self.extension_checklist.GetCount()):
                self.extension_checklist.Check(i, True)
                self.selected_extensions.add(self.extension_checklist.GetString(i))
        finally:
            self.extension_checklist.Thaw()

    def deselect_all_extensions(self, event):
        self.extension_checklist.Freeze()
        try:
            for i in range(self.extension_checklist.GetCount()):
                self.extension_checklist.Check(i, False)
            self.selected_extensions.clear()
        finally:
            self.extension_checklist.Thaw()

    def select_all_files_tab(self, event):
        self.Freeze()
        try:
            self.selected_files.clear()
            self.file_list.Freeze()
            try:
                for i in range(self.file_list.GetCount()):
                    self.file_list.Check(i, True)
                    self.selected_files.add(self.file_list.GetString(i))
            finally:
                self.file_list.Thaw()
            self._sync_other_uis()
        finally:
            self.Thaw()
        self._update_selection_counter()

    def deselect_all_files_tab(self, event):
        self.Freeze()
        try:
            self.file_list.Freeze()
            try:
                for i in range(self.file_list.GetCount()):
                    fp = self.file_list.GetString(i)
                    self.file_list.Check(i, False)
                    self.selected_files.discard(fp)
            finally:
                self.file_list.Thaw()
            self._sync_other_uis()
        finally:
            self.Thaw()
        self._update_selection_counter()

    def select_all_text_files_list(self, event):
        self.Freeze()
        try:
            self.text_file_list.Freeze()
            try:
                for i in range(self.text_file_list.GetCount()):
                    self.text_file_list.Check(i, True)
                    self.selected_files.add(self.text_file_list.GetString(i))
            finally:
                self.text_file_list.Thaw()
            self.filter_extensions(None)
            self.filter_files(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
        finally:
            self.Thaw()
        self._update_selection_counter()

    def deselect_all_text_files_list(self, event):
        self.Freeze()
        try:
            self.text_file_list.Freeze()
            try:
                for i in range(self.text_file_list.GetCount()):
                    fp = self.text_file_list.GetString(i)
                    self.text_file_list.Check(i, False)
                    self.selected_files.discard(fp)
            finally:
                self.text_file_list.Thaw()
            self.filter_extensions(None)
            self.filter_files(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
        finally:
            self.Thaw()
        self._update_selection_counter()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
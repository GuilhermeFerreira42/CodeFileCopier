import wx
import os
import re

class TreeNode:
    """Classe para representar nós da árvore binária."""
    def __init__(self, name):
        self.name = name
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def print_tree(self, level=0):
        """Retorna a árvore em formato hierárquico."""
        tree_str = " " * (level * 4) + f"{self.name}\n"
        for child in self.children:
            tree_str += child.print_tree(level + 1)
        return tree_str

class FileDropTarget(wx.FileDropTarget):
    """Classe para suportar arrastar e soltar diretórios."""
    def __init__(self, dir_picker, update_callback):
        super().__init__()
        self.dir_picker = dir_picker
        self.update_callback = update_callback

    def OnDropFiles(self, x, y, filenames):
        if len(filenames) > 0 and os.path.isdir(filenames[0]):
            self.dir_picker.SetPath(filenames[0])
            self.update_callback(None)
        return True

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame()
        self.frame.Show()
        return True

class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="INICIAR de Código")
        panel = wx.Panel(self)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # Seletor de diretório de origem
        self.source_dir_picker = wx.DirPickerCtrl(panel, message="Selecione o diretório de origem")
        self.source_dir_picker.Bind(wx.EVT_DIRPICKER_CHANGED, self.update_lists)
        self.sizer.Add(self.source_dir_picker, 0, wx.ALL | wx.EXPAND, 5)

        # Suporte a arrastar e soltar
        self.source_droptarget = FileDropTarget(self.source_dir_picker, self.update_lists)
        self.source_dir_picker.SetDropTarget(self.source_droptarget)

        # Seletor de diretório de saída
        self.output_dir_picker = wx.DirPickerCtrl(panel, message="Selecione o diretório de saída")
        self.sizer.Add(self.output_dir_picker, 0, wx.ALL | wx.EXPAND, 5)

        self.output_droptarget = FileDropTarget(self.output_dir_picker, self.update_lists)
        self.output_dir_picker.SetDropTarget(self.output_droptarget)

        # Notebook para abas
        self.notebook = wx.Notebook(panel)
        self.sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)

        # Aba de extensões
        self.extension_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.extension_panel, "Selecionar Extensões")
        self.setup_extension_panel()

        # Aba de arquivos
        self.file_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.file_panel, "Selecionar Arquivos")
        self.setup_file_panel()

        # Aba de texto
        self.text_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.text_panel, "Buscar por Nome")
        self.setup_text_panel()

        # Remover vinculações anteriores
        # self.extension_panel.Bind(wx.EVT_KEY_DOWN, self.on_search_key_down)
        # self.file_panel.Bind(wx.EVT_KEY_DOWN, self.on_search_key_down)

        # Configurar acelerador para a tecla 'Esc'
        esc_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_esc_pressed, id=esc_id)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, esc_id)])
        self.SetAcceleratorTable(accel_tbl)



        # Botão de copiar
        self.copy_button = wx.Button(panel, label="INICIAR")
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.sizer.Add(self.copy_button, 0, wx.ALL | wx.CENTER, 5)

        # Botão de limpar
        self.clear_button = wx.Button(panel, label="Limpar")
        self.clear_button.Bind(wx.EVT_BUTTON, self.on_clear)
        self.sizer.Add(self.clear_button, 0, wx.ALL | wx.CENTER, 5)

        # Área de texto de saída
        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.output_text, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.sizer)
        self.SetSize((590, 650))

        # Listas e conjuntos para seleções
        self.all_extensions = []
        self.all_files = []
        self.selected_extensions = set()
        self.selected_files = set()

    def setup_extension_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Barra de pesquisa
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.extension_panel, label="Pesquisar extensões:")
        self.extension_search = wx.TextCtrl(self.extension_panel)
        self.extension_search.Bind(wx.EVT_TEXT, self.filter_extensions)
        search_sizer.Add(search_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        search_sizer.Add(self.extension_search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(search_sizer, 0, wx.ALL | wx.EXPAND, 10)

        instructions = wx.StaticText(self.extension_panel, label="Selecione as extensões que deseja copiar:")
        sizer.Add(instructions, 0, wx.ALL, 10)
        self.extension_checklist = wx.CheckListBox(self.extension_panel, choices=[])
        self.extension_checklist.Bind(wx.EVT_CHECKLISTBOX, self.on_extension_checked)
        sizer.Add(self.extension_checklist, 1, wx.ALL | wx.EXPAND, 10)

        # Botões
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_button = wx.Button(self.extension_panel, label="Selecionar Tudo")
        deselect_all_button = wx.Button(self.extension_panel, label="Desmarcar Tudo")
        button_sizer.Add(select_all_button, 1, wx.ALL, 5)
        button_sizer.Add(deselect_all_button, 1, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        self.extension_panel.SetSizer(sizer)

        select_all_button.Bind(wx.EVT_BUTTON, self.select_all_extensions)
        deselect_all_button.Bind(wx.EVT_BUTTON, self.deselect_all_extensions)

    def setup_file_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Barra de pesquisa
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.file_panel, label="Pesquisar arquivos:")
        self.file_search = wx.TextCtrl(self.file_panel)
        self.file_search.Bind(wx.EVT_TEXT, self.filter_files)
        search_sizer.Add(search_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        search_sizer.Add(self.file_search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(search_sizer, 0, wx.ALL | wx.EXPAND, 10)

        instructions = wx.StaticText(self.file_panel, label="Selecione os arquivos que deseja copiar:")
        sizer.Add(instructions, 0, wx.ALL, 10)
        self.file_list = wx.CheckListBox(self.file_panel, choices=[])
        self.file_list.Bind(wx.EVT_CHECKLISTBOX, self.on_file_checked)
        self.file_list.SetMinSize((400, 300))
        sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 10)

        # Botões
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_files_button = wx.Button(self.file_panel, label="Selecionar Todos")
        deselect_all_files_button = wx.Button(self.file_panel, label="Deselecionar Todos")
        button_sizer.Add(select_all_files_button, 1, wx.ALL, 5)
        button_sizer.Add(deselect_all_files_button, 1, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        self.file_panel.SetSizer(sizer)

        select_all_files_button.Bind(wx.EVT_BUTTON, self.select_all_files)
        deselect_all_files_button.Bind(wx.EVT_BUTTON, self.deselect_all_files)

    def on_esc_pressed(self, event):
        """Limpa a barra de pesquisa da aba ativa e retorna o foco para ela."""
        current_page = self.notebook.GetSelection()
        if current_page == 0:  # Aba de extensões
            self.extension_search.SetValue("")  # Limpa o texto
            self.filter_extensions(None)  # Atualiza a lista de extensões
            self.extension_search.SetFocus()  # Retorna o foco
        elif current_page == 1:  # Aba de arquivos
            self.file_search.SetValue("")  # Limpa o texto
            self.filter_files(None)  # Atualiza a lista de arquivos
            self.file_search.SetFocus()  # Retorna o foco
        elif current_page == 2:  # Aba de texto
            self.text_input.SetFocus()  # Mantém o texto e o foco
            # Mostrar todos os arquivos novamente
            self.text_file_list.SetItems(self.all_files)
            # Manter seleções existentes
            for i in range(self.text_file_list.GetCount()):
                file_path = self.text_file_list.GetString(i)
                self.text_file_list.Check(i, file_path in self.selected_files)

    def update_lists(self, event):
        source_directory = self.source_dir_picker.GetPath()
        if source_directory:
            self.all_extensions = sorted(set(
                os.path.splitext(file)[1]
                for root, _, files in os.walk(source_directory)
                for file in files
                if os.path.splitext(file)[1]
            ))
            self.filter_extensions(None)
            self.all_files = [
                os.path.join(root, file)
                for root, _, files in os.walk(source_directory)
                for file in files
            ]
            self.filter_files(None)
            # Atualizar a lista de arquivos na terceira aba
            self.text_file_list.SetItems(self.all_files)

    def filter_extensions(self, event):
        search_term = self.extension_search.GetValue().lower()
        filtered_extensions = [ext for ext in self.all_extensions if search_term in ext.lower()]
        self.extension_checklist.Set(filtered_extensions)
        for i, ext in enumerate(filtered_extensions):
            if ext in self.selected_extensions:
                self.extension_checklist.Check(i, True)

    def filter_files(self, event):
        search_term = self.file_search.GetValue().lower()
        filtered_files = [
            file for file in self.all_files
            if search_term in os.path.basename(file).lower() or
               search_term in os.path.dirname(file).lower() or
               search_term in os.path.splitext(file)[1].lower()
        ]
        self.file_list.Set(filtered_files)
        for i, file in enumerate(filtered_files):
            if file in self.selected_files:
                self.file_list.Check(i, True)

    def on_extension_checked(self, event):
        index = event.GetInt()
        ext = self.extension_checklist.GetString(index)
        if self.extension_checklist.IsChecked(index):
            self.selected_extensions.add(ext)
        else:
            self.selected_extensions.discard(ext)

    def on_file_checked(self, event):
        index = event.GetInt()
        file = self.file_list.GetString(index)
        if self.file_list.IsChecked(index):
            self.selected_files.add(file)
        else:
            self.selected_files.discard(file)

    def on_copy(self, event):
        source_directory = self.source_dir_picker.GetPath()
        output_directory = self.output_dir_picker.GetPath()
        if not source_directory or not output_directory:
            wx.MessageBox("Selecione os diretórios de origem e saída.", "Erro", wx.OK | wx.ICON_ERROR)
            return
        current_page = self.notebook.GetSelection()
        if current_page == 0:
            selected_extensions = list(self.selected_extensions)
            if not selected_extensions:
                wx.MessageBox("Selecione pelo menos uma extensão.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_extensions(source_directory, output_directory, selected_extensions)
        elif current_page == 1 or current_page == 2:  # Aba de arquivos ou texto
            selected_files = list(self.selected_files)
            if not selected_files:
                wx.MessageBox("Selecione pelo menos um arquivo.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_files(source_directory, output_directory, selected_files)

    def copy_by_extensions(self, source_directory, output_directory, selected_extensions):
        output_file_path = os.path.join(output_directory, "codigo_completo.txt")
        with open(output_file_path, "w", encoding="utf-8") as f:
            self.output_text.SetValue(f"Copiando arquivos de código de: {source_directory}\n\n")
            self.output_text.AppendText("Arquivos Copiados:\n")
            root_node = TreeNode(os.path.basename(source_directory))
            self.copy_files(source_directory, root_node, f, selected_extensions)
            f.write("\n==========================================\n")
            f.write("Estrutura de pastas:\n")
            f.write("==========================================\n")
            f.write(root_node.print_tree())
        wx.MessageBox(f"Arquivos copiados para {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)

    def copy_by_files(self, source_directory, output_directory, selected_files):
        output_file_path = os.path.join(output_directory, "codigo_completo.txt")
        with open(output_file_path, "w", encoding="utf-8") as f:
            self.output_text.SetValue(f"Copiando arquivos de código de: {source_directory}\n\n")
            self.output_text.AppendText("Arquivos Copiados:\n")
            root_node = TreeNode(os.path.basename(source_directory))
            for file in selected_files:
                self.output_text.AppendText(f"- {os.path.basename(file)}\n")
                with open(file, "r", encoding="utf-8", errors="ignore") as code_file:
                    f.write(f"Conteúdo de {os.path.basename(file)}:\n")
                    f.write(code_file.read() + "\n\n")
                self.add_to_tree(root_node, file)
            f.write("\n==========================================\n")
            f.write("Estrutura de pastas:\n")
            f.write("==========================================\n")
            f.write(root_node.print_tree())
        wx.MessageBox(f"Arquivos copiados para {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)

    def add_to_tree(self, root_node, file_path):
        parts = file_path.split(os.sep)
        current_node = root_node
        for part in parts[1:]:
            found = False
            for child in current_node.children:
                if child.name == part:
                    current_node = child
                    found = True
                    break
            if not found:
                new_node = TreeNode(part)
                current_node.add_child(new_node)
                current_node = new_node

    def copy_files(self, directory, tree_node, output_file, selected_extensions):
        for item in os.listdir(directory):
            path = os.path.join(directory, item)
            if os.path.isdir(path):
                child_node = TreeNode(item)
                tree_node.add_child(child_node)
                self.copy_files(path, child_node, output_file, selected_extensions)
            elif os.path.splitext(item)[1] in selected_extensions:
                self.output_text.AppendText(f"- {item}\n")
                tree_node.add_child(TreeNode(item))
                with open(path, "r", encoding="utf-8", errors="ignore") as code_file:
                    output_file.write(f"Conteúdo de {item}:\n")
                    output_file.write(code_file.read() + "\n\n")

    def on_clear(self, event):
        self.source_dir_picker.SetPath("")
        self.output_dir_picker.SetPath("")
        self.extension_checklist.Clear()
        self.file_list.Clear()
        self.text_input.Clear()
        self.text_file_list.Clear()
        self.output_text.Clear()
        self.all_extensions = []
        self.all_files = []
        self.selected_extensions.clear()
        self.selected_files.clear()
        self.extension_search.SetValue("")
        self.file_search.SetValue("")

    def select_all_extensions(self, event):
        for i in range(self.extension_checklist.GetCount()):
            ext = self.extension_checklist.GetString(i)
            self.extension_checklist.Check(i, True)
            self.selected_extensions.add(ext)

    def deselect_all_extensions(self, event):
        for i in range(self.extension_checklist.GetCount()):
            ext = self.extension_checklist.GetString(i)
            self.extension_checklist.Check(i, False)
            self.selected_extensions.discard(ext)

    def select_all_files(self, event):
        for i in range(self.file_list.GetCount()):
            file = self.file_list.GetString(i)
            self.file_list.Check(i, True)
            self.selected_files.add(file)

    def deselect_all_files(self, event):
        for i in range(self.file_list.GetCount()):
            file = self.file_list.GetString(i)
            self.file_list.Check(i, False)
            self.selected_files.discard(file)

    def setup_text_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Instruções
        instructions = wx.StaticText(self.text_panel, label="Digite os nomes dos arquivos (separados por espaço, vírgula ou linha):")
        sizer.Add(instructions, 0, wx.ALL, 10)

        # Campo de texto para entrada
        self.text_input = wx.TextCtrl(self.text_panel, style=wx.TE_MULTILINE)
        sizer.Add(self.text_input, 1, wx.EXPAND | wx.ALL, 10)

        # Botão "Selecionar"
        select_button = wx.Button(self.text_panel, label="Selecionar")
        select_button.Bind(wx.EVT_BUTTON, self.on_select_from_text)
        sizer.Add(select_button, 0, wx.ALL | wx.CENTER, 5)

        # Lista de arquivos (caminhos completos)
        self.text_file_list = wx.CheckListBox(self.text_panel, choices=[])
        self.text_file_list.Bind(wx.EVT_CHECKLISTBOX, self.on_text_file_checked)
        sizer.Add(self.text_file_list, 1, wx.EXPAND | wx.ALL, 10)

        # Botões de Seleção
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_button = wx.Button(self.text_panel, label="Selecionar Todos")
        deselect_all_button = wx.Button(self.text_panel, label="Deselecionar Todos")
        select_all_button.Bind(wx.EVT_BUTTON, self.select_all_text_files)
        deselect_all_button.Bind(wx.EVT_BUTTON, self.deselect_all_text_files)
        button_sizer.Add(select_all_button, 1, wx.ALL, 5)
        button_sizer.Add(deselect_all_button, 1, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND)

        self.text_panel.SetSizer(sizer)

    def on_select_from_text(self, event):
        source_directory = self.source_dir_picker.GetPath()
        if not source_directory:
            wx.MessageBox("Selecione o diretório de origem primeiro.", "Erro", wx.OK | wx.ICON_ERROR)
            return

        input_text = self.text_input.GetValue().strip()
        if not input_text:
            # Se o campo estiver vazio, mostrar todos os arquivos
            self.text_file_list.SetItems(self.all_files)
            return

        # Processar entradas (separar por espaço, vírgula ou nova linha)
        entries = [e.strip() for e in re.split(r'[,\s\n]+', input_text) if e.strip()]
        found_files = set()

        # Buscar arquivos com nomes exatos (case-insensitive)
        for root, _, files in os.walk(source_directory):
            for file in files:
                if file.lower() in [e.lower() for e in entries]:
                    found_files.add(os.path.join(root, file))

        if found_files:
            # Atualizar lista com caminhos completos
            self.text_file_list.SetItems(sorted(found_files))
            # Marcar arquivos encontrados
            self.selected_files.clear()
            for i in range(self.text_file_list.GetCount()):
                file_path = self.text_file_list.GetString(i)
                self.text_file_list.Check(i, True)
                self.selected_files.add(file_path)
        else:
            wx.MessageBox("Nenhum arquivo correspondente encontrado.", "Aviso", wx.OK | wx.ICON_WARNING)
        event.Skip()

    def on_text_file_checked(self, event):
        index = event.GetInt()
        file_path = self.text_file_list.GetString(index)
        if self.text_file_list.IsChecked(index):
            self.selected_files.add(file_path)
        else:
            self.selected_files.discard(file_path)
        event.Skip()

    def select_all_text_files(self, event):
        for i in range(self.text_file_list.GetCount()):
            file_path = self.text_file_list.GetString(i)
            self.text_file_list.Check(i, True)
            self.selected_files.add(file_path)
        event.Skip()

    def deselect_all_text_files(self, event):
        for i in range(self.text_file_list.GetCount()):
            file_path = self.text_file_list.GetString(i)
            self.text_file_list.Check(i, False)
            self.selected_files.discard(file_path)
        event.Skip()

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()

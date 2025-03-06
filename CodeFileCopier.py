import wx
import os

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


class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame()
        self.frame.Show()
        return True


class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Copiar Arquivos de Código")
        panel = wx.Panel(self)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # Seletor de diretório de origem
        self.source_dir_picker = wx.DirPickerCtrl(panel, message="Selecione o diretório de origem")
        self.source_dir_picker.Bind(wx.EVT_DIRPICKER_CHANGED, self.update_file_list)
        self.sizer.Add(self.source_dir_picker, 0, wx.ALL | wx.EXPAND, 5)

        # Adiciona suporte a arrastar e soltar para o diretório de origem
        self.source_droptarget = FileDropTarget(self.source_dir_picker)
        self.source_dir_picker.SetDropTarget(self.source_droptarget)

        # Seletor de diretório de saída
        self.output_dir_picker = wx.DirPickerCtrl(panel, message="Selecione o diretório de saída")
        self.sizer.Add(self.output_dir_picker, 0, wx.ALL | wx.EXPAND, 5)

        # Adiciona suporte a arrastar e soltar para o diretório de saída
        self.output_droptarget = FileDropTarget(self.output_dir_picker)
        self.output_dir_picker.SetDropTarget(self.output_droptarget)

        # Notebook para abas
        self.notebook = wx.Notebook(panel)
        self.sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)

        # Aba de seleção de extensões
        self.extension_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.extension_panel, "Selecionar Extensões")
        self.setup_extension_panel()

        # Aba de seleção de arquivos
        self.file_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.file_panel, "Selecionar Arquivos")
        self.setup_file_panel()

        # Botão de copiar
        self.copy_button = wx.Button(panel, label="Copiar Arquivos")
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.sizer.Add(self.copy_button, 0, wx.ALL | wx.CENTER, 5)

        # Área de texto de saída
        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.output_text, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.sizer)
        self.SetSize((600, 400))

        self.selected_extensions = []  # Lista de extensões selecionadas

    def setup_extension_panel(self):
        """Configura a aba de seleção de extensões."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(self.extension_panel, label="Selecione as extensões que deseja copiar:")
        sizer.Add(instructions, 0, wx.ALL, 10)
        self.extension_checklist = wx.CheckListBox(self.extension_panel, choices=[])
        sizer.Add(self.extension_checklist, 1, wx.ALL | wx.EXPAND, 10)
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
        """Configura a aba de seleção de arquivos específicos."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(self.file_panel, label="Selecione os arquivos que deseja copiar:")
        sizer.Add(instructions, 0, wx.ALL, 10)
        self.file_list = wx.CheckListBox(self.file_panel, choices=[])
        sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 10)
        self.file_list.SetMinSize((400, 300))
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_files_button = wx.Button(self.file_panel, label="Selecionar Todos")
        deselect_all_files_button = wx.Button(self.file_panel, label="Deselecionar Todos")
        button_sizer.Add(select_all_files_button, 1, wx.ALL, 5)
        button_sizer.Add(deselect_all_files_button, 1, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)
        self.file_panel.SetSizer(sizer)

        select_all_files_button.Bind(wx.EVT_BUTTON, self.select_all_files)
        deselect_all_files_button.Bind(wx.EVT_BUTTON, self.deselect_all_files)

    def select_all_extensions(self, event):
        """Seleciona todas as extensões na lista."""
        for i in range(self.extension_checklist.GetCount()):
            self.extension_checklist.Check(i, True)

    def deselect_all_extensions(self, event):
        """Desmarca todas as extensões na lista."""
        for i in range(self.extension_checklist.GetCount()):
            self.extension_checklist.Check(i, False)

    def select_all_files(self, event):
        """Seleciona todos os arquivos na lista."""
        for i in range(self.file_list.GetCount()):
            self.file_list.Check(i, True)

    def deselect_all_files(self, event):
        """Desmarca todos os arquivos na lista."""
        for i in range(self.file_list.GetCount()):
            self.file_list.Check(i, False)

    def update_file_list(self, event):
        """Atualiza a lista de arquivos na aba de seleção de arquivos."""
        source_directory = self.source_dir_picker.GetPath()
        if source_directory:
            files = [os.path.join(root, file) for root, _, files in os.walk(source_directory) for file in files]
            self.file_list.Set(files)
            # Atualiza também as extensões disponíveis
            extensions = sorted(set(os.path.splitext(file)[1] for file in files if os.path.splitext(file)[1]))
            self.extension_checklist.Set(extensions)

    def on_copy(self, event):
        """Executa a lógica de cópia dependendo da aba selecionada."""
        source_directory = self.source_dir_picker.GetPath()
        output_directory = self.output_dir_picker.GetPath()

        if not source_directory:
            wx.MessageBox("Por favor, selecione um diretório de origem.", "Erro", wx.OK | wx.ICON_ERROR)
            return
        if not output_directory:
            wx.MessageBox("Por favor, selecione um diretório de saída.", "Erro", wx.OK | wx.ICON_ERROR)
            return

        current_page = self.notebook.GetSelection()
        if current_page == 0:  # Aba de extensões
            self.copy_by_extensions(source_directory, output_directory)
        elif current_page == 1:  # Aba de arquivos
            self.copy_by_files(source_directory, output_directory)

    def copy_by_extensions(self, source_directory, output_directory):
        """Copia arquivos com base nas extensões selecionadas."""
        extensions = sorted(set(
            os.path.splitext(file)[1] 
            for root, _, files in os.walk(source_directory) 
            for file in files
        ))
        self.extension_checklist.Set(extensions)

        # Verifica se há extensões selecionadas, caso contrário, pede ao usuário
        if not self.selected_extensions:
            dlg = wx.Dialog(self, title="Selecionar Extensões", size=(400, 300))
            dlg_sizer = wx.BoxSizer(wx.VERTICAL)
            instructions = wx.StaticText(dlg, label="Selecione as extensões que deseja copiar:")
            dlg_sizer.Add(instructions, 0, wx.ALL, 10)
            self.extension_checklist = wx.CheckListBox(dlg, choices=extensions)
            dlg_sizer.Add(self.extension_checklist, 1, wx.ALL | wx.EXPAND, 10)
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            select_all_button = wx.Button(dlg, label="Selecionar Tudo")
            deselect_all_button = wx.Button(dlg, label="Desmarcar Tudo")
            button_sizer.Add(select_all_button, 1, wx.ALL, 5)
            button_sizer.Add(deselect_all_button, 1, wx.ALL, 5)
            dlg_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)
            action_sizer = wx.BoxSizer(wx.HORIZONTAL)
            ok_button = wx.Button(dlg, wx.ID_OK, label="OK")
            cancel_button = wx.Button(dlg, wx.ID_CANCEL, label="Cancelar")
            action_sizer.Add(ok_button, 1, wx.ALL, 5)
            action_sizer.Add(cancel_button, 1, wx.ALL, 5)
            dlg_sizer.Add(action_sizer, 0, wx.ALIGN_CENTER)
            dlg.SetSizer(dlg_sizer)

            select_all_button.Bind(wx.EVT_BUTTON, self.select_all_extensions)
            deselect_all_button.Bind(wx.EVT_BUTTON, self.deselect_all_extensions)

            if dlg.ShowModal() == wx.ID_OK:
                self.selected_extensions = [
                    extensions[i] 
                    for i in range(self.extension_checklist.GetCount()) 
                    if self.extension_checklist.IsChecked(i)
                ]
            else:
                dlg.Destroy()
                return
            dlg.Destroy()

        if not self.selected_extensions:
            wx.MessageBox("Nenhuma extensão selecionada.", "Aviso", wx.OK | wx.ICON_WARNING)
            return

        output_file_path = os.path.join(output_directory, "codigo_completo.txt")
        with open(output_file_path, "w", encoding="utf-8") as f:
            self.output_text.SetValue(f"Copiando arquivos de código de: {source_directory}\n\n")
            self.output_text.AppendText("Arquivos Copiados:\n")
            root_node = TreeNode(os.path.basename(source_directory))
            self.copy_files(source_directory, root_node, f)
            f.write("\n==========================================\n")
            f.write("Estrutura de pastas:\n")
            f.write("==========================================\n")
            f.write(root_node.print_tree())
        wx.MessageBox(f"Arquivos copiados para {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)

    def copy_by_files(self, source_directory, output_directory):
        """Copia arquivos específicos selecionados."""
        selected_files = [self.file_list.GetString(i) for i in self.file_list.GetCheckedItems()]
        if not selected_files:
            wx.MessageBox("Nenhum arquivo selecionado.", "Aviso", wx.OK | wx.ICON_WARNING)
            return

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
        """Adiciona um arquivo à estrutura da árvore binária."""
        parts = file_path.split(os.sep)
        current_node = root_node
        for part in parts[1:]:  # Ignora o diretório raiz
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

    def copy_files(self, directory, tree_node, output_file):
        """Copia arquivos recursivamente com base nas extensões selecionadas."""
        for item in os.listdir(directory):
            path = os.path.join(directory, item)
            if os.path.isdir(path):
                child_node = TreeNode(item)
                tree_node.add_child(child_node)
                self.copy_files(path, child_node, output_file)
            elif os.path.splitext(item)[1] in self.selected_extensions:
                self.output_text.AppendText(f"- {item}\n")
                tree_node.add_child(TreeNode(item))
                with open(path, "r", encoding="utf-8", errors="ignore") as code_file:
                    output_file.write(f"Conteúdo de {item}:\n")
                    output_file.write(code_file.read() + "\n\n")


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, dir_picker):
        super().__init__()
        self.dir_picker = dir_picker

    def OnDropFiles(self, x, y, filenames):
        if len(filenames) > 0 and os.path.isdir(filenames[0]):
            self.dir_picker.SetPath(filenames[0])
        return True


if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
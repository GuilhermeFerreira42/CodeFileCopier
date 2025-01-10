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

        self.copy_button = wx.Button(panel, label="Copiar Arquivos")
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_select_extensions)
        self.sizer.Add(self.copy_button, 0, wx.ALL | wx.CENTER, 5)

        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.output_text, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.sizer)
        self.SetSize((600, 400))

        self.selected_extensions = []  # Inicializa a lista de extensões selecionadas

    def on_select_extensions(self, event):
        source_directory = self.source_dir_picker.GetPath()
        
        if not source_directory:
            wx.MessageBox("Por favor, selecione um diretório de origem.", "Erro", wx.OK | wx.ICON_ERROR)
            return
        
        # Listar extensões de arquivos em todas as subpastas
        extensions = set()
        for root, dirs, files in os.walk(source_directory):
            for file in files:
                ext = os.path.splitext(file)[1]
                extensions.add(ext)

        # Listar extensões de arquivos em todas as subpastas
        extensions = sorted(set(
            os.path.splitext(file)[1] 
            for root, _, files in os.walk(source_directory) 
            for file in files
        ))

        # Criar janela personalizada para seleção de extensões
        dlg = wx.Dialog(self, title="Selecionar Extensões", size=(400, 300))
        dlg_sizer = wx.BoxSizer(wx.VERTICAL)

        instructions = wx.StaticText(dlg, label="Selecione as extensões que deseja copiar:")
        dlg_sizer.Add(instructions, 0, wx.ALL, 10)

        self.extension_checklist = wx.CheckListBox(dlg, choices=extensions)
        dlg_sizer.Add(self.extension_checklist, 1, wx.ALL | wx.EXPAND, 10)

        # Botões de "Selecionar Tudo" e "Desmarcar Tudo"
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_button = wx.Button(dlg, label="Selecionar Tudo")
        deselect_all_button = wx.Button(dlg, label="Desmarcar Tudo")
        button_sizer.Add(select_all_button, 1, wx.ALL, 5)
        button_sizer.Add(deselect_all_button, 1, wx.ALL, 5)
        dlg_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        # Botões OK e Cancelar
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(dlg, wx.ID_OK, label="OK")
        cancel_button = wx.Button(dlg, wx.ID_CANCEL, label="Cancelar")
        action_sizer.Add(ok_button, 1, wx.ALL, 5)
        action_sizer.Add(cancel_button, 1, wx.ALL, 5)
        dlg_sizer.Add(action_sizer, 0, wx.ALIGN_CENTER)

        dlg.SetSizer(dlg_sizer)

        # Event handlers para os botões
        def select_all(event):
            for i in range(self.extension_checklist.GetCount()):
                self.extension_checklist.Check(i, True)

        def deselect_all(event):
            for i in range(self.extension_checklist.GetCount()):
                self.extension_checklist.Check(i, False)

        select_all_button.Bind(wx.EVT_BUTTON, select_all)
        deselect_all_button.Bind(wx.EVT_BUTTON, deselect_all)

        # Mostrar o diálogo
        if dlg.ShowModal() == wx.ID_OK:
            self.selected_extensions = [
                extensions[i] 
                for i in range(self.extension_checklist.GetCount()) 
                if self.extension_checklist.IsChecked(i)
            ]
            self.on_copy(event)

        dlg.Destroy()

    def on_copy(self, event):
        source_directory = self.source_dir_picker.GetPath()
        output_directory = self.output_dir_picker.GetPath()

        if not source_directory:
            wx.MessageBox("Por favor, selecione um diretório de origem.", "Erro", wx.OK | wx.ICON_ERROR)
            return
        if not output_directory:
            wx.MessageBox("Por favor, selecione um diretório de saída.", "Erro", wx.OK | wx.ICON_ERROR)
            return

        output_file_path = os.path.join(output_directory, "codigo_completo.txt")
        with open(output_file_path, "w", encoding="utf-8") as f:
            self.output_text.SetValue(f"Copiando arquivos de código de: {source_directory}\n\n")
            self.output_text.AppendText("Arquivos Copiados:\n")

            # Criação da árvore binária
            root_node = TreeNode(os.path.basename(source_directory))
            self.copy_files(source_directory, root_node, f)

            # Adiciona a árvore de diretórios ao final do arquivo
            f.write("\n==========================================\n")
            f.write("Estrutura de pastas:\n")
            f.write("==========================================\n")
            f.write(root_node.print_tree())

        wx.MessageBox(f"Arquivos copiados para {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)

    def copy_files(self, directory, tree_node, output_file):
        for item in os.listdir(directory):
            path = os.path.join(directory, item)
            if os.path.isdir(path):
                # Cria um novo nó para o diretório
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
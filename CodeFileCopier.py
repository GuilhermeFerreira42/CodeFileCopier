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
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.sizer.Add(self.copy_button, 0, wx.ALL | wx.CENTER, 5)

        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.output_text, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.sizer)
        self.SetSize((600, 400))

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
            elif item.endswith((".py", ".java", ".c", ".cpp", ".js", ".html", ".css")):
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

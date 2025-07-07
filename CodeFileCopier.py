import wx
import os
import re

# NOVO: Função para a chave de ordenação natural
def natural_sort_key(s):
    """
    Retorna uma chave para ordenação natural (ex: 'item2' antes de 'item10').
    Converte a string em uma lista de strings e números.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class TreeNode:
    """Classe para representar nós da árvore binária (para a saída de texto)."""
    def __init__(self, name, full_path=None):
        self.name = name
        self.full_path = full_path
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def print_tree(self, level=0, is_last_child=False, parent_prefix=""):
        """Retorna a árvore em formato hierárquico."""
        prefix = parent_prefix
        if level > 0:
            prefix += "    " if is_last_child else "│   "

        tree_str = parent_prefix + ("└── " if is_last_child else "├── ") + f"{self.name}\n"
        
        num_children = len(self.children)
        # NOVO: Ordenar os filhos antes de imprimir para garantir a consistência
        sorted_children = sorted(self.children, key=lambda c: natural_sort_key(c.name))
        for i, child in enumerate(sorted_children):
            tree_str += child.print_tree(level + 1, i == num_children - 1, prefix)
        return tree_str
    
    def print_flat_list(self):
        """Retorna uma lista simples de nomes de arquivos."""
        list_str = ""
        for child in self.children: 
            list_str += f"- {child.name}\n"
        return list_str


class DirectoryDropTarget(wx.FileDropTarget):
    """Classe para suportar arrastar e soltar diretórios."""
    def __init__(self, dir_picker, update_callback):
        super().__init__()
        self.dir_picker = dir_picker
        self.update_callback = update_callback

    def OnDropFiles(self, x, y, filenames):
        if len(filenames) > 0 and os.path.isdir(filenames[0]):
            self.dir_picker.SetPath(filenames[0])
            if self.update_callback: 
                 self.update_callback(None)
        return True

class FileListDropTarget(wx.FileDropTarget):
    """Classe para suportar arrastar e soltar arquivos em uma lista."""
    def __init__(self, list_control, add_files_callback):
        super().__init__()
        self.list_control = list_control
        self.add_files_callback = add_files_callback

    def OnDropFiles(self, x, y, filenames):
        files_to_add = [f for f in filenames if os.path.isfile(f)]
        if files_to_add:
             self.add_files_callback(files_to_add)
        return True

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame()
        self.frame.Show()
        return True

class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Copiador de Código Avançado")
        panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Constantes para imagens da árvore ---
        self.IMG_UNCHECKED = 0
        self.IMG_CHECKED = 1
        self.IMG_PARTIAL = 2

        # --- Configuração da ImageList para o TreeCtrl ---
        self.file_tree_img_list = wx.ImageList(16, 16)
        self.file_tree_img_list.Add(self._create_checkbox_bitmap(False)) # IMG_UNCHECKED
        self.file_tree_img_list.Add(self._create_checkbox_bitmap(True))  # IMG_CHECKED
        self.file_tree_img_list.Add(self._create_checkbox_bitmap(None))  # IMG_PARTIAL


        # --- Sizers de Diretório ---
        dir_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_label = wx.StaticText(panel, label="Entrada:")
        self.source_dir_picker = wx.DirPickerCtrl(panel, message="Selecione o diretório de Entrada")
        self.source_dir_picker.Bind(wx.EVT_DIRPICKER_CHANGED, self.on_source_dir_changed)
        dir_input_sizer.Add(input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        dir_input_sizer.Add(self.source_dir_picker, 1, wx.ALL | wx.EXPAND, 5)
        self.main_sizer.Add(dir_input_sizer, 0, wx.EXPAND | wx.ALL, 5)

        dir_output_sizer = wx.BoxSizer(wx.HORIZONTAL)
        output_label = wx.StaticText(panel, label="Saída:")
        self.output_dir_picker = wx.DirPickerCtrl(panel, message="Selecione o diretório de Saída")
        dir_output_sizer.Add(output_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        dir_output_sizer.Add(self.output_dir_picker, 1, wx.ALL | wx.EXPAND, 5)
        self.main_sizer.Add(dir_output_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # NOVO: Sizer para a opção de ordenação
        sort_option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sort_label = wx.StaticText(panel, label="Ordem da Cópia:")
        self.sort_choice = wx.Choice(panel, choices=["Ordenação Natural (Padrão)", "Ordenação Alfabética"])
        self.sort_choice.SetSelection(0) # Padrão é Natural
        sort_option_sizer.Add(sort_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        sort_option_sizer.Add(self.sort_choice, 1, wx.ALL | wx.EXPAND, 5)
        self.main_sizer.Add(sort_option_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.source_droptarget = DirectoryDropTarget(self.source_dir_picker, self.on_source_dir_changed)
        self.source_dir_picker.SetDropTarget(self.source_droptarget)
        self.output_droptarget = DirectoryDropTarget(self.output_dir_picker, None)
        self.output_dir_picker.SetDropTarget(self.output_droptarget)

        self.notebook = wx.Notebook(panel)
        self.main_sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)

        self.extension_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.extension_panel, "Selecionar Extensões")
        self.setup_extension_panel()

        self.file_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.file_panel, "Selecionar Arquivos")
        self.setup_file_panel()

        self.text_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.text_panel, "Buscar por Nome")
        self.setup_text_panel()
        
        self.tree_explorer_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.tree_explorer_panel, "Explorador de Arquivos")
        self.setup_tree_explorer_panel() # Configura o file_tree aqui

        self.random_union_panel = wx.Panel(self.notebook)
        self.notebook.AddPage(self.random_union_panel, "Unir Arquivos Avulsos")
        self.setup_random_union_panel()

        esc_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_esc_pressed, id=esc_id)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, esc_id)])
        self.SetAcceleratorTable(accel_tbl)

        self.copy_button = wx.Button(panel, label="INICIAR CÓPIA")
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.main_sizer.Add(self.copy_button, 0, wx.ALL | wx.CENTER, 5)

        self.clear_button = wx.Button(panel, label="Limpar Tudo")
        self.clear_button.Bind(wx.EVT_BUTTON, self.on_clear_all)
        self.main_sizer.Add(self.clear_button, 0, wx.ALL | wx.CENTER, 5)

        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.main_sizer.Add(self.output_text, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(self.main_sizer)
        self.SetSize((700, 730)) # Aumentei um pouco a altura para a nova opção

        self.all_extensions = []
        self.all_files = [] 
        self.selected_extensions = set()
        self.selected_files = set() 
        self.arbitrary_files_for_union = [] 
        self.source_dir_last_path = None

    # NOVO: Função helper para obter a chave de ordenação selecionada
    def get_sort_key(self):
        selection = self.sort_choice.GetSelection()
        if selection == 0: # Natural
            return natural_sort_key
        else: # Alfabética
            return None # Usa a ordenação padrão de strings

    def _create_checkbox_bitmap(self, checked_state):
        """Cria um bitmap 16x16 para simular um checkbox.
           checked_state: True (marcado), False (desmarcado), None (parcial)
        """
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

    def on_source_dir_changed(self, event):
        current_path = self.source_dir_picker.GetPath()
        if current_path and current_path != self.source_dir_last_path:
            self.source_dir_last_path = current_path
            # Envolver atualizações de UI em Freeze/Thaw
            self.Freeze() 
            try:
                self.update_file_and_extension_lists()
                self.populate_file_tree() 
            finally:
                self.Thaw()
        if event: 
            event.Skip()

    def update_file_and_extension_lists(self):
        source_directory = self.source_dir_picker.GetPath()
        if not source_directory or not os.path.isdir(source_directory):
            self.all_extensions = []
            self.all_files = []
        else:
            extensions = set()
            files_list = []
            # os.walk pode ser lento para diretórios muito grandes.
            # Para aplicações muito sensíveis, isso poderia ir para um thread,
            # mas para este escopo, vamos focar nas atualizações da UI.
            for root, _, files in os.walk(source_directory):
                for file in files:
                    ext = os.path.splitext(file)[1]
                    if ext:
                        extensions.add(ext)
                    files_list.append(os.path.join(root, file))
            self.all_extensions = sorted(list(extensions))
            # ALTERAÇÃO: Usar a função de ordenação para a lista de arquivos
            sort_key_func = self.get_sort_key()
            self.all_files = sorted(files_list, key=sort_key_func)


        # Congelar o notebook ou painéis individuais antes de múltiplas atualizações de lista
        # self.notebook.Freeze() # Ou congelar painéis/listas individualmente
        try:
            self.filter_extensions(None)  
            self.filter_files(None)       
            
            if hasattr(self, 'text_file_list'): 
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files)
                    current_text_selections = {self.text_file_list.GetString(i) for i in self.text_file_list.GetCheckedItems()}
                    self.selected_files.intersection_update(self.all_files) 
                    self.selected_files.update(current_text_selections.intersection(self.all_files))
                    
                    new_checked_indices = []
                    for i, item_path in enumerate(self.all_files):
                        if item_path in self.selected_files:
                            new_checked_indices.append(i)
                    self.text_file_list.SetCheckedItems(new_checked_indices)
                finally:
                    self.text_file_list.Thaw()
        finally:
            # self.notebook.Thaw()
            pass # Thaw individual já feito


    def setup_extension_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.extension_panel, label="Pesquisar extensões:")
        self.extension_search = wx.TextCtrl(self.extension_panel)
        self.extension_search.Bind(wx.EVT_TEXT, self.filter_extensions)
        search_sizer.Add(search_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5) 
        search_sizer.Add(self.extension_search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(search_sizer, 0, wx.ALL | wx.EXPAND, 10)

        instructions = wx.StaticText(self.extension_panel, label="Selecione as extensões que deseja copiar:")
        sizer.Add(instructions, 0, wx.ALL, 10)
        self.extension_checklist = wx.CheckListBox(self.extension_panel, choices=[])
        self.extension_checklist.Bind(wx.EVT_CHECKLISTBOX, self.on_extension_checked)
        sizer.Add(self.extension_checklist, 1, wx.ALL | wx.EXPAND, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_button = wx.Button(self.extension_panel, label="Selecionar Tudo")
        deselect_all_button = wx.Button(self.extension_panel, label="Desmarcar Tudo")
        button_sizer.Add(select_all_button, 1, wx.ALL, 5) 
        button_sizer.Add(deselect_all_button, 1, wx.ALL, 5) 
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 5) 

        self.extension_panel.SetSizer(sizer)
        select_all_button.Bind(wx.EVT_BUTTON, self.select_all_extensions)
        deselect_all_button.Bind(wx.EVT_BUTTON, self.deselect_all_extensions)

    def setup_file_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self.file_panel, label="Pesquisar arquivos:")
        self.file_search = wx.TextCtrl(self.file_panel)
        self.file_search.Bind(wx.EVT_TEXT, self.filter_files)
        search_sizer.Add(search_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        search_sizer.Add(self.file_search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(search_sizer, 0, wx.ALL | wx.EXPAND, 10)

        instructions = wx.StaticText(self.file_panel, label="Selecione os arquivos que deseja copiar:")
        sizer.Add(instructions, 0, wx.ALL, 10)
        self.file_list = wx.CheckListBox(self.file_panel, choices=[])
        self.file_list.Bind(wx.EVT_CHECKLISTBOX, self.on_file_checked)
        self.file_list.SetMinSize((400, 300))
        sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_files_button = wx.Button(self.file_panel, label="Selecionar Todos")
        deselect_all_files_button = wx.Button(self.file_panel, label="Deselecionar Todos")
        button_sizer.Add(select_all_files_button, 1, wx.ALL, 5) 
        button_sizer.Add(deselect_all_files_button, 1, wx.ALL, 5) 
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)

        self.file_panel.SetSizer(sizer)
        select_all_files_button.Bind(wx.EVT_BUTTON, self.select_all_files_tab) 
        deselect_all_files_button.Bind(wx.EVT_BUTTON, self.deselect_all_files_tab) 

    def setup_text_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(self.text_panel, label="Digite nomes ou caminhos de arquivos (ex: de 'git status', separados por espaço, vírgula ou linha):")
        sizer.Add(instructions, 0, wx.ALL, 10)

        self.text_input = wx.TextCtrl(self.text_panel, style=wx.TE_MULTILINE)
        self.text_input.SetMinSize((-1, 100)) 
        sizer.Add(self.text_input, 0, wx.EXPAND | wx.ALL, 10) 

        select_button = wx.Button(self.text_panel, label="Buscar e Selecionar na Lista Abaixo")
        select_button.Bind(wx.EVT_BUTTON, self.on_select_from_text_input)
        sizer.Add(select_button, 0, wx.ALL | wx.CENTER, 5)

        self.text_file_list = wx.CheckListBox(self.text_panel, choices=[])
        self.text_file_list.Bind(wx.EVT_CHECKLISTBOX, self.on_text_file_list_checked)
        self.text_file_list.SetMinSize((-1, 200)) 
        sizer.Add(self.text_file_list, 1, wx.EXPAND | wx.ALL, 10) 

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_button = wx.Button(self.text_panel, label="Selecionar Todos na Lista")
        deselect_all_button = wx.Button(self.text_panel, label="Deselecionar Todos na Lista")
        select_all_button.Bind(wx.EVT_BUTTON, self.select_all_text_files_list)
        deselect_all_button.Bind(wx.EVT_BUTTON, self.deselect_all_text_files_list)
        button_sizer.Add(select_all_button, 1, wx.ALL | wx.EXPAND, 5)
        button_sizer.Add(deselect_all_button, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5) 

        self.text_panel.SetSizer(sizer)

    def setup_tree_explorer_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(self.tree_explorer_panel, label="Selecione arquivos ou pastas no diretório de Entrada (duplo clique/Enter para marcar/desmarcar):")
        sizer.Add(instructions, 0, wx.ALL, 10)

        self.file_tree = wx.TreeCtrl(self.tree_explorer_panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        self.file_tree.AssignImageList(self.file_tree_img_list) 
        
        self.file_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_tree_item_checkbox_activated) 
        
        sizer.Add(self.file_tree, 1, wx.EXPAND | wx.ALL, 10)
        self.tree_explorer_panel.SetSizer(sizer)

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

            num_selected = 0
            # Esta parte pode ser lenta se a pasta tiver muitos arquivos.
            # A verificação de 'in self.selected_files' é O(1) em média para sets.
            for f_path in descendant_files:
                if f_path in self.selected_files:
                    num_selected += 1
            
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
        image_index = self.IMG_UNCHECKED
        if state == "checked":
            image_index = self.IMG_CHECKED
        elif state == "partial":
            image_index = self.IMG_PARTIAL
        
        # Evitar chamar SetItemImage se a imagem já for a correta
        # current_image = self.file_tree.GetItemImage(tree_item) # GetItemImage pode não retornar o que esperamos para comparação direta
        # if current_image != image_index: # Esta comparação pode não ser confiável
        self.file_tree.SetItemImage(tree_item, image_index)


    def _update_all_tree_item_images(self, start_node):
        if not start_node.IsOk():
            return
        
        self.file_tree.Freeze() # Congelar a árvore antes de múltiplas atualizações de imagem
        try:
            self._update_tree_item_image_recursive_worker(start_node)
        finally:
            self.file_tree.Thaw()

    def _update_tree_item_image_recursive_worker(self, current_node):
        """Trabalhador recursivo para _update_all_tree_item_images."""
        if not current_node.IsOk():
            return
        self._update_tree_item_image(current_node)
        child, cookie = self.file_tree.GetFirstChild(current_node)
        while child.IsOk():
            self._update_tree_item_image_recursive_worker(child)
            child, cookie = self.file_tree.GetNextChild(current_node, cookie)


    def _update_parents_images(self, tree_item):
        self.file_tree.Freeze() # Congelar antes de atualizar pais
        try:
            parent = self.file_tree.GetItemParent(tree_item)
            while parent.IsOk() and parent != self.file_tree.GetRootItem(): 
                self._update_tree_item_image(parent)
                parent = self.file_tree.GetItemParent(parent)
        finally:
            self.file_tree.Thaw()

    def populate_file_tree(self):
        self.file_tree.Freeze() # Congelar a árvore antes de grandes modificações
        try:
            self.file_tree.DeleteAllItems()
            source_dir = self.source_dir_picker.GetPath()
            if not source_dir or not os.path.isdir(source_dir):
                return
            
            invisible_root = self.file_tree.AddRoot("DummyRoot") 
            self._populate_tree_recursive(source_dir, invisible_root, is_top_level=True)
            
            # _update_all_tree_item_images já tem seu próprio Freeze/Thaw
            self._update_all_tree_item_images(invisible_root)
        finally:
            self.file_tree.Thaw()


    def _populate_tree_recursive(self, parent_os_path, parent_tree_item, is_top_level=False):
        try:
            # ALTERAÇÃO: Usar a função de ordenação ao listar os itens do diretório
            sort_key_func = self.get_sort_key()
            items_in_os = sorted(os.listdir(parent_os_path), key=sort_key_func)
        except OSError:
            return 

        for item_name in items_in_os:
            current_os_path = os.path.join(parent_os_path, item_name)
            current_tree_item = self.file_tree.AppendItem(parent_tree_item, item_name)
            self.file_tree.SetItemData(current_tree_item, current_os_path) 

            if os.path.isdir(current_os_path):
                self.file_tree.SetItemTextColour(current_tree_item, wx.BLUE) 
                self._populate_tree_recursive(current_os_path, current_tree_item)
            
    def on_tree_item_checkbox_activated(self, event): 
        tree_item = event.GetItem()
        if not tree_item.IsOk(): return
        
        item_path = self.file_tree.GetItemData(tree_item)
        if not item_path: return

        self.file_tree.Freeze() # Congelar antes de múltiplas atualizações
        try:
            if os.path.isfile(item_path):
                if item_path in self.selected_files:
                    self.selected_files.discard(item_path)
                    self.output_text.AppendText(f"Desmarcado (árvore): {os.path.basename(item_path)}\n")
                else:
                    self.selected_files.add(item_path)
                    self.output_text.AppendText(f"Marcado (árvore): {os.path.basename(item_path)}\n")
                self._update_tree_item_image(tree_item) 
                self._update_parents_images(tree_item)  # _update_parents_images já tem Freeze/Thaw interno

            elif os.path.isdir(item_path):
                descendant_files = self._get_all_descendant_files_from_os_path(item_path)
                current_state = self._get_tree_item_state(tree_item) 

                if current_state == "checked": 
                    for f in descendant_files:
                        if f in self.selected_files:
                            self.selected_files.discard(f)
                    self.output_text.AppendText(f"Pasta desmarcada (árvore): {os.path.basename(item_path)} e seus conteúdos\n")
                else: 
                    for f in descendant_files:
                        self.selected_files.add(f)
                    self.output_text.AppendText(f"Pasta marcada (árvore): {os.path.basename(item_path)} e seus conteúdos\n")
                
                # _update_all_tree_item_images já tem Freeze/Thaw interno
                self._update_all_tree_item_images(tree_item) 
                self._update_parents_images(tree_item) # _update_parents_images já tem Freeze/Thaw interno
        finally:
            self.file_tree.Thaw()
            
        event.Skip()

    def on_tree_selection_changed(self, event):
        pass

    def setup_random_union_panel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(self.random_union_panel, label="Adicione arquivos de qualquer local para uni-los:")
        sizer.Add(instructions, 0, wx.ALL, 10)

        self.random_files_checklist = wx.CheckListBox(self.random_union_panel, choices=[], style=wx.LB_MULTIPLE)
        self.random_files_checklist.Bind(wx.EVT_CHECKLISTBOX, self.on_random_file_checklist_toggled)
        sizer.Add(self.random_files_checklist, 1, wx.EXPAND | wx.ALL, 10)

        drop_target = FileListDropTarget(self.random_files_checklist, self.add_arbitrary_files_to_list)
        self.random_files_checklist.SetDropTarget(drop_target)
        self.random_union_panel.SetDropTarget(drop_target)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_files_button = wx.Button(self.random_union_panel, label="Adicionar Arquivos...")
        add_files_button.Bind(wx.EVT_BUTTON, self.on_add_arbitrary_files_button)
        
        remove_selected_button = wx.Button(self.random_union_panel, label="Remover Selecionados da Lista")
        remove_selected_button.Bind(wx.EVT_BUTTON, self.on_remove_selected_arbitrary_files)

        clear_list_button = wx.Button(self.random_union_panel, label="Limpar Lista")
        clear_list_button.Bind(wx.EVT_BUTTON, self.on_clear_arbitrary_files_list)

        button_sizer.Add(add_files_button, 1, wx.ALL | wx.EXPAND, 5)
        button_sizer.Add(remove_selected_button, 1, wx.ALL | wx.EXPAND, 5)
        button_sizer.Add(clear_list_button, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.random_union_panel.SetSizer(sizer)

    def on_add_arbitrary_files_button(self, event):
        with wx.FileDialog(self, "Selecione arquivos para unir", wildcard="Todos os arquivos (*.*)|*.*",
                           style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            paths = fileDialog.GetPaths()
            self.add_arbitrary_files_to_list(paths)

    def add_arbitrary_files_to_list(self, file_paths):
        self.random_files_checklist.Freeze()
        try:
            added_count = 0
            for path in file_paths:
                if path not in self.arbitrary_files_for_union:
                    self.arbitrary_files_for_union.append(path)
                    added_count +=1
            
            # ALTERAÇÃO: Ordenar a lista completa antes de adicioná-la à UI
            sort_key_func = self.get_sort_key()
            self.arbitrary_files_for_union.sort(key=sort_key_func)
            self.random_files_checklist.Set(self.arbitrary_files_for_union)
            # Marcar todos como checados
            for i in range(self.random_files_checklist.GetCount()):
                self.random_files_checklist.Check(i)

            if added_count > 0:
                self.output_text.AppendText(f"{added_count} arquivo(s) avulso(s) adicionado(s) à lista para união.\n")
        finally:
            self.random_files_checklist.Thaw()


    def on_random_file_checklist_toggled(self, event):
        pass 

    def on_remove_selected_arbitrary_files(self, event):
        selected_indices = self.random_files_checklist.GetCheckedItems()
        if not selected_indices: return

        self.random_files_checklist.Freeze()
        try:
            removed_count = 0
            # Ordenar índices em reverso para evitar problemas ao deletar
            for index in sorted(selected_indices, reverse=True):
                path_to_remove = self.random_files_checklist.GetString(index)
                if path_to_remove in self.arbitrary_files_for_union:
                    self.arbitrary_files_for_union.remove(path_to_remove)
                self.random_files_checklist.Delete(index)
                removed_count += 1
            if removed_count > 0:
                 self.output_text.AppendText(f"{removed_count} arquivo(s) avulso(s) removido(s) da lista.\n")
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


    def on_esc_pressed(self, event):
        current_page_idx = self.notebook.GetSelection()
        widget_to_focus = None
        if current_page_idx == 0:  
            self.extension_search.SetValue("")
            self.filter_extensions(None) # filter_extensions já tem Freeze/Thaw
            widget_to_focus = self.extension_search
        elif current_page_idx == 1:  
            self.file_search.SetValue("")
            self.filter_files(None) # filter_files já tem Freeze/Thaw
            widget_to_focus = self.file_search
        elif current_page_idx == 2:  
            self.text_file_list.Freeze()
            try:
                self.text_file_list.SetItems(self.all_files) 
                for i, file_path in enumerate(self.all_files):
                     self.text_file_list.Check(i, file_path in self.selected_files)
            finally:
                self.text_file_list.Thaw()
            widget_to_focus = self.text_input 
        elif current_page_idx == 3: 
            widget_to_focus = self.file_tree
        elif current_page_idx == 4: 
            widget_to_focus = self.random_files_checklist
        
        if widget_to_focus:
            widget_to_focus.SetFocus()

    def filter_extensions(self, event):
        search_term = self.extension_search.GetValue().lower()
        filtered_extensions = [ext for ext in self.all_extensions if search_term in ext.lower()]
        
        self.extension_checklist.Freeze()
        try:
            self.extension_checklist.Set(filtered_extensions)
            for i, ext in enumerate(filtered_extensions):
                if ext in self.selected_extensions:
                    self.extension_checklist.Check(i, True)
                else:
                    self.extension_checklist.Check(i, False)
        finally:
            self.extension_checklist.Thaw()


    def filter_files(self, event): 
        search_term = self.file_search.GetValue().lower()
        if not self.all_files: 
            self.file_list.Set([])
            return

        filtered_files = []
        if not search_term: 
            filtered_files = self.all_files
        else:
            filtered_files = [
                file for file in self.all_files
                if search_term in os.path.basename(file).lower() or \
                   search_term in os.path.dirname(file).lower() 
            ]
        
        self.file_list.Freeze()
        try:
            self.file_list.Set(filtered_files)
            for i, file_path in enumerate(filtered_files):
                if file_path in self.selected_files:
                     self.file_list.Check(i, True)
                else:
                    self.file_list.Check(i, False)
        finally:
            self.file_list.Thaw()


    def on_extension_checked(self, event):
        index = event.GetInt()
        ext = self.extension_checklist.GetString(index)
        if self.extension_checklist.IsChecked(index):
            self.selected_extensions.add(ext)
        else:
            self.selected_extensions.discard(ext)

    def on_file_checked(self, event): 
        index = event.GetInt()
        file_path = self.file_list.GetString(index)
        if self.file_list.IsChecked(index):
            self.selected_files.add(file_path)
        else:
            self.selected_files.discard(file_path)
        
        # Sincronizar outras UIs
        self.Freeze() # Congela o frame principal para múltiplas atualizações
        try:
            self.filter_extensions(None) 
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
            if hasattr(self, 'text_file_list'):
                self.text_file_list.Freeze()
                try:
                    for i, fp_text in enumerate(self.text_file_list.GetStrings()): 
                        if fp_text in self.all_files: 
                             self.text_file_list.Check(i, fp_text in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
        finally:
            self.Thaw()


    def on_select_from_text_input(self, event):
        source_directory = self.source_dir_picker.GetPath()
        if not source_directory:
            wx.MessageBox("Selecione o diretório de Entrada primeiro.", "Erro", wx.OK | wx.ICON_ERROR)
            return

        input_text = self.text_input.GetValue().strip()
        
        self.Freeze() # Congelar frame para múltiplas atualizações de UI
        try:
            if not input_text:
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files) 
                    for i, file_path in enumerate(self.all_files): 
                        self.text_file_list.Check(i, file_path in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
                return

            raw_entries = re.split(r'[,\s\n]+', input_text)
            search_terms = []
            for entry in raw_entries:
                entry = entry.strip()
                if not entry: continue
                match = re.match(r'\s*(?:modified:|new file:|deleted:|renamed:)?\s*(?P<filepath>[^\s].*?)(?:\s*->\s*.*)?$', entry)
                term = match.group('filepath').strip() if match else entry
                if "->" in term: 
                    term = term.split("->")[-1].strip()
                search_terms.append(term)
            
            if not search_terms: 
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files)
                    for i, file_path in enumerate(self.all_files):
                        self.text_file_list.Check(i, file_path in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
                return

            found_files_for_this_search = set()
            for full_path in self.all_files: 
                basename = os.path.basename(full_path)
                name_no_ext, _ = os.path.splitext(basename)
                
                try:
                    relative_path_from_source = os.path.relpath(full_path, source_directory).replace("\\", "/")
                except ValueError: 
                    relative_path_from_source = basename.replace("\\","/") 

                for term in search_terms:
                    term_lower = term.lower()
                    term_as_path_lower = term.replace("\\", "/").lower()
                    normalized_full_path_lower = full_path.replace("\\", "/").lower()

                    matched = False
                    if "/" in term or "\\" in term: 
                        if normalized_full_path_lower.endswith(term_as_path_lower):
                            matched = True
                        elif relative_path_from_source.lower() == term_as_path_lower:
                            matched = True
                    else: 
                        if term_lower == basename.lower(): 
                            matched = True
                        elif term_lower == name_no_ext.lower(): 
                            matched = True
                    
                    if matched:
                        found_files_for_this_search.add(full_path)
                        break 
            
            self.selected_files.clear() 

            # ALTERAÇÃO: Ordenar a lista encontrada antes de exibir
            sort_key_func = self.get_sort_key()
            paths_to_display_in_list = sorted(list(found_files_for_this_search), key=sort_key_func)
            
            self.text_file_list.Freeze()
            try:
                self.text_file_list.SetItems(paths_to_display_in_list)
                for i, file_path_in_list in enumerate(paths_to_display_in_list):
                    self.text_file_list.Check(i, True) 
                    self.selected_files.add(file_path_in_list) 
            finally:
                self.text_file_list.Thaw()

            if not found_files_for_this_search:
                wx.MessageBox("Nenhum arquivo correspondente encontrado no diretório de Entrada para os termos fornecidos.", "Aviso", wx.OK | wx.ICON_WARNING)
            else:
                self.output_text.AppendText(f"{len(self.selected_files)} arquivo(s) selecionado(s) pela busca por nome.\n")

            self.filter_extensions(None) 
            self.filter_files(None)      
            
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                 self._update_all_tree_item_images(self.file_tree.GetRootItem())
        finally:
            self.Thaw()


    def on_text_file_list_checked(self, event): 
        index = event.GetInt()
        file_path = self.text_file_list.GetString(index)
        if self.text_file_list.IsChecked(index):
            self.selected_files.add(file_path)
        else:
            if file_path in self.selected_files: 
                self.selected_files.discard(file_path)
        
        self.Freeze()
        try:
            self.filter_extensions(None)
            self.filter_files(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
        finally:
            self.Thaw()


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
                wx.MessageBox(f"Não foi possível criar o diretório de Saída: {output_directory}", "Erro", wx.OK | wx.ICON_ERROR)
                return

        current_page_idx = self.notebook.GetSelection()
        page_title = self.notebook.GetPageText(current_page_idx)
        files_to_process = [] 

        self.output_text.SetValue(f"Iniciando cópia (aba: {page_title})...\n")
        self.output_text.AppendText(f"Diretório de Saída: {output_directory}\n")

        if page_title == "Selecionar Extensões":
            if not source_directory:
                wx.MessageBox("Selecione o diretório de Entrada para copiar por extensões.", "Erro", wx.OK | wx.ICON_ERROR)
                return
            selected_exts = list(self.selected_extensions)
            if not selected_exts:
                wx.MessageBox("Selecione pelo menos uma extensão.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_extensions(source_directory, output_directory, selected_exts)
            return 

        elif page_title == "Selecionar Arquivos":
            if not source_directory: 
                wx.MessageBox(f"Selecione o diretório de Entrada para a aba '{page_title}'.", "Erro", wx.OK | wx.ICON_ERROR)
                return
            files_to_process = [self.file_list.GetString(i) for i in self.file_list.GetCheckedItems()]
            files_to_process = [f for f in files_to_process if f.startswith(source_directory)]
            
            if not files_to_process:
                wx.MessageBox("Nenhum arquivo selecionado na aba 'Selecionar Arquivos' para copiar.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_selected_file_paths(source_directory, output_directory, files_to_process)
            return

        elif page_title == "Buscar por Nome":
            if not source_directory: 
                wx.MessageBox(f"Selecione o diretório de Entrada para a aba '{page_title}'.", "Erro", wx.OK | wx.ICON_ERROR)
                return
            files_to_process = [self.text_file_list.GetString(i) for i in self.text_file_list.GetCheckedItems()]
            files_to_process = [f for f in files_to_process if f.startswith(source_directory)]

            if not files_to_process:
                wx.MessageBox("Nenhum arquivo selecionado na aba 'Buscar por Nome' para copiar.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_selected_file_paths(source_directory, output_directory, files_to_process)
            return
            
        elif page_title == "Explorador de Arquivos":
            if not source_directory: 
                wx.MessageBox(f"Selecione o diretório de Entrada para a aba '{page_title}'.", "Erro", wx.OK | wx.ICON_ERROR)
                return
            # ALTERAÇÃO: Ordenar a lista final de arquivos selecionados antes de copiar
            sort_key_func = self.get_sort_key()
            files_to_process = sorted([f for f in list(self.selected_files) if f.startswith(source_directory)], key=sort_key_func)


            if not files_to_process:
                wx.MessageBox("Nenhum arquivo selecionado na aba 'Explorador de Arquivos' para copiar.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_by_selected_file_paths(source_directory, output_directory, files_to_process)
            return
        
        elif page_title == "Unir Arquivos Avulsos":
            files_to_process = [self.random_files_checklist.GetString(i) for i in self.random_files_checklist.GetCheckedItems()]
            if not files_to_process:
                wx.MessageBox("Nenhum arquivo avulso selecionado na lista para unir.", "Aviso", wx.OK | wx.ICON_WARNING)
                return
            self.copy_arbitrary_files(output_directory, files_to_process)
            return
        else:
            wx.MessageBox(f"Lógica de cópia não implementada para a aba: {page_title}", "Erro", wx.OK | wx.ICON_ERROR)
            return


    def copy_by_extensions(self, source_dir, output_dir, sel_extensions):
        output_file_path = os.path.join(output_dir, "codigo_completo.txt")
        self.output_text.AppendText(f"Copiando arquivos de: {source_dir} com extensões: {sel_extensions}\n")
        files_copied_count = 0
        sort_key_func = self.get_sort_key() # NOVO: Obter a função de ordenação

        with open(output_file_path, "w", encoding="utf-8", errors="ignore") as f_out:
            root_node = TreeNode(os.path.basename(source_dir) or source_dir)
            
            def _process_dir_for_extensions(current_dir, current_treenode):
                nonlocal files_copied_count
                try:
                    # ALTERAÇÃO: Usar a função de ordenação ao listar o diretório
                    items_in_dir = sorted(os.listdir(current_dir), key=sort_key_func)
                except OSError as e:
                    self.output_text.AppendText(f"Erro ao listar diretório {current_dir}: {e}\n")
                    return

                for item in items_in_dir:
                    item_path = os.path.join(current_dir, item)
                    if os.path.isdir(item_path):
                        child_node = TreeNode(item)
                        current_treenode.add_child(child_node)
                        _process_dir_for_extensions(item_path, child_node)
                    elif os.path.splitext(item)[1] in sel_extensions:
                        # self.output_text.AppendText(f"- {item} (de {os.path.relpath(item_path, source_dir)})\n") # Pode ser lento
                        f_out.write(f"==========================================\n")
                        f_out.write(f"Conteúdo de {os.path.basename(item)} (caminho: {os.path.relpath(item_path, source_dir)}):\n")
                        f_out.write(f"==========================================\n")
                        try:
                            with open(item_path, "r", encoding="utf-8", errors="ignore") as code_file:
                                f_out.write(code_file.read() + "\n\n")
                            current_treenode.add_child(TreeNode(item)) 
                            files_copied_count +=1
                        except Exception as e:
                            self.output_text.AppendText(f"Erro ao ler {item}: {e}\n") # Log de erro é importante
                            f_out.write(f"[Erro ao ler arquivo: {e}]\n\n")
                wx.YieldIfNeeded() # Permite que a UI processe eventos durante loops longos

            _process_dir_for_extensions(source_dir, root_node) 

            f_out.write("\n==========================================\n")
            f_out.write("Estrutura de pastas (relativa à Entrada):\n")
            f_out.write("==========================================\n")
            f_out.write(root_node.print_tree())
        
        self.output_text.AppendText(f"\nCópia por extensões concluída. {files_copied_count} arquivo(s) copiado(s) para {output_file_path}\n")
        if files_copied_count > 0 :
            wx.MessageBox(f"{files_copied_count} arquivo(s) copiado(s) para {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"Nenhum arquivo encontrado com as extensões selecionadas em {source_dir}.", "Aviso", wx.OK | wx.ICON_WARNING)


    def copy_by_selected_file_paths(self, source_dir, output_dir, sel_files_paths):
        output_file_path = os.path.join(output_dir, "codigo_completo.txt")
        self.output_text.AppendText(f"Copiando {len(sel_files_paths)} arquivo(s) selecionado(s) de: {source_dir}\n")
        files_copied_count = 0
        
        # ALTERAÇÃO: Garantir que a lista de arquivos esteja ordenada antes de processar.
        # A lista já deve vir ordenada da chamada em `on_copy`, mas garantimos aqui.
        sort_key_func = self.get_sort_key()
        sel_files_paths.sort(key=sort_key_func)

        if not sel_files_paths: 
             common_prefix_for_tree = source_dir
        else:
            common_prefix_for_tree = os.path.commonpath(sel_files_paths)
            if not os.path.isdir(common_prefix_for_tree): 
                common_prefix_for_tree = os.path.dirname(common_prefix_for_tree)
        
        if common_prefix_for_tree.startswith(source_dir) and common_prefix_for_tree != source_dir :
            root_node_name_for_tree = os.path.relpath(common_prefix_for_tree, os.path.dirname(source_dir))
        elif common_prefix_for_tree == source_dir:
             root_node_name_for_tree = os.path.basename(source_dir)
        else: 
            root_node_name_for_tree = os.path.basename(common_prefix_for_tree or "arquivos_selecionados")

        root_node_for_text_output = TreeNode(root_node_name_for_tree or "Raiz")

        with open(output_file_path, "w", encoding="utf-8", errors="ignore") as f_out:
            for i, file_path in enumerate(sel_files_paths): # Adicionado i para wx.YieldIfNeeded
                try:
                    rel_path_for_tree_structure = os.path.relpath(file_path, common_prefix_for_tree)
                except ValueError: 
                    rel_path_for_tree_structure = os.path.basename(file_path)

                parts = rel_path_for_tree_structure.split(os.sep)
                current_node_for_text = root_node_for_text_output
                
                for idx_part, part_name in enumerate(parts): # Renomeado i para idx_part
                    is_last_part = (idx_part == len(parts) - 1)
                    found_node = None
                    for child in current_node_for_text.children:
                        if child.name == part_name:
                            found_node = child
                            break
                    if found_node:
                        current_node_for_text = found_node
                    else:
                        new_node = TreeNode(part_name) 
                        current_node_for_text.add_child(new_node)
                        current_node_for_text = new_node
                    
                path_header_in_txt = os.path.relpath(file_path, source_dir)
                # self.output_text.AppendText(f"- {os.path.basename(file_path)} (de {path_header_in_txt})\n") # Pode ser lento
                f_out.write(f"==========================================\n")
                f_out.write(f"Conteúdo de {os.path.basename(file_path)} (caminho: {path_header_in_txt}):\n")
                f_out.write(f"==========================================\n")
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as code_file:
                        f_out.write(code_file.read() + "\n\n")
                    files_copied_count += 1
                except Exception as e:
                    self.output_text.AppendText(f"Erro ao ler {os.path.basename(file_path)}: {e}\n")
                    f_out.write(f"[Erro ao ler arquivo: {e}]\n\n")
                if i % 10 == 0: # A cada 10 arquivos, por exemplo
                    wx.YieldIfNeeded()
            
            f_out.write("\n==========================================\n")
            f_out.write("Estrutura de pastas (arquivos selecionados, relativa ao ancestral comum ou Entrada):\n")
            f_out.write("==========================================\n")
            f_out.write(root_node_for_text_output.print_tree())

        self.output_text.AppendText(f"\nCópia de arquivos selecionados concluída. {files_copied_count} arquivo(s) copiado(s) para {output_file_path}\n")
        wx.MessageBox(f"{files_copied_count} arquivo(s) copiado(s) para {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)


    def copy_arbitrary_files(self, output_dir, arbitrary_file_paths):
        output_file_path = os.path.join(output_dir, "codigo_completo.txt")
        self.output_text.AppendText(f"Unindo {len(arbitrary_file_paths)} arquivo(s) avulso(s)...\n")
        files_copied_count = 0

        # ALTERAÇÃO: Ordenar a lista de arquivos avulsos antes de processar
        sort_key_func = self.get_sort_key()
        arbitrary_file_paths.sort(key=sort_key_func)

        with open(output_file_path, "w", encoding="utf-8", errors="ignore") as f_out:
            
            for i, file_path in enumerate(arbitrary_file_paths): # Adicionado i
                # self.output_text.AppendText(f"- {os.path.basename(file_path)} (de {file_path})\n") # Pode ser lento
                f_out.write(f"==========================================\n")
                f_out.write(f"Conteúdo de {os.path.basename(file_path)} (caminho original: {file_path}):\n")
                f_out.write(f"==========================================\n")
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as code_file:
                        f_out.write(code_file.read() + "\n\n")
                    files_copied_count +=1
                except Exception as e:
                    self.output_text.AppendText(f"Erro ao ler {os.path.basename(file_path)}: {e}\n")
                    f_out.write(f"[Erro ao ler arquivo: {e}]\n\n")
                if i % 10 == 0:
                    wx.YieldIfNeeded()

            f_out.write("\n==========================================\n")
            f_out.write("Arquivos Avulsos Incluídos (Caminhos Originais):\n")
            f_out.write("==========================================\n")
            for file_path in arbitrary_file_paths:
                 f_out.write(f"- {file_path}\n")

        self.output_text.AppendText(f"\nUnião de arquivos avulsos concluída. {files_copied_count} arquivo(s) processado(s) para {output_file_path}\n")
        if files_copied_count > 0:
            wx.MessageBox(f"{files_copied_count} arquivo(s) avulso(s) unido(s) em {output_file_path}", "Sucesso", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"Nenhum arquivo avulso processado.", "Aviso", wx.OK | wx.ICON_WARNING)


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

            self.output_text.Clear()
            self.output_text.AppendText("Todos os campos e seleções foram limpos.\n")
        finally:
            self.Thaw()


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
            
            self.filter_extensions(None) 
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                 self._update_all_tree_item_images(self.file_tree.GetRootItem())
            if hasattr(self, 'text_file_list'):
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files) 
                    for i, fp in enumerate(self.all_files):
                         self.text_file_list.Check(i, fp in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
        finally:
            self.Thaw()


    def deselect_all_files_tab(self, event): 
        self.Freeze()
        try:
            self.file_list.Freeze()
            try:
                for i in range(self.file_list.GetCount()):
                    file_path_in_list = self.file_list.GetString(i)
                    self.file_list.Check(i, False)
                    if file_path_in_list in self.selected_files:
                         self.selected_files.discard(file_path_in_list)
            finally:
                self.file_list.Thaw()
            
            self.filter_extensions(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
            if hasattr(self, 'text_file_list'):
                self.text_file_list.Freeze()
                try:
                    self.text_file_list.SetItems(self.all_files)
                    for i, fp in enumerate(self.all_files):
                        self.text_file_list.Check(i, fp in self.selected_files)
                finally:
                    self.text_file_list.Thaw()
        finally:
            self.Thaw()


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

    def deselect_all_text_files_list(self, event): 
        self.Freeze()
        try:
            self.text_file_list.Freeze()
            try:
                for i in range(self.text_file_list.GetCount()):
                    file_path_in_list = self.text_file_list.GetString(i)
                    self.text_file_list.Check(i, False)
                    if file_path_in_list in self.selected_files:
                        self.selected_files.discard(file_path_in_list)
            finally:
                self.text_file_list.Thaw()
            
            self.filter_extensions(None)
            self.filter_files(None)
            if hasattr(self, 'file_tree') and self.file_tree.GetRootItem().IsOk():
                self._update_all_tree_item_images(self.file_tree.GetRootItem())
        finally:
            self.Thaw()


if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
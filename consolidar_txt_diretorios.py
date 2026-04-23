import os
import re

# Função para a chave de ordenação natural
def natural_sort_key(s):
    """
    Retorna uma chave para ordenação natural (ex: 'item2' antes de 'item10').
    Converte a string em uma lista de strings e números.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class TreeNode:
    """Classe para representar nós da árvore (para a saída de texto)."""
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
        
        sorted_children = sorted(self.children, key=lambda c: natural_sort_key(c.name))
        
        num_children = len(sorted_children) # Usar sorted_children para o número de filhos
        for i, child in enumerate(sorted_children):
            tree_str += child.print_tree(level + 1, i == num_children - 1, prefix)
        return tree_str

def consolidar_diretorios(diretorio_raiz_entrada, diretorio_saida):
    """
    Consolida arquivos de texto de subdiretórios em arquivos únicos,
    nomeados de acordo com seus respectivos subdiretórios, e inclui uma estrutura de árvore.
    """
    # --- Validação de Caminhos ---
    if not os.path.isdir(diretorio_raiz_entrada):
        print(f"ERRO: O diretório raiz de entrada '{diretorio_raiz_entrada}' não foi encontrado ou não é um diretório válido.")
        return False # Retorna False para indicar falha

    try:
        if not os.path.exists(diretorio_saida):
            os.makedirs(diretorio_saida)
            print(f"INFO: Diretório de saída criado: '{diretorio_saida}'")
        elif not os.path.isdir(diretorio_saida):
            print(f"ERRO: O caminho de saída '{diretorio_saida}' existe, mas não é um diretório válido.")
            return False
    except OSError as e:
        print(f"ERRO: Não foi possível criar ou acessar o diretório de saída '{diretorio_saida}'. Detalhes: {e}")
        return False
    # --- Fim da Validação de Caminhos ---

    print(f"\nINFO: Iniciando o processo de consolidação de arquivos a partir de '{diretorio_raiz_entrada}'...")

    processado_algum_diretorio = False

    for root, dirs, files in os.walk(diretorio_raiz_entrada):
        arquivos_txt_no_subdiretorio = []
        for file in files:
            if file.lower().endswith(".txt"): # Usar .lower() para ser case-insensitive
                arquivos_txt_no_subdiretorio.append(os.path.join(root, file))

        # Se não houver arquivos TXT, pula para o próximo diretório
        if not arquivos_txt_no_subdiretorio:
            continue

        # Determina o nome para o arquivo consolidado de saída
        relative_path = os.path.relpath(root, diretorio_raiz_entrada)
        if relative_path == ".":
            # Se for o diretório raiz e contiver arquivos TXT, usa o nome do diretório raiz para o arquivo de saída
            nome_arquivo_consolidado = os.path.basename(diretorio_raiz_entrada) + ".txt"
        else:
            # Caso contrário, usa o nome do subdiretório
            nome_arquivo_consolidado = os.path.basename(root) + ".txt"

        print(f"\nINFO: Processando o diretório: '{root}'")
        print(f"INFO: O arquivo consolidado será salvo como '{nome_arquivo_consolidado}'")

        # Ordena os arquivos naturalmente
        arquivos_txt_no_subdiretorio.sort(key=natural_sort_key)

        conteudo_consolidado = []
        
        # Cria um TreeNode para o subdiretório atual
        no_subdiretorio = TreeNode(os.path.basename(root), root)

        for caminho_arquivo in arquivos_txt_no_subdiretorio:
            nome_arquivo = os.path.basename(caminho_arquivo)
            
            # Adiciona o arquivo à estrutura da árvore
            no_subdiretorio.add_child(TreeNode(nome_arquivo, caminho_arquivo))

            cabecalho = f"==========================================\nConteúdo de {nome_arquivo} (caminho: {caminho_arquivo}):\n==========================================\n"
            try:
                with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                conteudo_consolidado.append(cabecalho)
                conteudo_consolidado.append(conteudo)
                conteudo_consolidado.append("\n\n") # Adiciona alguma separação entre os conteúdos dos arquivos
                print(f"DEBUG: Conteúdo do arquivo '{nome_arquivo}' lido com sucesso.")
            except UnicodeDecodeError:
                # Tenta outra codificação se utf-8 falhar
                try:
                    with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                        conteudo = f.read()
                    conteudo_consolidado.append(cabecalho)
                    conteudo_consolidado.append(conteudo)
                    conteudo_consolidado.append("\n\n")
                    print(f"INFO: Conteúdo do arquivo '{nome_arquivo}' lido com sucesso usando codificação 'latin-1'.")
                except Exception as e:
                    print(f"AVISO: Erro ao ler o arquivo '{caminho_arquivo}' com utf-8 e latin-1. Detalhes: {e}. O conteúdo deste arquivo será ignorado.")
                    conteudo_consolidado.append(f"AVISO: Não foi possível ler o conteúdo de {nome_arquivo} (caminho: {caminho_arquivo}). Ocorreu um erro na leitura do arquivo.\n\n")
            except Exception as e:
                print(f"AVISO: Erro inesperado ao ler o arquivo '{caminho_arquivo}'. Detalhes: {e}. O conteúdo deste arquivo será ignorado.")
                conteudo_consolidado.append(f"AVISO: Não foi possível ler o conteúdo de {nome_arquivo} (caminho: {caminho_arquivo}). Ocorreu um erro inesperado.\n\n")

        # Adiciona a estrutura da árvore binária no final
        conteudo_consolidado.append("==========================================\nEstrutura de Pastas e Arquivos Consolidados:\n==========================================\n")
        conteudo_consolidado.append(no_subdiretorio.print_tree())
        
        caminho_arquivo_saida = os.path.join(diretorio_saida, nome_arquivo_consolidado)
        try:
            with open(caminho_arquivo_saida, 'w', encoding='utf-8') as outfile:
                outfile.writelines(conteudo_consolidado)
            print(f"SUCESSO: Arquivos do diretório '{root}' consolidados em '{caminho_arquivo_saida}'.")
            processado_algum_diretorio = True
        except Exception as e:
            print(f"ERRO: Não foi possível escrever o arquivo consolidado em '{caminho_arquivo_saida}'. Detalhes: {e}")
            # Não retorna False aqui, para permitir que outros diretórios sejam processados

    if not processado_algum_diretorio:
        print("\nINFO: Nenhuma pasta com arquivos TXT foi encontrada para consolidação no diretório raiz fornecido.")
        return False
    
    return True # Retorna True para indicar sucesso geral

if __name__ == "__main__":
    print("=========================================================================")
    print("                  Ferramenta de Consolidação de TXT                      ")
    print("=========================================================================")
    print("Este script irá consolidar arquivos TXT de múltiplos subdiretórios.")
    print("Para cada subdiretório (ou o diretório raiz se contiver TXTs),")
    print("será criado um arquivo de saída único com o nome do diretório.")
    print("No final de cada arquivo consolidado, haverá uma estrutura de árvore.")
    print("Os arquivos dentro de cada subdiretório serão ordenados naturalmente.")
    print("-------------------------------------------------------------------------")

    while True:
        diretorio_raiz_entrada = input("\n[PASSO 1/2] Por favor, insira o CAMINHO COMPLETO para o diretório raiz (onde estão os subdiretórios com os arquivos TXT): ")
        if not os.path.isdir(diretorio_raiz_entrada):
            print(f"ATENÇÃO: O caminho '{diretorio_raiz_entrada}' não é um diretório válido ou não existe. Por favor, tente novamente.")
        else:
            break

    while True:
        diretorio_saida = input("[PASSO 2/2] Por favor, insira o CAMINHO COMPLETO para o diretório de saída (onde os arquivos consolidados serão salvos, ex: C:\\Users\\SeuUsuario\\Desktop): ")
        if not os.path.exists(diretorio_saida):
            try:
                os.makedirs(diretorio_saida)
                print(f"INFO: Diretório de saída '{diretorio_saida}' criado com sucesso.")
                break
            except OSError as e:
                print(f"ATENÇÃO: Não foi possível criar o diretório de saída '{diretorio_saida}'. Detalhes: {e}. Por favor, verifique as permissões ou tente outro caminho.")
        elif not os.path.isdir(diretorio_saida):
            print(f"ATENÇÃO: O caminho '{diretorio_saida}' existe, mas não é um diretório. Por favor, insira um caminho para um diretório válido.")
        else:
            break

    print("\n--- INICIANDO PROCESSAMENTO ---")
    sucesso_geral = consolidar_diretorios(diretorio_raiz_entrada, diretorio_saida)

    print("\n--- PROCESSO CONCLUÍDO ---")
    if sucesso_geral:
        print("A consolidação de arquivos foi concluída com sucesso.")
        print(f"Verifique os arquivos gerados em: '{diretorio_saida}'")
    else:
        print("Ocorreram erros durante o processo de consolidação ou nenhuma pasta com TXT foi encontrada.")
        print("Por favor, revise as mensagens de ERRO/AVISO acima e verifique os caminhos informados.")

    input("\nPressione Enter para sair.")
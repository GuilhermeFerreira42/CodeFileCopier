## **📌 Visão Geral**
O **Copiador de Código Avançado** é uma ferramenta desenvolvida em Python com interface gráfica (wxPython) que permite consolidar o conteúdo de múltiplos arquivos de código-fonte em um único arquivo de texto (`codigo_completo.txt`). Ele é ideal para preparar contextos para análise por Inteligências Artificiais ou para arquivar versões de projetos.

**Principais Capacidades:**
✅ Seleção de arquivos por **extensão**.
✅ Seleção manual de arquivos em uma **lista detalhada**.
✅ **Busca flexível** por nomes ou caminhos de arquivos (compatível com saídas do `git status`).
✅ Navegação hierárquica em **árvore de diretórios com checkboxes** para seleção de pastas e arquivos.
✅ **União de arquivos avulsos** de diferentes locais do sistema.
✅ Cópia do conteúdo para um arquivo consolidado, mantendo a **estrutura de pastas** relativa na saída.
✅ Operação de cópia **específica para a aba ativa**, evitando interferência entre seleções de abas diferentes.

---

## **🛠️ Funcionalidades Detalhadas**

### **1. Pastas de Trabalho**
* **Entrada:** Diretório principal que contém os arquivos e pastas que você deseja processar. Pode ser selecionado clicando no botão ou arrastando uma pasta para o campo.
* **Saída:** Diretório onde o arquivo `codigo_completo.txt` consolidado será salvo. Também suporta arrastar e soltar.

### **2. Abas de Seleção de Arquivos**
O programa organiza a seleção de arquivos em múltiplas abas para diferentes necessidades:

| **Aba** | **Descrição** | **Como Selecionar para Cópia** |
| :----------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ | :-------------------------------------------------------------- |
| **Selecionar Extensões** | Permite filtrar e selecionar arquivos com base em suas extensões (ex: `.py`, `.tsx`, `.html`) dentro do diretório de "Entrada".             | Marque as checkboxes das extensões desejadas.                 |
| **Selecionar Arquivos** | Exibe uma lista de todos os arquivos encontrados no diretório de "Entrada". Útil para selecionar arquivos individualmente de forma manual.   | Marque as checkboxes dos arquivos desejados na lista.         |
| **Buscar por Nome** | Permite colar texto (como a saída do `git status`) ou digitar nomes/caminhos de arquivos. O sistema buscará correspondências no diretório de "Entrada". | Após a busca, marque as checkboxes dos arquivos na lista de resultados. |
| **Explorador de Arquivos**| Apresenta uma visualização em árvore do diretório de "Entrada", similar a um explorador de arquivos, com checkboxes para cada item.           | Dê um duplo clique (ou Enter) em arquivos/pastas para marcar/desmarcar. A seleção de pastas afeta todos os seus descendentes. |
| **Unir Arquivos Avulsos**| Permite adicionar arquivos de quaisquer locais do seu sistema para serem unidos, independentemente do diretório de "Entrada".                  | Adicione arquivos à lista (arrastando ou pelo botão) e garanta que estejam marcados. |

### **3. Recursos Principais**
🔹 **Interface Intuitiva com Abas:** Navegação clara entre os diferentes modos de seleção.
🔹 **Drag-and-Drop:**
    * Arraste uma pasta para os campos "Entrada" ou "Saída" para selecioná-los rapidamente.
    * Arraste arquivos para a lista na aba "Unir Arquivos Avulsos".
🔹 **Busca Aprimorada na Aba "Texto":**
    * Cole diretamente a saída do comando `git status`. O sistema tentará identificar os arquivos modificados ou não rastreados.
    * Busca por nome de arquivo (com ou sem extensão) ou por partes do caminho.
    * Separe múltiplos termos de busca por espaço, vírgula ou nova linha.
🔹 **Navegação Hierárquica com Checkboxes (Aba "Explorador de Arquivos"):**
    * Visualize a estrutura de pastas do diretório de "Entrada".
    * Selecione/deselecione arquivos individuais ou pastas inteiras (incluindo subitens) com um duplo clique (ou Enter).
    * O estado visual (marcado, desmarcado, parcialmente marcado) é atualizado dinamicamente.
🔹 **Seleção em Massa:** Botões "Selecionar Tudo" / "Desmarcar Tudo" disponíveis nas abas de lista ("Extensões", "Arquivos", "Texto").
🔹 **Limpeza Rápida:**
    * **Tecla `ESC`**: Limpa o campo de pesquisa da aba ativa (Extensões, Arquivos) ou reseta a lista de resultados na aba "Texto" (mantendo o texto digitado).
    * **Botão "Limpar Tudo"**: Reseta todos os campos de diretório, seleções em todas as abas e a área de log.
🔹 **Estrutura de Pastas na Saída:** O arquivo `codigo_completo.txt` inclui uma representação da estrutura de pastas dos arquivos copiados, relativa ao diretório de "Entrada" ou ao ancestral comum dos arquivos selecionados. Para arquivos avulsos, lista seus caminhos originais.
🔹 **Log de Operações:** A área de texto na parte inferior da janela exibe o progresso da cópia e outras mensagens importantes.

---

## **🚀 Como Usar**

### **Passo 1: Configurar Diretórios**
1.  **Diretório de Entrada**: Clique no seletor ou arraste a pasta principal do seu projeto para o campo "Entrada:". Este é o diretório onde o programa procurará os arquivos nas abas "Extensões", "Arquivos", "Texto" e "Explorador de Arquivos".
2.  **Diretório de Saída**: Clique no seletor ou arraste uma pasta para o campo "Saída:". É aqui que o arquivo `codigo_completo.txt` será criado.

### **Passo 2: Selecionar Arquivos na Aba Desejada**
Escolha uma das abas e selecione os arquivos conforme a descrição abaixo:

* **Aba "Selecionar Extensões"**:
    1.  Digite no campo "Pesquisar extensões" para filtrar a lista (opcional).
    2.  Marque as caixas de seleção ao lado das extensões desejadas.
* **Aba "Selecionar Arquivos"**:
    1.  Digite no campo "Pesquisar arquivos" para filtrar a lista (opcional).
    2.  Marque as caixas de seleção ao lado dos arquivos que deseja incluir.
* **Aba "Buscar por Nome"**:
    1.  Cole ou digite os nomes/caminhos dos arquivos no campo de texto principal.
    2.  Clique em "Buscar e Selecionar na Lista Abaixo".
    3.  Os arquivos encontrados aparecerão na lista abaixo, já marcados. Você pode desmarcar os que não desejar.
* **Aba "Explorador de Arquivos"**:
    1.  Navegue pela árvore de diretórios.
    2.  Dê um duplo clique (ou pressione Enter) sobre um arquivo para marcá-lo/desmarcá-lo.
    3.  Dê um duplo clique (ou pressione Enter) sobre uma pasta para marcar/desmarcar todos os arquivos e subpastas dentro dela.
* **Aba "Unir Arquivos Avulsos"**:
    1.  Clique em "Adicionar Arquivos..." e selecione os arquivos de qualquer local.
    2.  Ou, arraste arquivos diretamente para a área da lista.
    3.  Certifique-se de que os arquivos que deseja unir estejam marcados na lista.

### **Passo 3: Iniciar a Cópia**
1.  Certifique-se de que a aba correta (com os arquivos que você quer copiar) esteja ativa.
2.  Clique no botão **`INICIAR CÓPIA`**.
3.  O sistema processará **apenas os arquivos selecionados na aba atualmente ativa**.
4.  O progresso será exibido na área de log e uma mensagem de sucesso aparecerá ao final.

---

## **⌨️ Atalhos**
| Tecla   | Ação na Aba Ativa                                                               |
| :------ | :------------------------------------------------------------------------------ |
| `ESC`   | Limpa o campo de pesquisa (Extensões, Arquivos). Reseta a lista de resultados (Texto). |
| `Enter` | (No Explorador de Arquivos) Ativa o item para marcar/desmarcar.                 |

---

## **📝 Exemplo de Saída (`codigo_completo.txt`)**
O arquivo gerado terá um formato similar a este:

```plaintext
==========================================
Conteúdo de nome_do_arquivo.ext (caminho: caminho/relativo/ao/diretorio_entrada/nome_do_arquivo.ext):
==========================================
[Conteúdo do primeiro arquivo selecionado]

==========================================
Conteúdo de outro_arquivo.py (caminho: outro/caminho/outro_arquivo.py):
==========================================
[Conteúdo do segundo arquivo selecionado]

...

==========================================
Estrutura de pastas (arquivos selecionados, relativa ao ancestral comum ou Entrada):
==========================================
Diretorio_Entrada/
├── subpasta1/
│   └── arquivo1.tsx
└── arquivo2.py
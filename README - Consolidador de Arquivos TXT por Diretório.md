# Consolidador de Arquivos TXT por Diretório

Este script Python automatiza a consolidação de múltiplos arquivos de texto (`.txt`) localizados em diferentes subdiretórios de um diretório raiz. Ele agrupa os conteúdos de todos os arquivos `.txt` de cada subdiretório em um único arquivo de saída, nomeado com o nome do respectivo subdiretório. Além disso, o script garante a ordenação natural dos arquivos e inclui uma estrutura de árvore detalhada ao final de cada arquivo consolidado.

## Recursos

* **Consolidação por Subdiretório:** Cada subdiretório (ou o diretório raiz, se contiver arquivos `.txt`) gera um arquivo consolidado próprio.
* **Ordenação Natural:** Os arquivos dentro de cada diretório são ordenados de forma natural (ex: `1.txt`, `2.txt`, `10.txt`, em vez de `1.txt`, `10.txt`, `2.txt`).
* **Formato de Saída Detalhado:**
    * Cada conteúdo de arquivo é precedido por um cabeçalho indicando o nome do arquivo original e seu caminho completo.
    * Uma representação em árvore dos arquivos consolidados é anexada ao final de cada arquivo de saída.
* **Robustez e Feedback:**
    * Validação rigorosa dos caminhos de entrada e saída.
    * Criação automática do diretório de saída, se necessário.
    * Mensagens informativas (`INFO`, `SUCESSO`, `AVISO`, `ERRO`, `DEBUG`) durante todo o processo.
    * Tratamento de erros de leitura de arquivos (tentando múltiplas codificações).
    * A janela do console permanece aberta ao final para visualização do feedback.

## Como Usar

1.  **Pré-requisitos:** Certifique-se de ter o Python 3 instalado em seu sistema.
2.  **Salve o Script:** Salve o código fornecido em um arquivo chamado `consolidar_txt_diretorios.py` (ou o nome que preferir).
3.  **Abra o Terminal/Prompt de Comando:**
    * **Windows:** Pesquise por "CMD" ou "Prompt de Comando".
    * **macOS/Linux:** Abra o aplicativo "Terminal".
4.  **Navegue até a Pasta do Script:** Use o comando `cd` (change directory) para ir até a pasta onde você salvou o arquivo `consolidar_txt_diretorios.py`.
    * Exemplo: `cd C:\MeusScriptsPython`
5.  **Execute o Script:** Digite o seguinte comando e pressione Enter:
    ```bash
    python consolidar_txt_diretorios.py
    ```
6.  **Forneça os Caminhos:** O script irá solicitar que você insira os caminhos completos:
    * **Diretório Raiz de Entrada:** O caminho para a pasta principal que contém todos os subdiretórios com seus arquivos `.txt`.
        * Exemplo: `C:\Meus Documentos\Minhas Aulas de DVDs`
    * **Diretório de Saída:** O caminho para a pasta onde os novos arquivos consolidados serão salvos.
        * Exemplo: `C:\Users\SeuUsuario\Desktop\Aulas Consolidadas`
7.  **Acompanhe o Processo:** O script exibirá mensagens de progresso e status no terminal.
8.  **Verifique os Resultados:** Após a conclusão, os arquivos `.txt` consolidados estarão no diretório de saída especificado.

## Exemplo de Estrutura de Diretórios de Entrada
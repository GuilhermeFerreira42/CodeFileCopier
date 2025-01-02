
# Copiar Arquivos de Código com Estrutura de Árvore Binária

## Sobre o Projeto
Este é um programa em Python com interface gráfica (GUI) desenvolvida em wxPython. O objetivo é copiar recursivamente todos os arquivos de código de um diretório selecionado para um único arquivo de saída, incluindo uma representação da estrutura do diretório em formato de árvore binária.

## Funcionalidades
- Interface gráfica intuitiva para selecionar diretórios de origem e saída.
- Copia arquivos de código com extensões suportadas (como `.py`, `.java`, `.c`, `.cpp`, `.js`, `.html`, `.css`).
- Gera um arquivo `codigo_completo.txt` com:
  - O conteúdo dos arquivos de código copiados.
  - Uma representação hierárquica da estrutura do diretório em formato de árvore binária.

## Tecnologias Utilizadas
- **Python 3.10+**
- **wxPython** para criação da interface gráfica

## Como Usar

### 1. Instale as Dependências
Certifique-se de que o wxPython esteja instalado em seu ambiente Python:
```bash
pip install wxPython
```

### 2. Execute o Programa
Salve o código do programa em um arquivo `copiar_codigo.py` e execute-o:
```bash
python copiar_codigo.py
```

### 3. Selecione os Diretórios
- Escolha o diretório de origem onde estão os arquivos de código.
- Escolha o diretório de saída onde o arquivo `codigo_completo.txt` será gerado.

### 4. Clique no Botão "Copiar Arquivos"
O programa irá:
- Copiar os arquivos de código para o arquivo de saída.
- Gerar a estrutura de diretórios em formato de árvore binária e adicioná-la ao final do arquivo.

### 5. Confira a Saída
O arquivo `codigo_completo.txt` conterá:
- O conteúdo de todos os arquivos de código encontrados.
- A representação da árvore binária dos diretórios.

## Estrutura do Arquivo de Saída
Exemplo de conteúdo do arquivo `codigo_completo.txt`:

```
Conteúdo de exemplo.py:
print("Hello, World!")

Conteúdo de main.c:
#include <stdio.h>
int main() {
    printf("Hello, World!\n");
    return 0;
}

==========================================
Estrutura de pastas:
==========================================
root_directory
    folder1
        file1.py
        file2.java
    folder2
        file3.c
        file4.html
```

## Observações
1. Apenas arquivos com extensões suportadas serão incluídos no arquivo de saída.
2. Certifique-se de ter permissões de leitura nos diretórios de origem e de escrita no diretório de saída.

## Contribuição
Sinta-se à vontade para contribuir com melhorias ou sugerir novos recursos. 

## Licença
Este projeto está licenciado sob a Licença MIT.

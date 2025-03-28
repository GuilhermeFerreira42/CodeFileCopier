# Copiador de Arquivos de Código

Uma aplicação gráfica para copiar arquivos de código com diferentes métodos de seleção.

## Funcionalidades

- Seleção por extensão de arquivo
- Busca por nome de arquivo
- Seleção por lista de nomes de arquivos
- Interface gráfica intuitiva
- Suporte a múltipla seleção de arquivos
- Copia em lote para diretório de destino

## Requisitos

- Python 3.6 ou superior
- wxPython 4.2.1

## Instalação

1. Clone este repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Uso

Execute o programa:
```bash
python code_file_copier.py
```

### Abas Disponíveis

1. **Por Extensão**
   - Selecione o diretório de origem
   - Digite as extensões dos arquivos (separadas por vírgula)
   - Selecione os arquivos desejados

2. **Por Busca**
   - Selecione o diretório de origem
   - Digite o termo de busca
   - Selecione os arquivos desejados

3. **Por Texto**
   - Selecione o diretório de origem
   - Digite os nomes dos arquivos (separados por vírgula ou nova linha)
   - Clique em "Selecionar"
   - Selecione os arquivos desejados

### Atalhos

- **ESC**: Limpa o campo de busca nas abas 1 e 2, ou restaura a lista de arquivos na aba 3

### Copiando Arquivos

1. Selecione os arquivos desejados em qualquer uma das abas
2. Clique no botão "Copiar Arquivos"
3. Selecione o diretório de destino
4. Os arquivos serão copiados para o diretório selecionado

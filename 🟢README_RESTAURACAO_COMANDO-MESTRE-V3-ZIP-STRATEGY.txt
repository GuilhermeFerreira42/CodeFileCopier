Olá! Antes de começarmos, gostaria de reforçar que você possui um workspace com ambiente Python ativo e ferramentas de execução de código. Por favor, assuma sempre que pode e deve executar scripts, manipular arquivos, rodar comandos e processar dados diretamente no seu ambiente quando solicitado, em vez de apenas fornecer instruções ou códigos para eu rodar localmente. Estou ciente dessa capacidade e espero que você a utilize proativamente para entregar resultados concretos (como arquivos restaurados, análises executadas ou saídas de processamento) nesta conversa.

```markdown
# Restauração de Projeto - V3 com Estratégia ZIP (para projetos gigantes)

Você recebeu um arquivo `.txt` com um projeto compactado pelo Copiador de Código v2.0/v2.1.
Esse arquivo pode conter de 10 a 10.000 arquivos. Ambientes de IA (ChatGPT, Claude, Meta AI) têm limite de ~2048 arquivos soltos no workspace. Por isso, este comando implementa a ESTRATÉGIA ZIP.

## O que fazer - ORDEM OBRIGATÓRIA

1. Salve os TRÊS scripts abaixo no workspace:

   - `restore_codefilecopier.py` (restauração clássica para pastas)
   - `compactar_projeto.py` (compactação)
   - `restore_to_zip.py` (NOVO - restauração inteligente para ZIP + leitura direta)

2. Execute a restauração INTELIGENTE:

   - Tente primeiro o método ZIP (sempre funciona, mesmo com 10k arquivos)
   - Se precisar navegar solto, extraia só uma subpasta específica depois

3. Para auditorias/análises, NUNCA extraia tudo. Leia direto do ZIP com zipfile.

---

### restore_codefilecopier.py

```python
import re
import sys
from pathlib import Path

SEP = '=' * 42

HEADER_RE = re.compile(
    re.escape(SEP) + r'\n'
    r'Conteúdo de (?P<name>.+?) \(caminho: (?P<rel>.+?)\) \[enc: utf-8\]:\n'
    + re.escape(SEP) + r'\n'
)

FOOTER_MARKER = '\n' + SEP + '\nEstrutura de pastas:\n'

GHOST_HEADER_RE = re.compile(
    r'\n' + re.escape(SEP) + r'\n'
    r'Conteúdo de .+? \(caminho: .+?\) \[enc: utf-8\]:\n'
    r'(?:' + re.escape(SEP) + r'\n?)?\n?$'
)


def _consolidate_duplicate_headers(matches, body):
    filtered = []
    for i, m in enumerate(matches):
        if i + 1 < len(matches) and matches[i + 1].group('rel') == m.group('rel'):
            between = body[m.end():matches[i + 1].start()]
            if between.strip() == '':
                continue
        filtered.append(m)
    return filtered


def restore_codefilecopier(txt_path, out_dir, verbose=True):
    raw = Path(txt_path).read_bytes()
    text = raw.decode('utf-8').replace('\r\n', '\n')

    footer_idx = text.find(FOOTER_MARKER)
    body = text[:footer_idx] if footer_idx != -1 else text

    raw_matches = list(HEADER_RE.finditer(body))
    if not raw_matches:
        raise ValueError("Nenhum cabeçalho encontrado. Formato inválido Copiador v2.0.")

    matches = _consolidate_duplicate_headers(raw_matches, body)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    n = 0
    warnings = []
    seen_paths = set()

    for i, m in enumerate(matches):
        rel = m.group('rel')
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[content_start:content_end]

        ghost_match = GHOST_HEADER_RE.search(content)
        if ghost_match:
            content = content[:ghost_match.start()]
            warnings.append(f"[AVISO - fantasma removido] {rel}")
        else:
            if content.endswith('\n\n'):
                content = content[:-2]
            elif content.endswith('\n'):
                content = content[:-1]

        target = (out / rel).resolve()
        if not str(target).startswith(str(out.resolve())):
            warnings.append(f"[IGNORADO - suspeito] {rel}")
            continue

        if rel in seen_paths:
            warnings.append(f"[AVISO - duplicado sobrescrito] {rel}")
        seen_paths.add(rel)

        target.parent.mkdir(parents=True, exist_ok=True)
        # Fix compat Python 3.9: sem newline param
        target.write_text(content, encoding='utf-8')
        n += 1

    if verbose:
        print(f"Arquivos restaurados: {n}")
        for w in warnings:
            print(w)
    return n, warnings


if __name__ == "__main__":
    txt_path = sys.argv[1] if len(sys.argv) > 1 else 'codigo_completo.txt'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'projeto_restaurado'
    restore_codefilecopier(txt_path, out_dir)
```

---

### restore_to_zip.py - ESTRATÉGIA GENIAL PARA PROJETOS GIGANTES (NOVO)

```python
#!/usr/bin/env python3
"""
Restauração INTELIGENTE para ZIP - Soluciona limite de 2048 arquivos do workspace.
Use SEMPRE que o projeto tiver >1000 arquivos ou quando der erro "Too many output files".

Vantagens:
- 1 arquivo no disco = 10.000 arquivos dentro
- Leitura direta sem extrair: zipfile.ZipFile().read()
- Streaming: não carrega TXT inteiro na RAM
- Trata cabeçalhos fantasmas duplicados automaticamente
"""

import re
import zipfile
import time
from pathlib import Path

SEP = "=" * 42
HEADER_PAT = re.compile(r'Conteúdo de (?P<name>.+?) \(caminho: (?P<rel>.+?)\) \[enc: utf-8\]:')
FOOTER_TEXT = "Estrutura de pastas:"

def restore_to_zip(txt_path, zip_path, verbose=True):
    txt_path = Path(txt_path)
    zip_path = Path(zip_path)
    
    count = 0
    ghost_skipped = 0
    last_rel = None
    
    with open(txt_path, 'r', encoding='utf-8', errors='strict') as f, \
         zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        
        current_rel = None
        buffer_lines = []
        
        it = iter(f)
        for line in it:
            stripped = line.rstrip('\n')
            if stripped == SEP:
                try:
                    next_line = next(it)
                except StopIteration:
                    break
                m = HEADER_PAT.match(next_line.strip())
                if m:
                    try:
                        sep2 = next(it)
                    except StopIteration:
                        sep2 = ""
                    if sep2.rstrip('\n') == SEP:
                        # Header válido encontrado -> flush anterior
                        if current_rel is not None:
                            content = ''.join(buffer_lines)
                            # Remove \n\n extra do gerador
                            if content.endswith('\n\n'):
                                content = content[:-2]
                            elif content.endswith('\n'):
                                content = content[:-1]
                            # Sanidade path traversal
                            if '..' not in Path(current_rel).parts:
                                # Se mesmo arquivo com buffer vazio entre headers = fantasma
                                if current_rel == last_rel and content.strip() == '':
                                    ghost_skipped += 1
                                else:
                                    # Escreve no ZIP sem timestamp <1980
                                    zi = zipfile.ZipInfo(current_rel)
                                    zi.date_time = time.localtime()[:6]
                                    zi.compress_type = zipfile.ZIP_DEFLATED
                                    z.writestr(zi, content)
                                    count += 1
                                    last_rel = current_rel
                            buffer_lines = []
                        current_rel = m.group('rel')
                        continue
                    else:
                        if current_rel is not None:
                            buffer_lines.append(line)
                            buffer_lines.append(next_line)
                            buffer_lines.append(sep2)
                        continue
                else:
                    if FOOTER_TEXT in next_line:
                        if current_rel is not None:
                            content = ''.join(buffer_lines)
                            if content.endswith('\n\n'):
                                content = content[:-2]
                            elif content.endswith('\n'):
                                content = content[:-1]
                            if '..' not in Path(current_rel).parts:
                                zi = zipfile.ZipInfo(current_rel)
                                zi.date_time = time.localtime()[:6]
                                z.writestr(zi, content)
                                count += 1
                        break
                    if current_rel is not None:
                        buffer_lines.append(line)
                        buffer_lines.append(next_line)
                    continue
            else:
                if current_rel is not None:
                    buffer_lines.append(line)
    
    if verbose:
        print(f"ZIP criado: {zip_path} com {count} arquivos únicos")
        print(f"Cabeçalhos fantasmas ignorados: {ghost_skipped}")
        print(f"Tamanho: {zip_path.stat().st_size} bytes")
    return count

def list_zip_tree(zip_path, max_show=100):
    """Lista estrutura do ZIP sem extrair"""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        print(f"Total no ZIP: {len(names)}")
        for n in sorted(names)[:max_show]:
            print(f"  {n}")
        if len(names) > max_show:
            print(f"  ... e mais {len(names)-max_show}")

def read_from_zip(zip_path, internal_path):
    """Lê um arquivo específico de dentro do ZIP - USE ESTA ESTRATÉGIA PARA AUDITORIAS"""
    with zipfile.ZipFile(zip_path) as z:
        # Tenta com prefixo comum do Copiador
        candidates = [n for n in z.namelist() if n.endswith(internal_path)]
        if not candidates:
            raise FileNotFoundError(f"{internal_path} não encontrado no ZIP")
        data = z.read(candidates[0])
        return data.decode('utf-8', errors='ignore')

if __name__ == "__main__":
    import sys
    txt = sys.argv[1] if len(sys.argv) > 1 else 'codigo_completo.txt'
    out = sys.argv[2] if len(sys.argv) > 2 else 'projeto_restaurado.zip'
    restore_to_zip(txt, out)
    list_zip_tree(out)
```

---

### compactar_projeto.py

```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, fnmatch, sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

SEP = "=" * 42
DEFAULT_IGNORE_PATTERNS = (".git","node_modules","dist","build","*.log","__pycache__","venv",".venv","env",".env",".tox",".mypy_cache",".pytest_cache","*.pyc","*.pyo","*.egg-info",".DS_Store","Thumbs.db",)

@dataclass
class Skip:
    path: Path
    reason: str

def matches_pattern(name: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(name.casefold(), pattern.casefold())

def should_ignore(path: Path, root: Path, patterns: Iterable[str]) -> bool:
    return any(matches_pattern(part, pattern) for part in path.relative_to(root).parts for pattern in patterns)

def decode_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None

def tree_text(relative_paths: list[Path], root_name: str) -> str:
    tree: dict[str, dict | None] = {}
    for rel in relative_paths:
        current = tree
        for part in rel.parts[:-1]:
            child = current.setdefault(part, {})
            current = child
        current[rel.name] = None
    lines = [root_name]
    def walk(node, prefix=""):
        entries = sorted(node.items(), key=lambda item: (item[1] is None, item[0].casefold()))
        for index, (name, child) in enumerate(entries):
            last = index == len(entries) - 1
            lines.append(prefix + ("`-- " if last else "|-- ") + name)
            if isinstance(child, dict):
                walk(child, prefix + ("    " if last else "|   "))
    walk(tree)
    return "\n".join(lines) + "\n"

def compact(source: Path, output: Path, patterns: tuple[str, ...]) -> tuple[int, list[Skip]]:
    source = source.resolve()
    output = output.resolve()
    if not source.is_dir():
        raise ValueError(f"Pasta não existe: {source}")
    if output == source or source in output.parents:
        raise ValueError("Saída deve ficar fora da origem.")
    included = []
    skipped = []
    for path in sorted(source.rglob("*"), key=lambda p: str(p.relative_to(source)).casefold()):
        if not path.is_file():
            continue
        if should_ignore(path, source, patterns):
            skipped.append(Skip(path, "padrão global"))
            continue
        try:
            content = decode_text(path)
        except OSError as exc:
            skipped.append(Skip(path, f"erro: {exc}"))
            continue
        if content is None:
            skipped.append(Skip(path, "binário ou não UTF-8"))
            continue
        included.append((path, content))
    output.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S %z")
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("=" * 60 + "\n")
        handle.write("  COPIADOR DE CÓDIGO v2.1 — Python Edition\n")
        handle.write("=" * 60 + "\n")
        handle.write(f"  Data/Hora     : {now}\n")
        handle.write(f"  Origem        : {source}\n")
        handle.write(f"  Total arquivos: {len(included)}\n")
        if patterns:
            handle.write("  Filtros       : padrões globais\n")
        handle.write("=" * 60 + "\n\n")
        relative_paths = []
        for path, content in included:
            rel = path.relative_to(source)
            rel_with_root = Path(source.name) / rel
            relative_paths.append(rel)
            handle.write(SEP + "\n")
            handle.write(f"Conteúdo de {path.name} (caminho: {rel_with_root.as_posix()}) [enc: utf-8]:\n")
            handle.write(SEP + "\n")
            handle.write(content)
            handle.write("\n\n")
        handle.write("\n" + SEP + "\nEstrutura de pastas:\n" + SEP + "\n")
        handle.write(tree_text(relative_paths, source.name))
    return len(included), skipped

def main() -> int:
    parser = argparse.ArgumentParser(description="Gera .txt restaurável")
    parser.add_argument("pasta", type=Path, help="Pasta do projeto")
    parser.add_argument("-o", "--saida", type=Path, default=None, help="Caminho .txt saída")
    parser.add_argument("--sem-filtros", action="store_true", help="Inclui ignorados; binários excluídos")
    parser.add_argument("--mostrar-ignorados", action="store_true", help="Mostra ignorados")
    args = parser.parse_args()
    source = args.pasta.expanduser()
    default_output = source.resolve().parent / f"{source.name}_codigo_completo.txt"
    output = (args.saida or default_output).expanduser()
    patterns = () if args.sem_filtros else DEFAULT_IGNORE_PATTERNS
    try:
        count, skipped = compact(source, output, patterns)
    except (ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Arquivo gerado: {output.resolve()}")
    print(f"Arquivos compactados: {count}")
    print(f"Arquivos ignorados: {len(skipped)}")
    if args.mostrar_ignorados:
        for item in skipped:
            print(f"  [IGNORADO — {item.reason}] {item.path.relative_to(source.resolve())}")
    elif skipped:
        print("Use --mostrar-ignorados para ver a lista.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## ESTRATÉGIA ZIP - Instruções para IAs (LEIA ISSO COM ATENÇÃO)

Quando você receber um `codigo_completo.txt` gigante:

### Passo 1: NÃO extraia para pasta se tiver >1000 arquivos
Ambientes de IA limitam arquivos soltos. Erro típico:
```
Too many output files: 7536, limit is: 2048
```

### Passo 2: Use restore_to_zip.py
```bash
python3 restore_to_zip.py codigo_completo.txt projeto_restaurado.zip
```
Isso cria 1 arquivo no disco com 10k arquivos dentro.

### Passo 3: Leia DIRETO do ZIP sem extrair (INTELIGÊNCIA ARTIFICIAL FAZ ASSIM)

```python
import zipfile
zip_path = '/mnt/data/projeto_restaurado.zip'

# Listar tudo sem extrair
with zipfile.ZipFile(zip_path) as z:
    print(f"Total: {len(z.namelist())} arquivos")
    # filtrar specs
    specs = [n for n in z.namelist() if n.endswith('.md') and '01_original' in n]

# Ler um arquivo específico sem extrair
def read_from_zip(internal_path):
    with zipfile.ZipFile(zip_path) as z:
        candidates = [n for n in z.namelist() if n.endswith(internal_path)]
        return z.read(candidates[0]).decode('utf-8')

conteudo = read_from_zip('SESSIONS.md')
```

### Passo 4: Para auditorias, use sub-agents lendo do mesmo ZIP
Cada sub-agent abre o mesmo ZIP e lê seu spec. Não precisam extrair.

### Passo 5: Se precisar extrair, extraia SÓ uma subpasta
```python
with zipfile.ZipFile(zip_path) as z:
    for name in z.namelist():
        if '02_replica/src/' in name: # só 56 arquivos
            z.extract(name, '/mnt/data/parcial')
```

### Por que isso é genial?
- Evita limite de arquivos
- Streaming não carrega TXT gigante na RAM (evita timeout 120s)
- Trata cabeçalhos fantasmas duplicados automaticamente
- Permite auditoria completa sem extrair nada

---

## Compactar

```bash
python3 compactar_projeto.py ./minha-pasta -o ./codigo_completo.txt
```

## Restaurar clássico (projetos pequenos <1000 arquivos)

```bash
python3 restore_codefilecopier.py codigo_completo.txt projeto_restaurado
```

## Restaurar inteligente (projetos gigantes >1000 arquivos) - USE ESTE

```bash
python3 restore_to_zip.py codigo_completo.txt projeto_restaurado.zip
python3 -c "import zipfile; print(len(zipfile.ZipFile('projeto_restaurado.zip').namelist()))"
```
```

---

> **Instrução final para a IA que receber este comando:** Salve os 3 scripts, execute `restore_to_zip.py` primeiro, confirme que o ZIP foi criado com `zipfile.ZipFile().namelist()`, e só então comece qualquer análise. NUNCA tente extrair tudo solto se o ZIP tiver >2000 arquivos. Leia sempre direto do ZIP usando a função `read_from_zip()` demonstrada acima.

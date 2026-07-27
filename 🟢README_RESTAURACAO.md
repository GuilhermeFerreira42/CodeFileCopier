```markdown
# Restauração de Projeto

Você recebeu um arquivo `.txt` com um projeto compactado pelo Copiador de Código v2.0.

## O que fazer

1. Salve os dois scripts abaixo no workspace:

   - `restore_codefilecopier.py`
   - `compactar_projeto.py`

2. Execute a restauração:

```bash
python3 restore_codefilecopier.py NOME_DO_ARQUIVO.txt projeto_restaurado
```

3. Se houver `package.json` na pasta restaurada, pergunte se devo rodar `npm install`.

## Scripts

### restore_codefilecopier.py

```python
#!/usr/bin/env python3
"""Restaura um projeto a partir de um .txt gerado pelo Copiador de Código v2.0."""

import re
import sys
from pathlib import Path

SEP = "=" * 42
HEADER_RE = re.compile(
    r"^Conteúdo de (.+?) \(caminho: (.+?)\) \[enc: utf-8\]:$"
)

def restore(source: str, dest: str) -> int:
    src = Path(source)
    if not src.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {source}")

    text = src.read_text(encoding="utf-8")
    count = 0
    current_path = None
    current_lines: list[str] = []
    in_file = False

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == SEP:
            if in_file and current_path is not None:
                out = Path(dest) / current_path
                out.parent.mkdir(parents=True, exist_ok=True)
                content = "".join(current_lines)
                if content.endswith("\n\n"):
                    content = content[:-1]
                out.write_text(content, encoding="utf-8", newline="\n")
                count += 1
            in_file = not in_file
            if in_file:
                current_lines = []
                current_path = None
            continue

        if in_file and current_path is None:
            m = HEADER_RE.match(stripped)
            if m:
                current_path = m.group(2)
            continue

        if in_file and current_path is not None:
            current_lines.append(line)

    return count

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Uso: python3 {sys.argv[0]} ARQUIVO.txt PASTA_DESTINO")
        sys.exit(1)
    try:
        n = restore(sys.argv[1], sys.argv[2])
        print(f"Arquivos restaurados: {n}")
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
```

### compactar_projeto.py

```python
#!/usr/bin/env python3
"""Compacta uma pasta de código em um .txt compatível com restore_codefilecopier.py."""

import fnmatch
import sys
from datetime import datetime
from pathlib import Path

SEP = "=" * 42
IGNORE = (
    ".git", "node_modules", "dist", "build", "*.log", "__pycache__",
    "venv", ".venv", "env", ".env", ".tox", ".mypy_cache", ".pytest_cache",
    "*.pyc", "*.pyo", "*.egg-info", ".DS_Store", "Thumbs.db",
)

def should_ignore(path: Path, root: Path) -> bool:
    return any(
        fnmatch.fnmatchcase(p.casefold(), pat.casefold())
        for p in path.relative_to(root).parts for pat in IGNORE
    )

def decode(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None

def tree(rels: list[Path], name: str) -> str:
    t: dict[str, dict | None] = {}
    for r in rels:
        c = t
        for p in r.parts[:-1]:
            c = c.setdefault(p, {})
        c[r.name] = None
    lines = [name]
    def walk(n: dict, pre: str = ""):
        entries = sorted(n.items(), key=lambda x: (x[1] is not None, x[0].casefold()))
        for i, (k, v) in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(pre + ("`-- " if last else "|-- ") + k)
            if isinstance(v, dict):
                walk(v, pre + ("    " if last else "|   "))
    walk(t)
    return "\n".join(lines) + "\n"

def compact(source: str, output: str) -> tuple[int, list[str]]:
    src = Path(source).resolve()
    out = Path(output).resolve()

    included: list[tuple[Path, str]] = []
    skipped: list[str] = []

    for f in sorted(src.rglob("*"), key=lambda p: str(p.relative_to(src)).casefold()):
        if not f.is_file():
            continue
        if should_ignore(f, src):
            skipped.append(str(f.relative_to(src)))
            continue
        content = decode(f)
        if content is None:
            skipped.append(f"{f.relative_to(src)} (binário)")
            continue
        included.append((f, content))

    out.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S %z")

    with out.open("w", encoding="utf-8", newline="\n") as h:
        h.write("=" * 60 + "\n")
        h.write("  COPIADOR DE CÓDIGO v2.1 — Python Edition\n")
        h.write("=" * 60 + "\n")
        h.write(f"  Data/Hora     : {now}\n")
        h.write(f"  Origem        : {src}\n")
        h.write(f"  Total arquivos: {len(included)}\n")
        h.write("=" * 60 + "\n\n")

        rels: list[Path] = []
        for f, content in included:
            rel = f.relative_to(src)
            rels.append(rel)
            rw = Path(src.name) / rel
            h.write(SEP + "\n")
            h.write(f"Conteúdo de {f.name} (caminho: {rw.as_posix()}) [enc: utf-8]:\n")
            h.write(SEP + "\n")
            h.write(content)
            h.write("\n\n")

        h.write("\n" + SEP + "\nEstrutura de pastas:\n" + SEP + "\n")
        h.write(tree(rels, src.name))

    return len(included), skipped

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 compactar_projeto.py PASTA [-o SAIDA.txt]")
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else f"{Path(src).name}_codigo_completo.txt"
    n, sk = compact(src, out)
    print(f"Arquivo gerado: {Path(out).resolve()}")
    print(f"Arquivos compactados: {n}")
    print(f"Ignorados: {len(sk)}")
```

## Compactar

```bash
python3 compactar_projeto.py ./minha-pasta -o ./codigo_completo.txt
```
```
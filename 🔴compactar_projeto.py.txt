#!/usr/bin/env python3
"""Compacta uma pasta de código em um .txt compatível com restore_codefilecopier.py.

Exemplos:
  python3 compactar_projeto.py ./minha-pasta
  python3 compactar_projeto.py ./minha-pasta -o ./codigo_completo.txt
  python3 compactar_projeto.py ./minha-pasta --sem-filtros

O arquivo gerado contém apenas arquivos de texto UTF-8. Arquivos binários,
arquivos em codificação não UTF-8 e itens ignorados são listados no resumo.
Nenhum conteúdo é enviado à rede.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

SEP = "=" * 42

# Mesmos padrões globais do Copiador de Código v2.1.
DEFAULT_IGNORE_PATTERNS = (
    ".git",
    "node_modules",
    "dist",
    "build",
    "*.log",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    ".DS_Store",
    "Thumbs.db",
)


@dataclass
class Skip:
    path: Path
    reason: str


def matches_pattern(name: str, pattern: str) -> bool:
    """Compara o nome de um arquivo/pasta a um padrão simples com * e ?."""
    return fnmatch.fnmatchcase(name.casefold(), pattern.casefold())


def should_ignore(path: Path, root: Path, patterns: Iterable[str]) -> bool:
    """Retorna True se qualquer componente relativo corresponder a um padrão."""
    return any(
        matches_pattern(part, pattern)
        for part in path.relative_to(root).parts
        for pattern in patterns
    )


def decode_text(path: Path) -> str | None:
    """Lê somente texto UTF-8. NUL indica arquivo binário com segurança."""
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        # utf-8-sig também remove um BOM, quando houver.
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def tree_text(relative_paths: list[Path], root_name: str) -> str:
    """Monta a árvore apenas informativa exibida no fim do arquivo."""
    tree: dict[str, dict | None] = {}
    for rel in relative_paths:
        current = tree
        for part in rel.parts[:-1]:
            child = current.setdefault(part, {})
            assert isinstance(child, dict)
            current = child
        current[rel.name] = None

    lines = [root_name]

    def walk(node: dict[str, dict | None], prefix: str = "") -> None:
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
        raise ValueError(f"A pasta de origem não existe ou não é uma pasta: {source}")
    if output == source or source in output.parents:
        raise ValueError("O arquivo de saída deve ficar fora da pasta de origem.")

    included: list[tuple[Path, str]] = []
    skipped: list[Skip] = []

    # rglob é ordenado para que a saída seja repetível e mais fácil de comparar.
    for path in sorted(source.rglob("*"), key=lambda p: str(p.relative_to(source)).casefold()):
        if not path.is_file():
            continue
        if should_ignore(path, source, patterns):
            skipped.append(Skip(path, "padrão global"))
            continue
        try:
            content = decode_text(path)
        except OSError as exc:
            skipped.append(Skip(path, f"erro de leitura: {exc}"))
            continue
        if content is None:
            skipped.append(Skip(path, "binário ou não UTF-8"))
            continue
        included.append((path, content))

    output.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S %z")

    # newline='\n' garante o formato esperado pelo restaurador em qualquer SO.
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

        relative_paths: list[Path] = []
        for path, content in included:
            rel = path.relative_to(source)
            # O nome da pasta raiz é incluído, assim a restauração recria o projeto
            # dentro da pasta destino, como ocorre no seletor de diretório do HTML.
            rel_with_root = Path(source.name) / rel
            relative_paths.append(rel)
            handle.write(SEP + "\n")
            handle.write(
                f"Conteúdo de {path.name} (caminho: {rel_with_root.as_posix()}) [enc: utf-8]:\n"
            )
            handle.write(SEP + "\n")
            handle.write(content)
            handle.write("\n\n")

        handle.write("\n" + SEP + "\nEstrutura de pastas:\n" + SEP + "\n")
        handle.write(tree_text(relative_paths, source.name))

    return len(included), skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera um .txt restaurável a partir de uma pasta de código."
    )
    parser.add_argument("pasta", type=Path, help="Pasta do projeto a compactar")
    parser.add_argument(
        "-o", "--saida", type=Path, default=None,
        help="Caminho do .txt de saída (padrão: ao lado da pasta)",
    )
    parser.add_argument(
        "--sem-filtros", action="store_true",
        help="Inclui itens normalmente ignorados; binários continuam excluídos.",
    )
    parser.add_argument(
        "--mostrar-ignorados", action="store_true",
        help="Mostra todos os arquivos ignorados (o padrão mostra somente o total).",
    )
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

import re
import sys
from pathlib import Path

SEP = '=' * 42

# Casa cada bloco de arquivo procurando diretamente pelo próximo cabeçalho real
# (ou pelo marcador de fim "Estrutura de pastas:") em vez de usar lookahead
# não-guloso sobre [\s\S], que falha (corta no 1º \n) quando o conteúdo do
# arquivo tem múltiplas linhas.
HEADER_RE = re.compile(
    re.escape(SEP) + r'\n'
    r'Conteúdo de (?P<name>.+?) \(caminho: (?P<rel>.+?)\) \[enc: utf-8\]:\n'
    + re.escape(SEP) + r'\n'
)

FOOTER_MARKER = '\n' + SEP + '\nEstrutura de pastas:\n'


def restore_codefilecopier(txt_path, out_dir, verbose=True):
    raw = Path(txt_path).read_bytes()
    text = raw.decode('utf-8').replace('\r\n', '\n')

    # Delimita o fim da seção de conteúdo de arquivos (antes da árvore final),
    # se o marcador existir. Se não existir, processa o texto inteiro.
    footer_idx = text.find(FOOTER_MARKER)
    body = text[:footer_idx] if footer_idx != -1 else text

    matches = list(HEADER_RE.finditer(body))
    if not matches:
        raise ValueError(
            "Nenhum cabeçalho de arquivo encontrado. O .txt não está no "
            "formato esperado do Copiador de Código v2.0."
        )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    n = 0
    warnings = []
    seen_paths = set()

    for i, m in enumerate(matches):
        rel = m.group('rel')
        name = m.group('name')

        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[content_start:content_end]

        # genOutput grava: sep + header + sep + content + '\n\n'
        # então cada bloco de conteúdo termina com exatamente 2 '\n' a mais
        # do que o conteúdo original (1 do próprio write, 1 separador de bloco),
        # exceto o último bloco do arquivo, que pode não ter o segundo '\n'
        # caso o footer não exista. Removemos no máximo 2 '\n' finais.
        if content.endswith('\n\n'):
            content = content[:-2]
        elif content.endswith('\n'):
            content = content[:-1]

        # Sanidade: caminho relativo não pode escapar da pasta de destino
        target = (out / rel).resolve()
        if not str(target).startswith(str(out.resolve())):
            warnings.append(f"[IGNORADO - caminho suspeito] {rel}")
            continue

        if rel in seen_paths:
            warnings.append(f"[AVISO - caminho duplicado, sobrescrito] {rel}")
        seen_paths.add(rel)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8', newline='\n')
        n += 1

    if verbose:
        print(f"Arquivos restaurados: {n}")
        if footer_idx == -1:
            warnings.append("[AVISO] Marcador 'Estrutura de pastas:' não encontrado no .txt.")
        for w in warnings:
            print(w)

    return n, warnings


if __name__ == "__main__":
    txt_path = sys.argv[1] if len(sys.argv) > 1 else 'codigo_completo.txt'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'projeto_restaurado'
    restore_codefilecopier(txt_path, out_dir)

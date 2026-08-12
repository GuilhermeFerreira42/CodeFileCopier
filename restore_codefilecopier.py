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

# Salvaguarda B: fragmento de cabeçalho malformado/incompleto que pode sobrar
# grudado no FINAL do conteúdo extraído de um bloco (ex: cabeçalho "fantasma"
# duplicado que o gerador produziu sem o separador de fechamento, ou com uma
# linha em branco no meio que impede o HEADER_RE de reconhecê-lo como
# cabeçalho válido). Casa com ou sem o segundo separador, ancorado no fim
# da string.
GHOST_HEADER_RE = re.compile(
    r'\n' + re.escape(SEP) + r'\n'
    r'Conteúdo de .+? \(caminho: .+?\) \[enc: utf-8\]:\n'
    r'(?:' + re.escape(SEP) + r'\n?)?\n?$'
)


def _consolidate_duplicate_headers(matches, body):
    """Salvaguarda A: quando dois (ou mais) cabeçalhos COMPLETOS consecutivos
    apontam para o MESMO arquivo (mesmo caminho), com apenas espaço em
    branco entre eles, os anteriores são cabeçalhos "fantasma" e devem ser
    descartados — só o último da sequência é válido, pois é o que fica
    imediatamente antes do conteúdo real.

    Importante: só descarta quando o trecho ENTRE os dois cabeçalhos é
    vazio/whitespace. Isso evita apagar arquivos genuinamente vazios que só
    coincidentemente compartilham o caminho com o próximo cabeçalho (o que,
    na prática, nunca deveria acontecer, mas mantemos a checagem por
    segurança).
    """
    filtered = []
    for i, m in enumerate(matches):
        if i + 1 < len(matches) and matches[i + 1].group('rel') == m.group('rel'):
            between = body[m.end():matches[i + 1].start()]
            if between.strip() == '':
                continue  # cabeçalho fantasma: descarta, o próximo prevalece
        filtered.append(m)
    return filtered


def restore_codefilecopier(txt_path, out_dir, verbose=True):
    raw = Path(txt_path).read_bytes()
    text = raw.decode('utf-8').replace('\r\n', '\n')

    # Salvaguarda C: delimita o fim da seção de conteúdo de arquivos (antes
    # da árvore final), se o marcador existir. Se não existir, processa o
    # texto inteiro.
    footer_idx = text.find(FOOTER_MARKER)
    body = text[:footer_idx] if footer_idx != -1 else text

    raw_matches = list(HEADER_RE.finditer(body))
    if not raw_matches:
        raise ValueError(
            "Nenhum cabeçalho de arquivo encontrado. O .txt não está no "
            "formato esperado do Copiador de Código v2.0."
        )

    # Salvaguarda A: consolida cabeçalhos duplicados consecutivos do mesmo
    # arquivo antes de extrair qualquer conteúdo.
    matches = _consolidate_duplicate_headers(raw_matches, body)

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

        # Salvaguarda B: verifica ANTES de qualquer trim se um fragmento de
        # cabeçalho malformado sobrou grudado no final do conteúdo bruto
        # (ver GHOST_HEADER_RE acima). O '\n' que abre o padrão fantasma é o
        # mesmo separador de bloco que o gerador escreveria de qualquer
        # forma, então cortar ali já restaura o conteúdo original completo
        # (incluindo eventual newline final que o próprio arquivo tinha) —
        # por isso, quando o fantasma é encontrado, NÃO aplicamos o trim
        # normal de '\n\n' por cima.
        ghost_match = GHOST_HEADER_RE.search(content)
        if ghost_match:
            content = content[:ghost_match.start()]
            warnings.append(f"[AVISO - fragmento de cabeçalho fantasma removido do final] {rel}")
        else:
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

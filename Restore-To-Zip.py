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
                            if content.endswith('\n\n'):
                                content = content[:-2]
                            elif content.endswith('\n'):
                                content = content[:-1]
                            if '..' not in Path(current_rel).parts:
                                if current_rel == last_rel and content.strip() == '':
                                    ghost_skipped += 1
                                else:
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
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        print(f"Total no ZIP: {len(names)}")
        for n in sorted(names)[:max_show]:
            print(f"  {n}")
        if len(names) > max_show:
            print(f"  ... e mais {len(names)-max_show}")

def read_from_zip(zip_path, internal_path):
    with zipfile.ZipFile(zip_path) as z:
        candidates = [n for n in z.namelist() if n.endswith(internal_path)]
        if not candidates:
            raise FileNotFoundError(f"{internal_path} não encontrado")
        data = z.read(candidates[0])
        return data.decode('utf-8', errors='ignore')

if __name__ == "__main__":
    import sys
    txt = sys.argv[1] if len(sys.argv) > 1 else 'codigo_completo.txt'
    out = sys.argv[2] if len(sys.argv) > 2 else 'projeto_restaurado.zip'
    restore_to_zip(txt, out)
    list_zip_tree(out)

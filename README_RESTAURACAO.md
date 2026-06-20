# Instruções para o Agente — Restauração de Projeto

## O que é isto

Você recebeu dois arquivos:

1. **Um arquivo `.txt` grande** — é um projeto de código inteiro, compactado em
   texto único pelo programa "Copiador de Código v2.0". Ele contém o conteúdo
   de cada arquivo do projeto, separado por cabeçalhos no formato:

   ```
   ==========================================
   Conteúdo de NOME_DO_ARQUIVO (caminho: CAMINHO/RELATIVO) [enc: utf-8]:
   ==========================================
   <conteúdo do arquivo aqui>
   ```

   No final do arquivo há uma seção "Estrutura de pastas:" com a árvore do
   projeto (apenas informativa, não é usada pela restauração).

2. **Um script Python** (`restore_codefilecopier.py`) — já pronto, testado e
   validado. Ele faz a restauração: lê o `.txt` e recria a estrutura real de
   pastas e arquivos em disco.

## O que fazer (passo a passo)

1. **Não leia o conteúdo do `.txt` diretamente.** Ele é grande e não é
   necessário — o script cuida de tudo.

2. Execute o script no terminal, passando o nome do `.txt` (pode ter qualquer
   nome) e uma pasta de destino:

   ```bash
   python3 restore_codefilecopier.py NOME_DO_ARQUIVO.txt projeto_restaurado
   ```

   - Substitua `NOME_DO_ARQUIVO.txt` pelo nome real do arquivo que você recebeu.
   - `projeto_restaurado` é o nome da pasta de saída — pode trocar se preferir.

3. O script vai imprimir quantos arquivos foram restaurados. Se aparecer
   algum aviso (`[AVISO ...]` ou `[IGNORADO ...]`), reporte ao usuário antes
   de continuar.

4. Depois de rodar, **não presuma que terminou**: avise o usuário que a
   restauração foi concluída e pergunte se ele quer conferir a estrutura
   antes de prosseguir.

5. Este projeto restaurado **não inclui `node_modules`** (foi excluída
   propositalmente do `.txt` para evitar binários incompatíveis). Se o
   projeto for Node.js (tiver `package.json`), pergunte ao usuário se deseja
   rodar `npm install` na pasta restaurada antes de seguir com o
   desenvolvimento.

## Depois da restauração

O conteúdo da pasta `projeto_restaurado` (ou o nome que você escolheu) é um
sistema/projeto real que o usuário estava desenvolvendo antes. A partir daqui,
trate-o como um projeto de trabalho normal: o usuário vai dar contexto sobre
o que o sistema faz e quais são os próximos passos de desenvolvimento.

## Importante

- O script já foi testado contra arquivos com múltiplas linhas, acentuação,
  caminhos com espaço, conteúdo contendo `====` (que poderia ser confundido
  com separador), e tentativas de caminho inválido (`../`). Não precisa
  reescrever ou "corrigir" o script — apenas execute-o.
- Se o script falhar com erro de "Nenhum cabeçalho de arquivo encontrado",
  avise o usuário: provavelmente o `.txt` não é do formato esperado, ou está
  corrompido/incompleto.

#!/usr/bin/env python3
"""
Corrige o erro de compilacao:

    javax.xml.stream.XMLStreamException: ParseError at [row,col]:[5,58]
    Message: The string "--" is not permitted within comments.

Causa: o arquivo app/src/main/res/layout/search_bar_holo.xml tem um
comentario XML com "--" solto no meio do texto. A especificacao XML
proibe "--" dentro de comentarios (<!-- ... -->), entao o aapt2 recusa
compilar o recurso.

O que este script faz:
1. Varre todos os arquivos .xml dentro de app/src/main/res/
2. Para cada comentario <!-- ... -->, troca qualquer "--" que apareca
   NO MEIO do comentario por um travessao simples "-" (preservando o
   "-->" de fechamento, que e obrigatorio e valido).
3. Salva os arquivos corrigidos e mostra um resumo do que mudou.

Uso (rodar dentro da pasta do projeto, ex: ~/Galeria3D):
    python3 corrigir_bug_xml_comentario.py
"""

import os
import re
import sys

# Pasta res do projeto Android (padrao: app/src/main/res a partir de onde
# o script for executado). Pode passar outro caminho como argumento.
RES_DIR = sys.argv[1] if len(sys.argv) > 1 else "app/src/main/res"

# Encontra comentarios XML completos: <!-- ... -->
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)


def fix_comment_body(body: str) -> str:
    """Remove qualquer '--' que sobrar dentro do corpo do comentario,
    substituindo por '-' ate nao haver mais ocorrencias."""
    while "--" in body:
        body = body.replace("--", "-")
    return body


def process_file(path: str) -> int:
    """Corrige um arquivo XML. Retorna quantos comentarios foram alterados."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    changed_count = 0

    def replacer(match: "re.Match[str]") -> str:
        nonlocal changed_count
        body = match.group(1)
        fixed_body = fix_comment_body(body)
        if fixed_body != body:
            changed_count += 1
        return "<!--" + fixed_body + "-->"

    new_content = COMMENT_RE.sub(replacer, content)

    if changed_count > 0:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return changed_count


def main() -> None:
    if not os.path.isdir(RES_DIR):
        print(f"ERRO: pasta '{RES_DIR}' nao encontrada.")
        print("Rode este script de dentro da pasta do projeto (ex: ~/Galeria3D),")
        print("ou passe o caminho da pasta res como argumento:")
        print("    python3 corrigir_bug_xml_comentario.py caminho/para/res")
        sys.exit(1)

    total_files_changed = 0
    total_comments_changed = 0

    for root, _dirs, files in os.walk(RES_DIR):
        for name in files:
            if not name.endswith(".xml"):
                continue
            path = os.path.join(root, name)
            try:
                n = process_file(path)
            except UnicodeDecodeError:
                # Arquivo binario com extensao .xml (raro) - ignora
                continue
            if n > 0:
                total_files_changed += 1
                total_comments_changed += n
                print(f"Corrigido: {path}  ({n} comentario(s))")

    print()
    if total_files_changed == 0:
        print("Nenhum problema encontrado (nenhum '--' dentro de comentarios XML).")
    else:
        print(f"Concluido: {total_comments_changed} comentario(s) corrigido(s) em "
              f"{total_files_changed} arquivo(s).")
        print("Agora rode de novo: ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

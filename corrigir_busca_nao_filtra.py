#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige o bug: a barra de busca (icone holo colapsavel) filtra a lista
por baixo dos panos, mas a tela nunca atualiza (nao esconde os itens que
nao batem com a busca).

CAUSA REAL: setSearchFilter() atualiza a lista filtrada em memoria
(mAlbums em ClusterAlbumSet.java / mPaths em ClusterAlbum.java), mas
nunca avisa o sistema de "versao de dados" que algo mudou. A grade na
tela e desenhada por uma thread de carregamento em segundo plano
(AlbumSetDataLoader / AlbumDataLoader) que so re-consulta a lista quando
o metodo reload() retorna um numero de versao DIFERENTE do que ja tem em
cache. Só que reload() so incrementa essa versao quando o MediaStore (o
banco de musicas do proprio Android) muda - nunca quando e so um filtro
de busca sendo aplicado. Resultado: a busca roda, os dados sao filtrados
certinho internamente, mas a tela nunca e avisada pra redesenhar.

CORRECAO: em setSearchFilter(), depois de aplicar o filtro, forcamos
manualmente um novo numero de versao (mDataVersion = nextVersionNumber()).
Assim, na proxima vez que a thread de carregamento chamar reload(), ela
recebe uma versao diferente da que tinha em cache e redesenha a grade
com a lista ja filtrada.

Arquivos corrigidos:
- app/src/main/java/com/android/gallery3d/data/ClusterAlbumSet.java
  (grade de cards: Artistas/Albuns/Playlists/...)
- app/src/main/java/com/android/gallery3d/data/ClusterAlbum.java
  (lista de faixas dentro de um card aberto)

Uso (rodar dentro da pasta do projeto, ex: ~/Galeria3D):
    python3 corrigir_busca_nao_filtra.py

Seguro rodar mais de uma vez (detecta o que ja foi aplicado e pula).
"""

import os
import sys

PROJECT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

FILES = {
    "cluster_album_set": "app/src/main/java/com/android/gallery3d/data/ClusterAlbumSet.java",
    "cluster_album": "app/src/main/java/com/android/gallery3d/data/ClusterAlbum.java",
}


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def apply_edit(path, old, new, label):
    if not os.path.isfile(path):
        print(f"  [ERRO] arquivo nao encontrado: {path}")
        return "missing"

    content = read(path)

    if new in content:
        print(f"  [ja aplicado] {label}")
        return "skipped"

    if old not in content:
        print(f"  [ERRO] trecho esperado nao encontrado em {path} para: {label}")
        print("         (o arquivo pode ja ter sido alterado por outra sessao;")
        print("          confira manualmente se necessario)")
        return "missing"

    content = content.replace(old, new, 1)
    write(path, content)
    print(f"  [OK] {label}")
    return "applied"


def main():
    os.chdir(PROJECT_DIR)

    for key, rel in FILES.items():
        if not os.path.isfile(rel):
            print(f"ERRO: nao encontrei '{rel}' a partir de '{os.getcwd()}'.")
            print("Rode este script de dentro da pasta do projeto (ex: ~/Galeria3D),")
            print("ou passe o caminho do projeto como argumento:")
            print("    python3 corrigir_busca_nao_filtra.py caminho/para/Galeria3D")
            sys.exit(1)

    results = []

    # ---------------------------------------------------------------
    # ClusterAlbumSet.java - grade de cards (Artistas/Albuns/...)
    # ---------------------------------------------------------------
    old = '''    public void setSearchFilter(String query) {
        mSearchQuery = (query == null) ? "" : query.trim();
        applySearchFilter();
        notifyContentChanged();
    }'''
    new = '''    public void setSearchFilter(String query) {
        mSearchQuery = (query == null) ? "" : query.trim();
        applySearchFilter();
        // Passo 6 (correcao): applySearchFilter() so troca a lista mAlbums
        // em memoria - sem isso, reload() (chamado pela thread de
        // carregamento da grade) so incrementa mDataVersion quando o
        // MediaStore muda, entao a busca nunca aparecia na tela mesmo
        // filtrando certo por baixo dos panos. Forcamos aqui uma nova
        // versao para o loader perceber a mudanca e redesenhar a grade.
        mDataVersion = nextVersionNumber();
        notifyContentChanged();
    }'''
    results.append(apply_edit(FILES["cluster_album_set"], old, new,
                               "ClusterAlbumSet.java: bump de versao no filtro de busca"))

    # ---------------------------------------------------------------
    # ClusterAlbum.java - lista de faixas dentro de um card aberto
    # ---------------------------------------------------------------
    old = '''    public void setSearchFilter(String query) {
        mSearchQuery = (query == null) ? "" : query.trim();
        applySearchFilter();
        notifyContentChanged();
    }'''
    new = '''    public void setSearchFilter(String query) {
        mSearchQuery = (query == null) ? "" : query.trim();
        applySearchFilter();
        // Passo 6 (correcao): mesmo motivo do ClusterAlbumSet - sem isso,
        // reload() nunca detecta a mudanca (o MediaStore em si nao mudou)
        // e a lista de faixas na tela nunca e atualizada apos filtrar.
        mDataVersion = nextVersionNumber();
        notifyContentChanged();
    }'''
    results.append(apply_edit(FILES["cluster_album"], old, new,
                               "ClusterAlbum.java: bump de versao no filtro de busca"))

    print()
    applied = results.count("applied")
    skipped = results.count("skipped")
    missing = results.count("missing")

    if missing > 0:
        print(f"ATENCAO: {missing} trecho(s) nao encontrado(s) - confira as mensagens de ERRO acima.")
    elif applied == 0:
        print("Nada a fazer - a correcao ja estava aplicada.")
    else:
        print(f"Concluido: {applied} correcao(oes) aplicada(s), {skipped} ja estavam prontas.")
        print("Agora rode: ./gradlew assembleDebug")
        print()
        print("IMPORTANTE: depois de instalar o novo APK, se o dispositivo ainda")
        print("mostrar o comportamento antigo, desinstale o app antes de reinstalar")
        print("(adb uninstall com.xaulinxs.galeria3d) para garantir que nao ha")
        print("versao antiga em cache.")


if __name__ == "__main__":
    main()

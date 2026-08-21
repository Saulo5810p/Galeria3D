#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige o problema: a barra de busca (antes um campo de texto ocupando
toda a largura, no topo) ficava atras/ofuscada pelo spinner de filtro
(Musicas/Artistas/Albuns/...) da ActionBar.

O que este script faz:
1. Remove a antiga barra de busca full-width (GalleryActivity.setupSearchBar())
   que era inflada dentro do FrameLayout "header" de main.xml.
2. Adiciona um item de busca (icone de lupa, estilo holo classico -
   @android:drawable/ic_menu_search, o mesmo ja usado no projeto) nos menus
   menu/albumset.xml e menu/album.xml, posicionado ao lado do overflow
   (3 pontinhos).
3. Usa android.widget.SearchView como "collapsible action view": ao tocar
   no icone, ele se expande e ocupa o espaco da ActionBar; a propria
   ActionBar do sistema esconde automaticamente o spinner de filtro e o
   titulo enquanto a busca esta expandida (comportamento nativo do Android,
   sem precisar de animacao manual). Ao fechar (X ou voltar), tudo volta ao
   normal sozinho e o filtro de busca e limpo.
4. Liga o SearchView ao hook onSearchQueryChanged(String) que ja existia
   em AlbumSetPage.java e AlbumPage.java (mesma logica de filtragem de
   antes, so mudou o componente de UI que dispara).

Uso (rodar dentro da pasta do projeto, ex: ~/Galeria3D):
    python3 mover_busca_para_icone_holo.py

Se algum trecho ja tiver sido aplicado antes (ex: rodou o script 2x), o
script detecta e pula sem erro.
"""

import os
import sys

PROJECT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

FILES = {
    "album_menu": "app/src/main/res/menu/album.xml",
    "albumset_menu": "app/src/main/res/menu/albumset.xml",
    "gallery_activity": "app/src/main/java/com/android/gallery3d/app/GalleryActivity.java",
    "album_page": "app/src/main/java/com/android/gallery3d/app/AlbumPage.java",
    "albumset_page": "app/src/main/java/com/android/gallery3d/app/AlbumSetPage.java",
}


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def apply_edit(path, old, new, label):
    """Aplica uma substituicao unica. Retorna 'applied', 'skipped' ou 'missing'."""
    if not os.path.isfile(path):
        print(f"  [ERRO] arquivo nao encontrado: {path}")
        return "missing"

    content = read(path)

    # Quando new e vazio (edicao de remocao), "new in content" e sempre
    # verdadeiro (string vazia esta em qualquer texto) - nao serve como
    # sinal de "ja aplicado". Nesse caso, "ja aplicado" so pode ser
    # concluido pela AUSENCIA do trecho antigo.
    if new != "" and new in content:
        print(f"  [ja aplicado] {label}")
        return "skipped"

    if old not in content:
        if new == "":
            print(f"  [ja aplicado] {label}")
            return "skipped"
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
            print("    python3 mover_busca_para_icone_holo.py caminho/para/Galeria3D")
            sys.exit(1)

    results = []

    # ---------------------------------------------------------------
    # 1) menu/albumset.xml - adiciona icone de busca colapsavel
    # ---------------------------------------------------------------
    old = '''    <item android:id="@+id/action_general_help"
            android:title="@string/help"
            android:visible="false"
            android:showAsAction="never" />
</menu>'''
    new = '''    <item android:id="@+id/action_general_help"
            android:title="@string/help"
            android:visible="false"
            android:showAsAction="never" />
    <!-- Passo 6 (revisao): busca como icone colapsavel ao lado do overflow
         (3 pontinhos), no estilo holo classico de apps AOSP da epoca do
         Gallery3D (Contatos, Play Store etc usavam o mesmo padrao). Ao
         clicar, o SearchView se expande e a propria ActionBar do sistema
         esconde automaticamente o spinner de filtro (Musicas/Artistas/...)
         e o titulo; ao fechar, tudo volta ao normal sozinho, sem codigo de
         animacao manual. -->
    <item android:id="@+id/action_search"
            android:icon="@android:drawable/ic_menu_search"
            android:title="@string/menu_search"
            android:showAsAction="ifRoom|collapseActionView"
            android:actionViewClass="android.widget.SearchView" />
</menu>'''
    results.append(apply_edit(FILES["albumset_menu"], old, new,
                               "menu/albumset.xml: icone de busca colapsavel"))

    # ---------------------------------------------------------------
    # 2) menu/album.xml - adiciona icone de busca colapsavel
    # ---------------------------------------------------------------
    old = '''    <item android:id="@+id/action_group_by"
            android:title="@string/group_by"
            android:showAsAction="never"/>
</menu>'''
    new = '''    <item android:id="@+id/action_group_by"
            android:title="@string/group_by"
            android:showAsAction="never"/>
    <!-- Passo 6 (revisao): mesmo icone de busca colapsavel do albumset.xml,
         ao lado do overflow (3 pontinhos). -->
    <item android:id="@+id/action_search"
            android:icon="@android:drawable/ic_menu_search"
            android:title="@string/menu_search"
            android:showAsAction="ifRoom|collapseActionView"
            android:actionViewClass="android.widget.SearchView" />
</menu>'''
    results.append(apply_edit(FILES["album_menu"], old, new,
                               "menu/album.xml: icone de busca colapsavel"))

    # ---------------------------------------------------------------
    # 3) AlbumSetPage.java - import + wiring do SearchView
    # ---------------------------------------------------------------
    old = '''import android.widget.Button;
import android.widget.RelativeLayout;
import android.widget.Toast;'''
    new = '''import android.widget.Button;
import android.widget.RelativeLayout;
import android.widget.SearchView;
import android.widget.Toast;'''
    results.append(apply_edit(FILES["albumset_page"], old, new,
                               "AlbumSetPage.java: import SearchView"))

    old = '''            if (mShowClusterMenu != wasShowingClusterMenu) {
                if (mShowClusterMenu) {
                    mActionBar.enableClusterMenu(mSelectedAction, this);
                } else {
                    mActionBar.disableClusterMenu(true);
                }
            }
        }
        return true;
    }'''
    new = '''            if (mShowClusterMenu != wasShowingClusterMenu) {
                if (mShowClusterMenu) {
                    mActionBar.enableClusterMenu(mSelectedAction, this);
                } else {
                    mActionBar.disableClusterMenu(true);
                }
            }

            setupSearchMenuItem(menu);
        }
        return true;
    }

    // Passo 6 (revisao): liga o icone de busca colapsavel (definido em
    // menu/albumset.xml) ao filtro que ja existia via onSearchQueryChanged().
    // A propria ActionBar do sistema cuida de esconder/mostrar o spinner de
    // filtro (Musicas/Artistas/...) quando o SearchView expande/recolhe.
    private void setupSearchMenuItem(Menu menu) {
        MenuItem searchItem = menu.findItem(R.id.action_search);
        if (searchItem == null) return;
        SearchView searchView = (SearchView) searchItem.getActionView();
        if (searchView == null) return;

        searchView.setOnQueryTextListener(new SearchView.OnQueryTextListener() {
            @Override
            public boolean onQueryTextSubmit(String query) {
                return true;
            }

            @Override
            public boolean onQueryTextChange(String newText) {
                onSearchQueryChanged(newText);
                return true;
            }
        });

        searchItem.setOnActionExpandListener(new MenuItem.OnActionExpandListener() {
            @Override
            public boolean onMenuItemActionExpand(MenuItem item) {
                return true;
            }

            @Override
            public boolean onMenuItemActionCollapse(MenuItem item) {
                onSearchQueryChanged("");
                return true;
            }
        });
    }'''
    results.append(apply_edit(FILES["albumset_page"], old, new,
                               "AlbumSetPage.java: wiring do SearchView"))

    # ---------------------------------------------------------------
    # 4) AlbumPage.java - import + wiring do SearchView
    # ---------------------------------------------------------------
    old = '''import android.view.MenuItem;
import android.widget.Toast;'''
    new = '''import android.view.MenuItem;
import android.widget.SearchView;
import android.widget.Toast;'''
    results.append(apply_edit(FILES["album_page"], old, new,
                               "AlbumPage.java: import SearchView"))

    old = '''            menu.findItem(R.id.action_camera).setVisible(
                    MediaSetUtils.isCameraSource(mMediaSetPath)
                    && GalleryUtils.isCameraAvailable(mActivity));

        }
        actionBar.setSubtitle(null);
        return true;
    }'''
    new = '''            menu.findItem(R.id.action_camera).setVisible(
                    MediaSetUtils.isCameraSource(mMediaSetPath)
                    && GalleryUtils.isCameraAvailable(mActivity));

            setupSearchMenuItem(menu);
        }
        actionBar.setSubtitle(null);
        return true;
    }

    // Passo 6 (revisao): liga o icone de busca colapsavel (definido em
    // menu/album.xml) ao filtro que ja existia via onSearchQueryChanged().
    private void setupSearchMenuItem(Menu menu) {
        MenuItem searchItem = menu.findItem(R.id.action_search);
        if (searchItem == null) return;
        SearchView searchView = (SearchView) searchItem.getActionView();
        if (searchView == null) return;

        searchView.setOnQueryTextListener(new SearchView.OnQueryTextListener() {
            @Override
            public boolean onQueryTextSubmit(String query) {
                return true;
            }

            @Override
            public boolean onQueryTextChange(String newText) {
                onSearchQueryChanged(newText);
                return true;
            }
        });

        searchItem.setOnActionExpandListener(new MenuItem.OnActionExpandListener() {
            @Override
            public boolean onMenuItemActionExpand(MenuItem item) {
                return true;
            }

            @Override
            public boolean onMenuItemActionCollapse(MenuItem item) {
                onSearchQueryChanged("");
                return true;
            }
        });
    }'''
    results.append(apply_edit(FILES["album_page"], old, new,
                               "AlbumPage.java: wiring do SearchView"))

    # ---------------------------------------------------------------
    # 5) GalleryActivity.java - remove a barra antiga full-width
    # ---------------------------------------------------------------
    old = '''        setContentView(R.layout.main);
        setupSearchBar();'''
    new = '''        setContentView(R.layout.main);
        // Passo 6 (revisao): a barra de busca full-width que ficava aqui
        // (setupSearchBar(), header do main.xml) foi substituida por um
        // icone de busca colapsavel na ActionBar, ao lado do overflow (3
        // pontinhos) - ver R.id.action_search em menu/albumset.xml e
        // menu/album.xml, ligado em AlbumSetPage/AlbumPage.setupSearchMenuItem().
        // Isso evita a sobreposicao com o spinner de filtro
        // (Musicas/Artistas/...) que antes ficava atras da barra antiga.'''
    results.append(apply_edit(FILES["gallery_activity"], old, new,
                               "GalleryActivity.java: remove chamada setupSearchBar()"))

    old = '''    // Passo 6: infla a barra de busca holo dentro do FrameLayout "header"
    // ja existente em res/layout/main.xml (id gallery_root -> header),
    // que ate agora estava sempre visibility="gone" e sem nenhum uso no
    // codigo. Torna visivel e liga o TextWatcher: a cada tecla, repassa o
    // texto para o ActivityState no topo da pilha (AlbumSetPage ou
    // AlbumPage, dependendo de onde o usuario esta navegando), via o novo
    // hook ActivityState.onSearchQueryChanged(). Chamado uma unica vez em
    // onCreate(), a barra sobrevive as trocas de estado (nao e recriada a
    // cada StateManager.startState()).
    private void setupSearchBar() {
        FrameLayout header = (FrameLayout) findViewById(R.id.header);
        if (header == null) return;
        View searchBar = getLayoutInflater().inflate(
                R.layout.search_bar_holo, header, false);
        header.addView(searchBar);
        header.setVisibility(View.VISIBLE);

        EditText editText = (EditText) searchBar.findViewById(R.id.search_bar_edit_text);
        editText.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                if (getStateManager().getStateCount() > 0) {
                    getStateManager().getTopState()
                            .onSearchQueryChanged(s.toString());
                }
            }
        });
    }

'''
    new = ""
    results.append(apply_edit(FILES["gallery_activity"], old, new,
                               "GalleryActivity.java: remove metodo setupSearchBar()"))

    # imports que ficaram sem uso
    old = '''import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.InputDevice;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;'''
    new = '''import android.os.Bundle;
import android.view.InputDevice;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Toast;'''
    results.append(apply_edit(FILES["gallery_activity"], old, new,
                               "GalleryActivity.java: limpa imports nao usados"))

    print()
    applied = results.count("applied")
    skipped = results.count("skipped")
    missing = results.count("missing")

    if missing > 0:
        print(f"ATENCAO: {missing} trecho(s) nao encontrado(s) - confira as mensagens de ERRO acima.")
        print("O restante das edicoes validas foi aplicado normalmente.")
    elif applied == 0:
        print("Nada a fazer - todas as edicoes ja estavam aplicadas.")
    else:
        print(f"Concluido: {applied} edicao(oes) aplicada(s), {skipped} ja estavam prontas.")
        print("Agora rode: ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passo 8b - Correcao no popup "Escolher imagens" (as 3 opcoes que aparecem ao
adicionar o widget na tela inicial: Imagens/Albuns/Aleatorio, resquicio de
quando o app era galeria de fotos). Troca por Musicas/Playlists/Albuns (de
reproducao de musica).

Mapeamento por baixo (confirmado com o usuario):
- Albuns      -> continua igual (escolhe uma pasta especifica, como hoje)
- Musicas     -> continua igual ao antigo "aleatorio" (mistura todas as
                 faixas do app, sem escolher nada)
- Playlists   -> NOVO fluxo: abre um picker de playlist (reaproveita
                 AlbumSetPage com o filtro CLUSTER_BY_TIME, que ja e o
                 mecanismo usado pela aba "Playlists" do grid principal
                 desde o Passo 5), substitui o fluxo antigo de "escolher 1
                 foto e cortar" que nao faz mais sentido.

Rodar dentro de ~/Galeria3D (Termux), DEPOIS do fix_step8_music_widget.py:
    python3 fix_step8b_widget_type_labels.py

Idempotente, com backup .bak_step8b (nome proprio, nao reusa nenhum .bak
antigo que ja possa existir no repo).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
JAVA = os.path.join(ROOT, "app", "src", "main", "java", "com", "android", "gallery3d")
RES = os.path.join(ROOT, "app", "src", "main", "res")


def backup(path):
    bak = path + ".bak_step8b"
    if not os.path.exists(bak):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(bak, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  backup criado: {bak}")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def step_strings(path, label):
    print(f"[strings] {os.path.relpath(path, ROOT)} ({label})")
    if not os.path.exists(path):
        print("  arquivo nao existe, pulando.")
        return
    content = read(path)
    changed = False

    replacements = [
        # (string antiga completa, string nova completa)
        (
            '<string name="widget_type_album">Choose an album</string>',
            '<string name="widget_type_album">Álbuns</string>',
        ),
        (
            '<string name="widget_type_shuffle">Shuffle all images</string>',
            '<string name="widget_type_shuffle">Músicas</string>',
        ),
        (
            '<string name="widget_type_photo">Choose an image</string>',
            '<string name="widget_type_photo">Playlists</string>',
        ),
        (
            '<string name="widget_type">Choose images</string>',
            '<string name="widget_type">Escolher músicas</string>',
        ),
        # values-pt / values-pt-rPT (msgid preservado, so o texto exibido muda)
        (
            '<string name="widget_type_album" msgid="6013045393140135468">"Escolher um álbum"</string>',
            '<string name="widget_type_album" msgid="6013045393140135468">"Álbuns"</string>',
        ),
        (
            '<string name="widget_type_shuffle" msgid="8594622705019763768">"Repr. aleat. todas as imagens"</string>',
            '<string name="widget_type_shuffle" msgid="8594622705019763768">"Músicas"</string>',
        ),
        (
            '<string name="widget_type_shuffle" msgid="8594622705019763768">"Reprod. aleator. as imagens"</string>',
            '<string name="widget_type_shuffle" msgid="8594622705019763768">"Músicas"</string>',
        ),
        (
            '<string name="widget_type_photo" msgid="6267065337367795355">"Escolher uma imagem"</string>',
            '<string name="widget_type_photo" msgid="6267065337367795355">"Playlists"</string>',
        ),
        (
            '<string name="widget_type_photo" msgid="6267065337367795355">"Selecionar uma imagem"</string>',
            '<string name="widget_type_photo" msgid="6267065337367795355">"Playlists"</string>',
        ),
        (
            '<string name="widget_type" msgid="1364653978966343448">"Escolher imagens"</string>',
            '<string name="widget_type" msgid="1364653978966343448">"Escolher músicas"</string>',
        ),
    ]

    for old, new in replacements:
        if old in content and new not in content:
            backup(path)
            content = content.replace(old, new, 1)
            changed = True

    if changed:
        write(path, content)
        print("  atualizado.")
    else:
        print("  ja aplicado (ou nao encontrado), nada a fazer.")


def step_playlist_picker():
    path = os.path.join(JAVA, "app", "PlaylistPicker.java")
    print(f"[novo arquivo] {os.path.relpath(path, ROOT)}")
    if os.path.exists(path):
        print("  ja existe, nada a fazer.")
        return

    content = '''/*
 * Fix (Player3D, Passo 8b - popup de tipo de widget): novo picker de
 * playlist para o widget de home screen, irmao de AlbumPicker (que escolhe
 * uma pasta/album). Reaproveita o MESMO mecanismo usado pela aba
 * "Playlists" do grid principal (Passo 5) - AlbumSetPage com o filtro
 * CLUSTER_BY_TIME (TimeClustering foi reescrito nesse passo para agrupar
 * por playlist do MediaStore, nao mais por data).
 */

package com.android.gallery3d.app;

import android.content.Intent;
import android.os.Bundle;

import com.android.gallery3d.R;
import com.android.gallery3d.data.DataManager;
import com.android.gallery3d.util.FilterUtils;

public class PlaylistPicker extends PickerActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle(R.string.select_playlist);
        Intent intent = getIntent();
        Bundle extras = intent.getExtras();
        Bundle data = extras == null ? new Bundle() : new Bundle(extras);

        data.putBoolean(GalleryActivity.KEY_GET_ALBUM, true);
        data.putString(AlbumSetPage.KEY_MEDIA_PATH,
                getDataManager().getTopSetPath(DataManager.INCLUDE_IMAGE));
        data.putInt(AlbumSetPage.KEY_SELECTED_CLUSTER_TYPE, FilterUtils.CLUSTER_BY_TIME);
        getStateManager().startState(AlbumSetPage.class, data);
    }
}
'''
    write(path, content)
    print("  criado.")


def step_select_playlist_string(path, label):
    print(f"[strings select_playlist] {os.path.relpath(path, ROOT)} ({label})")
    if not os.path.exists(path):
        print("  arquivo nao existe, pulando.")
        return
    content = read(path)
    if 'name="select_playlist"' in content:
        print("  ja existe, nada a fazer.")
        return

    anchor = 'name="select_album"'
    idx = content.find(anchor)
    if idx == -1:
        print("  AVISO: ancora select_album nao encontrada, pulando este arquivo.")
        return
    line_start = content.rfind("\n", 0, idx) + 1
    line_end = content.find("\n", idx)
    line = content[line_start:line_end]
    # Monta a nova linha reaproveitando o mesmo padrao (com ou sem msgid)
    if "msgid=" in line:
        new_line = line.replace('name="select_album"', 'name="select_playlist"') \
                        .replace("Selecionar álbum", "Selecionar playlist") \
                        .replace("Select album", "Select playlist")
    else:
        new_line = '    <string name="select_playlist">Select playlist</string>'

    backup(path)
    content = content[:line_end] + "\n" + new_line + content[line_end:]
    write(path, content)
    print("  adicionado.")


def step_widget_configure():
    path = os.path.join(JAVA, "gadget", "WidgetConfigure.java")
    print(f"[WidgetConfigure] {os.path.relpath(path, ROOT)}")
    content = read(path)
    changed = False

    # import novo
    if "import com.android.gallery3d.app.PlaylistPicker;" not in content:
        anchor = "import com.android.gallery3d.app.DialogPicker;\n"
        assert anchor in content, "import de DialogPicker nao encontrado"
        backup(path)
        content = content.replace(
            anchor, anchor + "import com.android.gallery3d.app.PlaylistPicker;\n", 1)
        changed = True

    # onActivityResult: precisa tratar o retorno do novo REQUEST_CHOOSE_PLAYLIST
    # do mesmo jeito que REQUEST_CHOOSE_ALBUM (mesmo callback, ambos viram
    # TYPE_ALBUM no fim das contas - uma playlist tambem e uma MediaSet).
    if "REQUEST_CHOOSE_PLAYLIST" not in content:
        old_const_block = (
            "    private static final int REQUEST_CHOOSE_ALBUM = 2;\n"
        )
        new_const_block = (
            "    private static final int REQUEST_CHOOSE_ALBUM = 2;\n"
            "    // Fix (Player3D, Passo 8b): novo request code para o picker de\n"
            "    // playlist, tratado igual ao de album (mesmo callback\n"
            "    // setChoosenAlbum(), ja que uma playlist tambem e uma MediaSet\n"
            "    // comum na hora de gravar no banco do widget).\n"
            "    private static final int REQUEST_CHOOSE_PLAYLIST = 5;\n"
        )
        assert old_const_block in content, "bloco de REQUEST_CHOOSE_ALBUM nao encontrado"
        backup(path)
        content = content.replace(old_const_block, new_const_block, 1)
        changed = True

        old_dispatch = (
            "        } else if (requestCode == REQUEST_CHOOSE_ALBUM) {\n"
            "            setChoosenAlbum(data);\n"
        )
        new_dispatch = (
            "        } else if (requestCode == REQUEST_CHOOSE_ALBUM\n"
            "                || requestCode == REQUEST_CHOOSE_PLAYLIST) {\n"
            "            setChoosenAlbum(data);\n"
        )
        assert old_dispatch in content, "dispatch de REQUEST_CHOOSE_ALBUM nao encontrado"
        content = content.replace(old_dispatch, new_dispatch, 1)

    # setWidgetType(): o ramo "else" antigo (foto unica + crop) vira o novo
    # fluxo de Playlists.
    old_else = (
        "        } else {\n"
        "            // Explicitly send the intent to the DialogPhotoPicker\n"
        "            Intent request = new Intent(this, DialogPicker.class)\n"
        "                    .setAction(Intent.ACTION_GET_CONTENT)\n"
        "                    .setType(\"image/*\");\n"
        "            startActivityForResult(request, REQUEST_GET_PHOTO);\n"
        "        }\n"
    )
    new_else = (
        "        } else {\n"
        "            // Fix (Player3D, Passo 8b): terceira opcao do popup agora e\n"
        "            // \"Playlists\" (antes era \"escolher 1 imagem\", fluxo de\n"
        "            // crop de foto que nao faz mais sentido no app de musica).\n"
        "            Intent intent = new Intent(this, PlaylistPicker.class);\n"
        "            startActivityForResult(intent, REQUEST_CHOOSE_PLAYLIST);\n"
        "        }\n"
    )
    if new_else not in content:
        assert old_else in content, "ramo else de setWidgetType() nao encontrado"
        backup(path)
        content = content.replace(old_else, new_else, 1)
        changed = True

    if changed:
        write(path, content)
        print("  atualizado.")
    else:
        print("  ja aplicado, nada a fazer.")


def step_manifest():
    path = os.path.join(ROOT, "app", "src", "main", "AndroidManifest.xml")
    print(f"[Manifest] {os.path.relpath(path, ROOT)}")
    content = read(path)

    marker = 'android:name="com.android.gallery3d.app.PlaylistPicker"'
    if marker in content:
        print("  ja registrado, nada a fazer.")
        return

    anchor = (
        '        <activity android:name="com.android.gallery3d.app.AlbumPicker"\n'
        '                android:configChanges="keyboardHidden|orientation|screenSize"\n'
        '                android:theme="@style/DialogPickerTheme"/>\n'
    )
    insertion = (
        '        <activity android:name="com.android.gallery3d.app.PlaylistPicker"\n'
        '                android:configChanges="keyboardHidden|orientation|screenSize"\n'
        '                android:theme="@style/DialogPickerTheme"/>\n'
    )
    assert anchor in content, "declaracao do AlbumPicker nao encontrada no Manifest"
    backup(path)
    content = content.replace(anchor, anchor + insertion, 1)
    write(path, content)
    print("  registrado.")


def main():
    print("=== Passo 8b: popup do widget - Musicas/Playlists/Albuns ===\n")
    step_strings(os.path.join(RES, "values", "strings.xml"), "default/en")
    step_strings(os.path.join(RES, "values-pt", "strings.xml"), "pt")
    step_strings(os.path.join(RES, "values-pt-rPT", "strings.xml"), "pt-rPT")
    step_select_playlist_string(os.path.join(RES, "values", "strings.xml"), "default/en")
    step_select_playlist_string(os.path.join(RES, "values-pt", "strings.xml"), "pt")
    step_select_playlist_string(os.path.join(RES, "values-pt-rPT", "strings.xml"), "pt-rPT")
    step_playlist_picker()
    step_widget_configure()
    step_manifest()
    print("\nConcluido. Recompile e reinstale o app; ao adicionar o widget de "
          "novo (ou reconfigurar um existente), o popup deve mostrar "
          "Álbuns / Músicas / Playlists.")


if __name__ == "__main__":
    main()

#!/data/data/com.termux/files/usr/bin/bash
set -e

if [ ! -f "app/src/main/java/com/android/gallery3d/app/GalleryActivity.java" ]; then
    echo "ERRO: rode este script na raiz de ~/Galeria3D"
    exit 1
fi

echo "== 1/8: apagando o pacote com.android.gallery3d.music/ inteiro =="
rm -rf app/src/main/java/com/android/gallery3d/music
echo "removido."

echo "== 2/8: apagando a arvore de dados paralela /localaudio (experimento anterior, fase5a) =="
rm -f app/src/main/java/com/android/gallery3d/data/LocalAudioSource.java
rm -f app/src/main/java/com/android/gallery3d/data/LocalAudioAlbumSet.java
rm -f app/src/main/java/com/android/gallery3d/data/LocalAudioAlbum.java
rm -f app/src/main/java/com/android/gallery3d/data/LocalAudioItem.java

python3 << 'PYEOF'
path = "app/src/main/java/com/android/gallery3d/data/DataManager.java"
content = open(path, encoding="utf-8").read()
old = "        addSource(new LocalAudioSource(mApplication));\n"
if old in content:
    content = content.replace(old, "")
    open(path, "w", encoding="utf-8").write(content)
    print("DataManager.java: linha de registro do LocalAudioSource removida.")
else:
    print("DataManager.java: nada a remover (ja limpo).")
PYEOF

echo "== 3/8: removendo MusicPlayerActivity do AndroidManifest.xml =="
python3 << 'PYEOF'
import re
path = "app/src/main/AndroidManifest.xml"
content = open(path, encoding="utf-8").read()
pattern = re.compile(
    r'[ \t]*<activity android:name="com\.android\.gallery3d\.music\.MusicPlayerActivity".*?/>\s*\n',
    re.DOTALL
)
new_content, n = pattern.subn("", content)
if n > 0:
    open(path, "w", encoding="utf-8").write(new_content)
    print(f"Manifest: {n} bloco(s) MusicPlayerActivity removido(s).")
else:
    print("Manifest: nenhuma referencia a MusicPlayerActivity encontrada (ja limpo).")
PYEOF

echo "== 4/8: removendo campos/metodos da bottom nav do GalleryActivity.java =="
python3 << 'PYEOF'
path = "app/src/main/java/com/android/gallery3d/app/GalleryActivity.java"
lines = open(path, encoding="utf-8").read().split("\n")

# --- remove as declaracoes de campo da bottom nav, uma a uma, tolerando ausencia ---
field_markers = [
    "private View mNavTabGallery3d;",
    "private View mNavTabMusic3d;",
    "private android.widget.TextView mNavTabGallery3dLabel;",
    "private android.widget.TextView mNavTabMusic3dLabel;",
    "private View mMusic3dPlaceholder;",
    "private com.android.gallery3d.music.MusicLibraryView mMusicLibraryView;",
    "private View mGlRootView;",
    "private View mGlRootCover;",
]
removed_fields = 0
new_lines = []
for line in lines:
    if line.strip() in field_markers:
        removed_fields += 1
        continue
    new_lines.append(line)
lines = new_lines
print(f"Campos removidos: {removed_fields}/{len(field_markers)}")

# --- remove a chamada setupBottomNav(); dentro de onCreate ---
new_lines = []
removed_call = 0
for line in lines:
    if line.strip() == "setupBottomNav();":
        removed_call += 1
        continue
    new_lines.append(line)
lines = new_lines
print(f"Chamada setupBottomNav() removida: {removed_call}")

# --- remove o bloco inteiro setupBottomNav()/showGalleryTab()/showMusicTab() ---
# localiza o inicio (assinatura do setupBottomNav) e o fim (chave de fechamento
# do showMusicTab, contando chaves para ser robusto a variacoes de conteudo
# interno entre versoes diferentes do arquivo).
start_idx = None
for i, line in enumerate(lines):
    if "private void setupBottomNav()" in line:
        start_idx = i
        break

if start_idx is None:
    print("AVISO: bloco setupBottomNav/showGalleryTab/showMusicTab nao encontrado - nada a remover aqui.")
else:
    # confirma que showMusicTab existe depois do inicio, e acha o fim dele
    show_music_idx = None
    for i in range(start_idx, len(lines)):
        if "private void showMusicTab()" in lines[i]:
            show_music_idx = i
            break
    if show_music_idx is None:
        raise SystemExit("ERRO: achou setupBottomNav mas nao showMusicTab - estrutura inesperada, aborta.")

    depth = 0
    started = False
    end_idx = None
    for i in range(show_music_idx, len(lines)):
        for ch in lines[i]:
            if ch == '{':
                depth += 1
                started = True
            elif ch == '}':
                depth -= 1
        if started and depth == 0:
            end_idx = i
            break
    if end_idx is None:
        raise SystemExit("ERRO: nao achei o fechamento de showMusicTab - aborta sem alterar.")

    # remove tambem uma linha em branco imediatamente antes do bloco, se houver
    real_start = start_idx
    if real_start > 0 and lines[real_start - 1].strip() == "":
        real_start -= 1

    del lines[real_start:end_idx + 1]
    print(f"Bloco setupBottomNav/showGalleryTab/showMusicTab removido (linhas {real_start}-{end_idx}).")

open(path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF

echo "== 5/8: restaurando main.xml (removendo includes de bottom_nav_bar e music3d_placeholder) =="
cat > app/src/main/res/layout/main.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
        android:id="@+id/gallery_root"
        android:orientation="vertical"
        android:layout_width="match_parent"
        android:layout_height="match_parent">
    <include layout="@layout/gl_root_group"/>
    <FrameLayout android:id="@+id/header"
            android:visibility="gone"
            android:layout_alignParentTop="true"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>
    <FrameLayout android:id="@+id/footer"
            android:visibility="gone"
            android:layout_alignParentBottom="true"
            android:layout_alignParentLeft="true"
            android:layout_alignParentRight="true"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>
</RelativeLayout>
EOF

echo "== 6/8: apagando layouts do experimento (bottom nav + RecyclerView de musica) =="
rm -f app/src/main/res/layout/bottom_nav_bar.xml
rm -f app/src/main/res/layout/music3d_placeholder.xml
rm -f app/src/main/res/layout/music_library_view.xml
rm -f app/src/main/res/layout/item_playlist.xml
rm -f app/src/main/res/layout/item_audio_album.xml
rm -f app/src/main/res/layout/item_audio_track.xml
rm -f app/src/main/res/layout/activity_music_player.xml

echo "== 7/8: apagando drawables do experimento =="
rm -f app/src/main/res/drawable/ic_nav_gallery3d.xml
rm -f app/src/main/res/drawable/ic_nav_music3d.xml
rm -f app/src/main/res/drawable/bottom_nav_pill_background.xml
rm -f app/src/main/res/drawable/bottom_nav_selected_pill.xml
rm -f app/src/main/res/drawable/ic_music_previous.xml
rm -f app/src/main/res/drawable/ic_music_next.xml
rm -f app/src/main/res/drawable/ic_music_repeat_all.xml
rm -f app/src/main/res/drawable/music_item_background.xml
rm -f app/src/main/res/drawable/music_tab_pill_background.xml
rm -f app/src/main/res/drawable/music_repeat_toggle_bg.xml

echo "== 8/8: removendo strings da bottom nav/experimento e dependencia recyclerview =="
python3 << 'PYEOF'
path = "app/src/main/res/values/strings.xml"
content = open(path, encoding="utf-8").read()
targets = [
    '    <string name="nav_tab_gallery3d">Galeria3D</string>\n',
    '    <string name="nav_tab_music3d">Music3D</string>\n',
    '    <string name="music3d_coming_soon">Em construcao</string>\n',
    '    <string name="music3d_tab_albums">Albuns</string>\n',
    '    <string name="music3d_tab_playlists">Playlists</string>\n',
    '    <string name="music3d_empty">Nada encontrado</string>\n',
]
removed = 0
for t in targets:
    if t in content:
        content = content.replace(t, "")
        removed += 1
open(path, "w", encoding="utf-8").write(content)
print(f"strings.xml: {removed}/{len(targets)} linhas removidas.")
PYEOF

python3 << 'PYEOF'
path = "app/build.gradle.kts"
content = open(path, encoding="utf-8").read()
old = '    implementation("androidx.recyclerview:recyclerview:1.3.2")\n'
if old in content:
    content = content.replace(old, "")
    open(path, "w", encoding="utf-8").write(content)
    print("build.gradle.kts: dependencia androidx.recyclerview removida.")
else:
    print("build.gradle.kts: nada a remover (ja limpo).")
PYEOF

echo ""
echo "Passo 0 concluido. Confira abaixo se sobrou algum resquico (a lista deve vir vazia):"
grep -rn "com\.android\.gallery3d\.music\|MusicPlayerActivity\|MusicLibraryView\|nav_tab_music3d\|bottom_nav_bar\|music3d_" \
    app/src/main/java app/src/main/res app/src/main/AndroidManifest.xml 2>/dev/null || echo "(nada encontrado - limpeza completa)"
echo ""
echo "Agora rode: ./gradlew assembleDebug"

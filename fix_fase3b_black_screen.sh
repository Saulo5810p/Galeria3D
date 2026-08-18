#!/data/data/com.termux/files/usr/bin/bash
set -e

JAVA_FILE="app/src/main/java/com/android/gallery3d/app/GalleryActivity.java"

if [ ! -f "$JAVA_FILE" ]; then
    echo "ERRO: rode este script na raiz de ~/Galeria3D (arquivo $JAVA_FILE nao encontrado)"
    exit 1
fi

python3 << 'PYEOF'
path = "app/src/main/java/com/android/gallery3d/app/GalleryActivity.java"
content = open(path, encoding="utf-8").read()

old_gallery = """    private void showGalleryTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.GONE);
        if (mGlRootView != null) mGlRootView.setVisibility(View.VISIBLE);
        if (mGlRootCover != null) mGlRootCover.setVisibility(View.VISIBLE);"""

new_gallery = """    private void showGalleryTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.GONE);
        if (mGlRootView != null) {
            mGlRootView.setVisibility(View.VISIBLE);
            // NAO mexer no mGlRootCover aqui: ele existe so para tampar o
            // primeiro frame do app (flash do SurfaceView) e a logica que o
            // esconde (mFirstDraw, dentro do GLRootView) so roda uma vez na
            // vida da instancia. Deixa-lo VISIBLE de novo aqui era a causa
            // da tela preta ao voltar pra esta aba.
            ((com.android.gallery3d.ui.GLRootView) mGlRootView).onResume();
        }"""

old_music = """    private void showMusicTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.VISIBLE);
        if (mGlRootView != null) mGlRootView.setVisibility(View.GONE);
        if (mGlRootCover != null) mGlRootCover.setVisibility(View.GONE);"""

new_music = """    private void showMusicTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.VISIBLE);
        if (mGlRootView != null) {
            ((com.android.gallery3d.ui.GLRootView) mGlRootView).onPause();
            mGlRootView.setVisibility(View.GONE);
        }"""

assert content.count(old_gallery) == 1, "bloco showGalleryTab nao encontrado (arquivo ja foi alterado?)"
assert content.count(old_music) == 1, "bloco showMusicTab nao encontrado (arquivo ja foi alterado?)"

content = content.replace(old_gallery, new_gallery)
content = content.replace(old_music, new_music)

open(path, "w", encoding="utf-8").write(content)
print("GalleryActivity.java corrigido com sucesso.")
PYEOF

echo "== Diff aplicado =="
grep -n "GLRootView) mGlRootView" "$JAVA_FILE" || true
echo ""
echo "Agora rode: ./gradlew assembleDebug"

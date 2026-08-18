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
        if (mGlRootView != null) {
            mGlRootView.setVisibility(View.VISIBLE);
            // NAO mexer no mGlRootCover aqui: ele existe so para tampar o
            // primeiro frame do app (flash do SurfaceView) e a logica que o
            // esconde (mFirstDraw, dentro do GLRootView) so roda uma vez na
            // vida da instancia. Deixa-lo VISIBLE de novo aqui era a causa
            // da tela preta ao voltar pra esta aba.
            ((com.android.gallery3d.ui.GLRootView) mGlRootView).onResume();
        }"""

new_gallery = """    private void showGalleryTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.GONE);
        if (mGlRootView != null) {
            // O GLRootView NUNCA fica GONE (ver showMusicTab). Aqui so
            // religamos a renderizacao com unfreeze() - o placeholder opaco
            // que estava por cima e' quem escondia a tela, nao este view.
            ((com.android.gallery3d.ui.GLRootView) mGlRootView).unfreeze();
        }"""

old_music = """    private void showMusicTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.VISIBLE);
        if (mGlRootView != null) {
            ((com.android.gallery3d.ui.GLRootView) mGlRootView).onPause();
            mGlRootView.setVisibility(View.GONE);
        }"""

new_music = """    private void showMusicTab() {
        if (mMusic3dPlaceholder != null) mMusic3dPlaceholder.setVisibility(View.VISIBLE);
        if (mGlRootView != null) {
            // IMPORTANTE: nunca chamar mGlRootView.setVisibility(View.GONE)
            // aqui. Isso destroi de verdade a Surface/contexto EGL do
            // GLSurfaceView, forcando um invalidateAllTextures() que corrompe
            // as capas dos albuns (TiledTexture reenvia um bitmap de rascunho
            // compartilhado quando o bitmap original ja foi descartado).
            // O placeholder do Music3D (fundo opaco, desenhado por cima no
            // XML) ja cobre a tela visualmente. So pausamos o desenho com
            // freeze(), sem tocar na Surface.
            ((com.android.gallery3d.ui.GLRootView) mGlRootView).freeze();
        }"""

assert content.count(old_gallery) == 1, "bloco showGalleryTab esperado nao encontrado - rode fix_fase3b_black_screen.sh antes deste script"
assert content.count(old_music) == 1, "bloco showMusicTab esperado nao encontrado - rode fix_fase3b_black_screen.sh antes deste script"

content = content.replace(old_gallery, new_gallery)
content = content.replace(old_music, new_music)

open(path, "w", encoding="utf-8").write(content)
print("GalleryActivity.java corrigido com sucesso (capas de album).")
PYEOF

echo "== Trecho aplicado =="
grep -n "freeze()\|unfreeze()" "$JAVA_FILE"
echo ""
echo "Agora rode: ./gradlew assembleDebug"

#!/data/data/com.termux/files/usr/bin/bash
# Fix: fila de reproducao (next/previous/fim-de-faixa/notificacao) usa a
# PASTA (BUCKET_ID) do arquivo como criterio PADRAO - so cai para
# ALBUM_ID quando a pasta nao rende fila usavel.
#
# IMPORTANTE (aprendido do build que falhou antes): os 2 arquivos abaixo
# SO funcionam juntos - MoviePlayer.java chama loadQueueForTrack(album,
# bucket, uri), que so existe em MusicPlaybackService.java se ele
# tambem for a versao nova. Se so um dos dois for copiado (por exemplo,
# se voce ja tinha rodado outro fix por cima antes deste), o build
# quebra com "cannot find symbol". Por isso este script SEMPRE copia os
# dois juntos e confere antes de compilar.
set -e
cd ~/Galeria3D

TS=$(date +%Y%m%d_%H%M%S)
BKDIR="passo_fix_fila_pasta_padrao_backups/$TS"
mkdir -p "$BKDIR/app/src/main/java/com/android/gallery3d/app"

echo "==> Backup dos arquivos atuais em $BKDIR"
cp app/src/main/java/com/android/gallery3d/app/MoviePlayer.java \
   "$BKDIR/app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"
cp app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java \
   "$BKDIR/app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java"

echo "==> Copiando os 2 arquivos corrigidos para o projeto (SEMPRE OS DOIS JUNTOS)"
cp "$(dirname "$0")/MoviePlayer.java" app/src/main/java/com/android/gallery3d/app/MoviePlayer.java
cp "$(dirname "$0")/MusicPlaybackService.java" app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java

echo "==> Checando consistencia entre os 2 arquivos antes de compilar"
if grep -q "loadQueueForAlbum" app/src/main/java/com/android/gallery3d/app/MoviePlayer.java; then
    echo "ERRO: MoviePlayer.java ainda chama loadQueueForAlbum (versao antiga)."
    echo "A copia falhou ou o arquivo do zip nao e o esperado. Abortando ANTES de compilar."
    exit 1
fi
if ! grep -q "loadQueueForTrack" app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java; then
    echo "ERRO: MusicPlaybackService.java nao tem loadQueueForTrack (versao antiga)."
    echo "A copia falhou ou o arquivo do zip nao e o esperado. Abortando ANTES de compilar."
    exit 1
fi
echo "==> OK, os 2 arquivos batem entre si."

echo "==> Limpando build antigo"
./gradlew clean

echo "==> Compilando"
./gradlew assembleDebug

echo ""
echo "==> OK. IMPORTANTE - desinstale antes de reinstalar:"
echo "    adb uninstall com.xaulinxs.galeria3d"
echo "    adb install app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "==> Depois de testar avancar/anterior/fim-de-faixa/notificacao, pegue um log SO desse servico assim:"
echo "    adb logcat -c"
echo "    adb logcat com.android.gallery3d.app.MusicPlaybackService:I *:S"
echo "    (deixe rodando, teste avancar/voltar, depois Ctrl+C e me manda o texto)"
echo ""
echo "==> O log vai mostrar uma linha 'fila carregada por pasta=...' ou 'fila carregada por album=...'"
echo "    pra cada faixa - assim da pra confirmar qual criterio esta valendo em cada caso."

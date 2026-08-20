#!/data/data/com.termux/files/usr/bin/bash
# Fix: fila de reproducao (next/previous/fim-de-faixa/notificacao) agora
# usa a PASTA (BUCKET_ID) do arquivo como criterio PADRAO de agrupamento
# - so cai para ALBUM_ID quando a pasta nao rende fila usavel (pasta com
# 1 arquivo so). Essa e a forma como players de musica modernos agrupam
# faixas locais por padrao; ALBUM_ID de audio sem tag fica nulo no
# MediaStore e nao deve ser o criterio principal.
#
# Este script tambem inclui, sem retrabalho, o fix anterior (metadata/
# duracao na notificacao) - MusicPlaybackService.java enviado aqui ja
# contem os dois fixes juntos, testado por leitura estatica (chaves e
# parenteses balanceados, sem referencias orfas ao metodo antigo
# loadQueueForAlbum).
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

echo "==> Copiando os 2 arquivos corrigidos para o projeto"
cp "$(dirname "$0")/MoviePlayer.java" app/src/main/java/com/android/gallery3d/app/MoviePlayer.java
cp "$(dirname "$0")/MusicPlaybackService.java" app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java

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

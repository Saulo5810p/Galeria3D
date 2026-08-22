#!/data/data/com.termux/files/usr/bin/bash
# Fix 1 (crash): NullPointerException em AlbumSetSlidingWindow$AlbumCoverLoader
# .updateEntry() - o slot da grade podia ser reciclado (rolagem, cache
# invalidado) enquanto um carregamento assincrono de capa ainda estava em
# voo; quando o resultado chegava, o app tentava escrever num slot que ja
# nao existia mais (ou ja era de outro item) e crashava. Mesmo risco
# corrigido tambem em AlbumLabelLoader.updateEntry() (nao tinha crashado
# ainda, mas tinha exatamente o mesmo bug).
#
# Fix 2 (slider dessincronizado do audio real): ao arrastar a barra de
# progresso, cada movimento do dedo disparava um seekTo() novo no
# MediaPlayer (varios por segundo, sobrepostos) - isso podia deixar o
# audio real "preso" numa posicao antiga enquanto a barra ja mostrava a
# posicao nova. Corrigido em 2 pontos:
#   a) o audio so recebe o pedido de seek quando o dedo solta a barra
#      (nao mais a cada movimento) - a barra continua se movendo
#      normalmente durante o arraste, isso e so visual.
#   b) o estado publicado pra UI/notificacao (posicao atual) so e
#      atualizado DEPOIS que o MediaPlayer confirma que o seek de fato
#      terminou (OnSeekCompleteListener novo), nao mais na hora de pedir
#      o seek (que e assincrono) - evita a UI "adiantar" a posicao antes
#      do audio real chegar la.
#
# Logs novos de diagnostico (tag MusicPlaybackService) para qualquer caso
# residual: toda chamada a seekTo() e todo onSeekComplete() geram uma
# linha de log com a posicao antes/depois.
set -e
cd ~/Galeria3D

TS=$(date +%Y%m%d_%H%M%S)
BKDIR="passo_fix_crash_grade_e_seek_backups/$TS"
mkdir -p "$BKDIR/app/src/main/java/com/android/gallery3d/app"
mkdir -p "$BKDIR/app/src/main/java/com/android/gallery3d/ui"

echo "==> Backup dos arquivos atuais em $BKDIR"
cp app/src/main/java/com/android/gallery3d/app/MoviePlayer.java \
   "$BKDIR/app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"
cp app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java \
   "$BKDIR/app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java"
cp app/src/main/java/com/android/gallery3d/ui/AlbumSetSlidingWindow.java \
   "$BKDIR/app/src/main/java/com/android/gallery3d/ui/AlbumSetSlidingWindow.java"

echo "==> Copiando os 3 arquivos corrigidos para o projeto"
cp "$(dirname "$0")/MoviePlayer.java" app/src/main/java/com/android/gallery3d/app/MoviePlayer.java
cp "$(dirname "$0")/MusicPlaybackService.java" app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java
cp "$(dirname "$0")/AlbumSetSlidingWindow.java" app/src/main/java/com/android/gallery3d/ui/AlbumSetSlidingWindow.java

echo "==> Checando consistencia entre MoviePlayer/MusicPlaybackService antes de compilar"
if grep -q "loadQueueForAlbum" app/src/main/java/com/android/gallery3d/app/MoviePlayer.java; then
    echo "ERRO: MoviePlayer.java ainda chama loadQueueForAlbum (versao antiga). Abortando ANTES de compilar."
    exit 1
fi
if ! grep -q "loadQueueForTrack" app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java; then
    echo "ERRO: MusicPlaybackService.java nao tem loadQueueForTrack (versao antiga). Abortando ANTES de compilar."
    exit 1
fi
if ! grep -q "OnSeekCompleteListener" app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java; then
    echo "ERRO: MusicPlaybackService.java sem OnSeekCompleteListener - copia da versao errada. Abortando."
    exit 1
fi
echo "==> OK, arquivos consistentes entre si."

echo "==> Limpando build antigo"
./gradlew clean

echo "==> Compilando"
./gradlew assembleDebug

echo ""
echo "==> OK. IMPORTANTE - desinstale antes de reinstalar:"
echo "    adb uninstall com.xaulinxs.galeria3d"
echo "    adb install app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "==> Teste: 1) abrir uma faixa sem capa (o crash da grade deve sumir)"
echo "           2) arrastar a barra de progresso durante a reproducao (o audio deve seguir a nova posicao)"
echo ""
echo "==> Se algo persistir, pegue o log filtrado:"
echo "    adb logcat -c"
echo "    adb logcat com.android.gallery3d.app.MusicPlaybackService:I *:S"
echo "    (deixe rodando, reproduza o problema, Ctrl+C, me manda o texto)"

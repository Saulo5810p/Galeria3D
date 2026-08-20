#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/Galeria3D

TS=$(date +%Y%m%d_%H%M%S)
BKDIR="passo_fix_fila_pasta_backups/$TS"
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
echo "==> Depois de testar avançar/anterior, pegue um log SÓ desse app assim:"
echo "    adb logcat -c"
echo "    adb logcat com.android.gallery3d.app.MusicPlaybackService:I *:S"
echo "    (deixe rodando, teste o avançar no app, depois Ctrl+C e me manda o texto)"

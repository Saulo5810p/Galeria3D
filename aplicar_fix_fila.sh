#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/Galeria3D

TS=$(date +%Y%m%d_%H%M%S)
BKDIR="passo_fix_corrida_fila_backups/$TS"
mkdir -p "$BKDIR/app/src/main/java/com/android/gallery3d/app"

echo "==> Fazendo backup do MoviePlayer.java atual em $BKDIR"
cp app/src/main/java/com/android/gallery3d/app/MoviePlayer.java \
   "$BKDIR/app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"

echo "==> Copiando MoviePlayer.java corrigido para o projeto"
cp "$(dirname "$0")/MoviePlayer.java" app/src/main/java/com/android/gallery3d/app/MoviePlayer.java

echo "==> Limpando build antigo (evita instalar um APK desatualizado)"
./gradlew clean

echo "==> Compilando"
./gradlew assembleDebug

echo ""
echo "==> OK. Agora DESINSTALE o app do dispositivo antes de reinstalar:"
echo "    adb uninstall com.xaulinxs.galeria3d"
echo "    adb install app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "(a desinstalacao e importante porque o Service em foreground as vezes"
echo " sobrevive a uma reinstalacao sem uninstall e continua rodando o"
echo " codigo antigo ate o Android matar o processo)"

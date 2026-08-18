#!/data/data/com.termux/files/usr/bin/bash
set -e

BUILD_FILE="app/build.gradle.kts"

echo "== Corrigindo namespace (R class) para com.android.gallery3d, mantendo applicationId =="
sed -i 's/namespace = "com.xaulinxs.galeria3d"/namespace = "com.android.gallery3d"/' "$BUILD_FILE"

echo "== Adicionando dependencias mp4parser e xmpcore =="
sed -i '/implementation("androidx.legacy:legacy-support-core-ui:1.0.0")/a\    implementation("com.googlecode.mp4parser:isoparser:1.1.22")\n    implementation("com.adobe.xmp:xmpcore:6.1.11")' "$BUILD_FILE"

echo "== Conferindo build.gradle.kts =="
cat "$BUILD_FILE"

echo "== Fix concluido =="

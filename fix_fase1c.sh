#!/data/data/com.termux/files/usr/bin/bash
set -e

MANIFEST="app/src/main/AndroidManifest.xml"

echo "== Removendo atributo package= do AndroidManifest.xml =="
sed -i 's/ package="com\.android\.gallery3d"//' "$MANIFEST"

echo "== Conferindo =="
grep -n "package=" "$MANIFEST" || echo "Nenhum atributo package= restante — ok"

echo "== Fix concluido =="

#!/data/data/com.termux/files/usr/bin/bash
set -e

JAVA_DIR="app/src/main/java"

echo "== Trocando com.adobe.xmp por com.adobe.internal.xmp nos imports =="
FILES=$(grep -rl "com\.adobe\.xmp" "$JAVA_DIR" 2>/dev/null || true)

if [ -z "$FILES" ]; then
  echo "Nenhum arquivo com com.adobe.xmp encontrado."
else
  for f in $FILES; do
    sed -i 's/com\.adobe\.xmp/com.adobe.internal.xmp/g' "$f"
    echo "Corrigido: $f"
  done
fi

echo "== Conferindo se sobrou algum import antigo =="
grep -rn "^import com\.adobe\.xmp\." "$JAVA_DIR" 2>/dev/null || echo "Nenhum import antigo restante — ok"

echo "== Fix concluido =="

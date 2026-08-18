#!/data/data/com.termux/files/usr/bin/bash
set -e

cd app/src/main/res

echo "== Corrigindo namespace de atributos customizados (res/com.android.gallery3d -> res-auto) =="
FILES=$(grep -rl 'res/com.android.gallery3d' . 2>/dev/null || true)

if [ -z "$FILES" ]; then
  echo "Nenhum arquivo com o namespace antigo encontrado."
else
  for f in $FILES; do
    sed -i 's#http://schemas.android.com/apk/res/com.android.gallery3d#http://schemas.android.com/apk/res-auto#g' "$f"
    echo "Corrigido: $f"
  done
fi

echo "== Conferindo se sobrou alguma referencia antiga =="
RESTANTE=$(grep -rl 'res/com.android.gallery3d' . 2>/dev/null | wc -l)
echo "Arquivos restantes: $RESTANTE"

echo "== Fix concluido =="

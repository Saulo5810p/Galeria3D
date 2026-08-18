#!/data/data/com.termux/files/usr/bin/bash
set -e

cd app/src/main/res

echo "== Removendo drawable vazio/corrompido sem uso =="
rm -fv filtershow_state_button_background
[ -f drawable/filtershow_state_button_background ] && rm -fv drawable/filtershow_state_button_background

echo "== Removendo entradas duplicadas product=\"nosdcard\" em todos os strings.xml =="
find . -path "*/values*/strings.xml" -exec sed -i '/product="nosdcard"/d' {} \;

echo "== Conferindo se ainda sobrou alguma duplicata =="
DUPES=$(grep -rl 'product="nosdcard"' . 2>/dev/null | wc -l)
echo "Arquivos restantes com nosdcard: $DUPES"

echo "== Fix concluido =="

#!/data/data/com.termux/files/usr/bin/bash
set -e

FILE=$(find . -iname "AbstractGalleryActivity.java" | head -1)
echo "Arquivo: $FILE"

echo "== Adicionando import de ActivityNotFoundException =="
if ! grep -q "import android.content.ActivityNotFoundException;" "$FILE"; then
  sed -i '/import android.content.ComponentName;/a import android.content.ActivityNotFoundException;' "$FILE"
fi

echo "== Envolvendo printBitmap com catch de ActivityNotFoundException =="
python3 - "$FILE" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path, "r") as f:
    content = f.read()

old = """        PrintHelper printer = new PrintHelper(this);
        try {
            printer.printBitmap(path, uri);
        } catch (FileNotFoundException fnfe) {
            Log.e(TAG, "Error printing an image", fnfe);
        }"""

new = """        PrintHelper printer = new PrintHelper(this);
        try {
            printer.printBitmap(path, uri);
        } catch (FileNotFoundException fnfe) {
            Log.e(TAG, "Error printing an image", fnfe);
        } catch (ActivityNotFoundException anfe) {
            Log.e(TAG, "No print service available on this device", anfe);
            android.widget.Toast.makeText(this,
                    "Nenhum servico de impressao disponivel neste dispositivo",
                    android.widget.Toast.LENGTH_LONG).show();
        }"""

if old not in content:
    print("AVISO: trecho original nao encontrado exatamente como esperado - nada foi alterado.")
    sys.exit(1)

content = content.replace(old, new)
with open(path, "w") as f:
    f.write(content)
print("Patch aplicado com sucesso.")
PYEOF

echo "== Fix concluido =="

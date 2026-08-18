#!/data/data/com.termux/files/usr/bin/bash
set -e
sed -i 's#-I"$JPEG_DIR" -fPIC -c#-I"$JPEG_DIR" -I"app/src/main/jni_jpegstream/third_party_stubs" -fPIC -c#' fase2c_full_native.sh
echo "== Conferindo a linha alterada =="
grep -n "third_party_stubs" fase2c_full_native.sh

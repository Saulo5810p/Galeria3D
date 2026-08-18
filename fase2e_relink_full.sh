#!/data/data/com.termux/files/usr/bin/bash
set -e

JNI_DIR="app/src/main/jni_eglfence_filtershow"
OUT_LIBS_DIR="app/src/main/jniLibs/arm64-v8a"
BUILD_TMP="native_build_tmp"
TARGET="aarch64-linux-android24"
STUBS="linkstubs"
EGL_INC="$JNI_DIR/third_party/khronos_headers"

rm -rf "$BUILD_TMP"
mkdir -p "$BUILD_TMP"

echo "== Relinkando libjni_eglfence.so contra stubs (liblog + libEGL) =="
clang++ -target "$TARGET" -shared \
  -o "$OUT_LIBS_DIR/libjni_eglfence.so" \
  "$JNI_DIR/jni_egl_fence.cpp" \
  -Wall -Wextra -Wno-unused-parameter -DEGL_EGLEXT_PROTOTYPES \
  -I"$JNI_DIR" -I"$EGL_INC" \
  -fPIC \
  -L"$STUBS" -l:liblog.so -l:libEGL.so \
  -Wl,-soname,libjni_eglfence.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_eglfence.so | cut -f1)"

echo "== Recompilando objetos dos filtros =="
FILTER_SRCS_C="gradient saturated exposure edge contrast hue shadows highlight hsv vibrance geometry negative redEyeMath fx wbalance redeye bwfilter"
FILTER_SRCS_CC="tinyplanet kmeans"

for name in $FILTER_SRCS_C; do
  clang -target "$TARGET" -Wall -Wextra -Wno-unused-parameter \
    -O3 -ffast-math -funroll-loops \
    -I"$JNI_DIR/filters" -fPIC -c "$JNI_DIR/filters/$name.c" \
    -o "$BUILD_TMP/$name.o"
done
for name in $FILTER_SRCS_CC; do
  clang++ -target "$TARGET" -Wall -Wextra -Wno-unused-parameter \
    -O3 -ffast-math -funroll-loops \
    -I"$JNI_DIR/filters" -fPIC -c "$JNI_DIR/filters/$name.cc" \
    -o "$BUILD_TMP/$name.o"
done

echo "== Linkando libjni_filtershow_filters.so contra stub (libjnigraphics) =="
clang++ -target "$TARGET" -shared \
  -o "$OUT_LIBS_DIR/libjni_filtershow_filters.so" \
  "$BUILD_TMP"/*.o \
  -L"$STUBS" -l:libjnigraphics.so \
  -Wl,-soname,libjni_filtershow_filters.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_filtershow_filters.so | cut -f1)"

echo "== Conferindo DT_NEEDED dos .so (deve mostrar liblog/libEGL/libjnigraphics agora) =="
echo "--- libjni_eglfence.so ---"
readelf -d "$OUT_LIBS_DIR/libjni_eglfence.so" | grep NEEDED
echo "--- libjni_filtershow_filters.so ---"
readelf -d "$OUT_LIBS_DIR/libjni_filtershow_filters.so" | grep NEEDED

echo "== Fim =="

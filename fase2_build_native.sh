#!/data/data/com.termux/files/usr/bin/bash
set -e

JNI_DIR="app/src/main/jni_eglfence_filtershow"
OUT_LIBS_DIR="app/src/main/jniLibs/arm64-v8a"
BUILD_TMP="native_build_tmp"
TARGET="aarch64-linux-android24"

echo "== Preparando pastas de saida =="
mkdir -p "$OUT_LIBS_DIR"
rm -rf "$BUILD_TMP"
mkdir -p "$BUILD_TMP"

EGL_INC="$JNI_DIR/third_party/khronos_headers"

echo "== Compilando libjni_eglfence.so =="
clang++ -target "$TARGET" \
  -Wall -Wextra -Wno-unused-parameter \
  -DEGL_EGLEXT_PROTOTYPES \
  -I"$JNI_DIR" -I"$EGL_INC" \
  -fPIC -shared \
  -o "$OUT_LIBS_DIR/libjni_eglfence.so" \
  "$JNI_DIR/jni_egl_fence.cpp" \
  -Wl,--unresolved-symbols=ignore-all \
  -Wl,-soname,libjni_eglfence.so

echo "libjni_eglfence.so: $(ls -la $OUT_LIBS_DIR/libjni_eglfence.so)"

echo "== Compilando objetos de libjni_filtershow_filters.so =="
FILTER_SRCS_C="gradient saturated exposure edge contrast hue shadows highlight hsv vibrance geometry negative redEyeMath fx wbalance redeye bwfilter"
FILTER_SRCS_CC="tinyplanet kmeans"

for name in $FILTER_SRCS_C; do
  echo "  compilando filters/$name.c"
  clang -target "$TARGET" \
    -Wall -Wextra -Wno-unused-parameter \
    -O3 -ffast-math -funroll-loops \
    -I"$JNI_DIR/filters" \
    -fPIC -c "$JNI_DIR/filters/$name.c" \
    -o "$BUILD_TMP/$name.o"
done

for name in $FILTER_SRCS_CC; do
  echo "  compilando filters/$name.cc"
  clang++ -target "$TARGET" \
    -Wall -Wextra -Wno-unused-parameter \
    -O3 -ffast-math -funroll-loops \
    -I"$JNI_DIR/filters" \
    -fPIC -c "$JNI_DIR/filters/$name.cc" \
    -o "$BUILD_TMP/$name.o"
done

echo "== Linkando libjni_filtershow_filters.so =="
clang++ -target "$TARGET" \
  -shared \
  -o "$OUT_LIBS_DIR/libjni_filtershow_filters.so" \
  "$BUILD_TMP"/*.o \
  -Wl,--unresolved-symbols=ignore-all \
  -Wl,-soname,libjni_filtershow_filters.so

echo "libjni_filtershow_filters.so: $(ls -la $OUT_LIBS_DIR/libjni_filtershow_filters.so)"

echo "== Fim: .so gerados em $OUT_LIBS_DIR =="
ls -la "$OUT_LIBS_DIR"

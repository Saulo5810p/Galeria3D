#!/data/data/com.termux/files/usr/bin/bash
set -e

OUT_LIBS_DIR="app/src/main/jniLibs/arm64-v8a"
BUILD_TMP="native_build_tmp"
TARGET="aarch64-linux-android24"
STUBS="linkstubs"

echo "== Relinkando libjni_eglfence.so contra stubs (liblog + libEGL) =="
clang++ -target "$TARGET" -shared \
  -o "$OUT_LIBS_DIR/libjni_eglfence.so" \
  app/src/main/jni_eglfence_filtershow/jni_egl_fence.cpp \
  -Wall -Wextra -Wno-unused-parameter -DEGL_EGLEXT_PROTOTYPES \
  -I"app/src/main/jni_eglfence_filtershow" -I"app/src/main/jni_eglfence_filtershow/third_party/khronos_headers" \
  -fPIC \
  -L"$STUBS" -l:liblog.so -l:libEGL.so \
  -Wl,-soname,libjni_eglfence.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_eglfence.so | cut -f1)"

echo "== Relinkando libjni_filtershow_filters.so contra stub (libjnigraphics) =="
# usa os .o ja compilados na etapa anterior, so troca a fase de link
clang++ -target "$TARGET" -shared \
  -o "$OUT_LIBS_DIR/libjni_filtershow_filters.so" \
  "$BUILD_TMP"/gradient.o "$BUILD_TMP"/saturated.o "$BUILD_TMP"/exposure.o "$BUILD_TMP"/edge.o \
  "$BUILD_TMP"/contrast.o "$BUILD_TMP"/hue.o "$BUILD_TMP"/shadows.o "$BUILD_TMP"/highlight.o \
  "$BUILD_TMP"/hsv.o "$BUILD_TMP"/vibrance.o "$BUILD_TMP"/geometry.o "$BUILD_TMP"/negative.o \
  "$BUILD_TMP"/redEyeMath.o "$BUILD_TMP"/fx.o "$BUILD_TMP"/wbalance.o "$BUILD_TMP"/redeye.o \
  "$BUILD_TMP"/bwfilter.o "$BUILD_TMP"/tinyplanet.o "$BUILD_TMP"/kmeans.o \
  -L"$STUBS" -l:libjnigraphics.so \
  -Wl,-soname,libjni_filtershow_filters.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_filtershow_filters.so | cut -f1)"

echo "== Conferindo DT_NEEDED dos dois .so =="
readelf -d "$OUT_LIBS_DIR/libjni_eglfence.so" | grep NEEDED
readelf -d "$OUT_LIBS_DIR/libjni_filtershow_filters.so" | grep NEEDED

echo "== Fim =="

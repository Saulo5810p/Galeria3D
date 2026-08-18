#!/data/data/com.termux/files/usr/bin/bash
set -e

JNI_DIR="app/src/main/jni_eglfence_filtershow"
JPEG_DIR="app/src/main/jni_jpegstream/src"
OUT_LIBS_DIR="app/src/main/jniLibs/arm64-v8a"
BUILD_TMP="native_build_tmp"
TARGET="aarch64-linux-android24"
TERMUX_LIB="/data/data/com.termux/files/usr/lib"

mkdir -p "$OUT_LIBS_DIR"
rm -rf "$BUILD_TMP"
mkdir -p "$BUILD_TMP"

EGL_INC="$JNI_DIR/third_party/khronos_headers"

echo "== [1/3] Recompilando libjni_eglfence.so com libc++ estatica =="
clang++ -target "$TARGET" \
  -Wall -Wextra -Wno-unused-parameter \
  -DEGL_EGLEXT_PROTOTYPES \
  -I"$JNI_DIR" -I"$EGL_INC" \
  -fPIC -shared -static-libstdc++ \
  -o "$OUT_LIBS_DIR/libjni_eglfence.so" \
  "$JNI_DIR/jni_egl_fence.cpp" \
  -Wl,--unresolved-symbols=ignore-all \
  -Wl,-soname,libjni_eglfence.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_eglfence.so | cut -f1)"

echo "== [2/3] Recompilando libjni_filtershow_filters.so com libc++ estatica =="
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

clang++ -target "$TARGET" -shared -static-libstdc++ \
  -o "$OUT_LIBS_DIR/libjni_filtershow_filters.so" \
  "$BUILD_TMP"/*.o \
  -Wl,--unresolved-symbols=ignore-all \
  -Wl,-soname,libjni_filtershow_filters.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_filtershow_filters.so | cut -f1)"

echo "== [3/3] Compilando libjni_jpegstream.so =="
rm -rf "$BUILD_TMP"/*.o
JPEG_SRCS="inputstream_wrapper jpegstream jerr_hook jpeg_hook jpeg_writer jpeg_reader outputstream_wrapper stream_wrapper"

for name in $JPEG_SRCS; do
  echo "  compilando src/$name.cpp"
  clang++ -target "$TARGET" \
    -Wall -Wextra -Wno-unused-parameter \
    -O3 -ffast-math -funroll-loops \
    -I"$JPEG_DIR" -fPIC -c "$JPEG_DIR/$name.cpp" \
    -o "$BUILD_TMP/jpeg_$name.o"
done

echo "== Copiando libjpeg.so.8 do Termux pro APK (soname exato) =="
cp -L "$TERMUX_LIB/libjpeg.so.8.3.2" "$OUT_LIBS_DIR/libjpeg.so.8"

echo "== Linkando libjni_jpegstream.so =="
clang++ -target "$TARGET" -shared -static-libstdc++ \
  -o "$OUT_LIBS_DIR/libjni_jpegstream.so" \
  "$BUILD_TMP"/jpeg_*.o \
  -L"$TERMUX_LIB" -l:libjpeg.so.8 \
  -Wl,--unresolved-symbols=ignore-all \
  -Wl,-soname,libjni_jpegstream.so
echo "OK: $(du -h $OUT_LIBS_DIR/libjni_jpegstream.so | cut -f1)"

echo "== Resultado final em $OUT_LIBS_DIR =="
ls -la "$OUT_LIBS_DIR"

#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "== Fase 1: reestruturando Galeria3D pra Gradle =="

# --- checagem de sanidade ---
if [ ! -f "AndroidManifest.xml" ] || [ ! -d "src" ]; then
  echo "ERRO: rode este script dentro da pasta Galeria3D (onde estao AndroidManifest.xml, src/, res/)"
  exit 1
fi

APPLICATION_ID="com.xaulinxs.galeria3d"
AAPT2_PATH="/data/data/com.termux/files/usr/bin/aapt2"

# --- estrutura de pastas ---
mkdir -p app/src/main/java
mkdir -p app/src/main/res
mkdir -p app/src/main/jni

# --- move recursos e manifest ---
mv res/* app/src/main/res/
mv AndroidManifest.xml app/src/main/AndroidManifest.xml
[ -f proguard.flags ] && mv proguard.flags app/proguard-rules.pro

# --- funde src + src_pd + gallerycommon num unico source set ---
cp -r src/* app/src/main/java/
cp -r src_pd/* app/src/main/java/
cp -r gallerycommon/src/* app/src/main/java/

# --- move codigo nativo pra dentro do modulo (fica parado ate a Fase 2) ---
mv jni app/src/main/jni_eglfence_filtershow
mv jni_jpegstream app/src/main/jni_jpegstream

# --- limpa o que era especifico do build Soong/AOSP ---
rm -f Android.bp jni/Android.bp jni_jpegstream/Android.bp gallerycommon/Android.bp
rm -f CleanSpec.mk OWNERS jarjar-rules.txt
rm -rf src src_pd gallerycommon

# --- settings.gradle.kts ---
cat > settings.gradle.kts << 'EOF'
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "Galeria3D"
include(":app")
EOF

# --- build.gradle.kts (raiz) ---
cat > build.gradle.kts << 'EOF'
plugins {
    id("com.android.application") version "8.7.3" apply false
}
EOF

# --- gradle.properties ---
cat > gradle.properties << EOF
org.gradle.jvmargs=-Xmx2048m
android.useAndroidX=true
android.nonTransitiveRClass=true
android.aapt2FromMavenOverride=$AAPT2_PATH
EOF

# --- local.properties ---
if [ -z "\$ANDROID_HOME" ]; then
  SDK_GUESS="/data/data/com.termux/files/home/android-sdk"
else
  SDK_GUESS="\$ANDROID_HOME"
fi
cat > local.properties << EOF
sdk.dir=$SDK_GUESS
EOF
echo ">> Confira se sdk.dir em local.properties esta correto pro seu setup."

# --- app/build.gradle.kts ---
cat > app/build.gradle.kts << EOF
plugins {
    id("com.android.application")
}

android {
    namespace = "$APPLICATION_ID"
    compileSdk = 34

    defaultConfig {
        applicationId = "$APPLICATION_ID"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    sourceSets["main"].java.srcDirs("src/main/java")
    sourceSets["main"].res.srcDirs("src/main/res")
    sourceSets["main"].manifest.srcFile("src/main/AndroidManifest.xml")

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.core:core:1.13.1")
    implementation("androidx.fragment:fragment:1.8.2")
    implementation("androidx.legacy:legacy-support-v13:1.0.0")
    implementation("androidx.legacy:legacy-support-core-ui:1.0.0")
}
EOF

# --- gera o wrapper do gradle (precisa do comando gradle instalado: pkg install gradle) ---
if command -v gradle >/dev/null 2>&1; then
  gradle wrapper --gradle-version 9.6.1 --distribution-type all
  chmod +x gradlew
  echo "== gradlew gerado =="
else
  echo "AVISO: comando 'gradle' nao encontrado. Rode: pkg install gradle"
  echo "Depois rode de novo so esta parte: gradle wrapper --gradle-version 9.6.1 --distribution-type all"
fi

echo "== Fase 1 concluida. Estrutura pronta em app/src/main =="
echo "== Codigo nativo guardado em app/src/main/jni_eglfence_filtershow e jni_jpegstream (Fase 2) =="

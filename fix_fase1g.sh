#!/data/data/com.termux/files/usr/bin/bash
set -e

BUILD_FILE="app/build.gradle.kts"
VIDEOUTILS="app/src/main/java/com/android/gallery3d/app/VideoUtils.java"
APPLICATION_ID="com.xaulinxs.galeria3d"

echo "== Estado atual do build.gradle.kts (antes do fix) =="
cat "$BUILD_FILE"
echo "== fim =="

echo "== Parando o daemon do Gradle (evita cache de dependencia zoada) =="
./gradlew --stop || true

echo "== Reescrevendo app/build.gradle.kts (com useLibrary org.apache.http.legacy) =="
cat > "$BUILD_FILE" << EOF
plugins {
    id("com.android.application")
}

android {
    namespace = "com.android.gallery3d"
    compileSdk = 34

    defaultConfig {
        applicationId = "$APPLICATION_ID"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    useLibrary("org.apache.http.legacy")

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
    implementation("com.googlecode.mp4parser:isoparser:1.1.22")
    implementation("com.adobe.xmp:xmpcore:6.1.11")
}
EOF

echo "== Corrigindo VideoUtils.java: IsoFile -> Container, getBox -> writeContainer =="
sed -i 's/import com\.coremedia\.iso\.IsoFile;/import com.coremedia.iso.boxes.Container;/' "$VIDEOUTILS"
sed -i 's/IsoFile out = new DefaultMp4Builder().build(movie);/Container out = new DefaultMp4Builder().build(movie);/' "$VIDEOUTILS"
sed -i 's/out\.getBox(fc); \/\/ This one build up the memory\./out.writeContainer(fc); \/\/ This one build up the memory./' "$VIDEOUTILS"

echo "== Conferindo alteracoes no VideoUtils.java =="
grep -n "Container\|writeContainer" "$VIDEOUTILS"

echo "== Estado final do build.gradle.kts (depois do fix) =="
cat "$BUILD_FILE"

echo "== Fix concluido =="

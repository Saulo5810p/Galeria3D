plugins {
    id("com.android.application")
}

android {
    namespace = "com.android.gallery3d"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.xaulinxs.galeria3d"
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

configurations.all {
    exclude(group = "org.jetbrains.kotlin", module = "kotlin-stdlib-jdk7")
    exclude(group = "org.jetbrains.kotlin", module = "kotlin-stdlib-jdk8")
}

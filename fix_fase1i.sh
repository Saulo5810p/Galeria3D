#!/data/data/com.termux/files/usr/bin/bash
set -e

BUILD_FILE="app/build.gradle.kts"

echo "== Adicionando exclusao global de kotlin-stdlib-jdk7/jdk8 (duplicadas na 1.8.22) =="

if grep -q "configurations.all" "$BUILD_FILE"; then
  echo "Bloco configurations.all ja existe, pulando insercao (confira manualmente se precisar)."
else
  cat >> "$BUILD_FILE" << 'EOF'

configurations.all {
    exclude(group = "org.jetbrains.kotlin", module = "kotlin-stdlib-jdk7")
    exclude(group = "org.jetbrains.kotlin", module = "kotlin-stdlib-jdk8")
}
EOF
fi

echo "== Conferindo final do build.gradle.kts =="
tail -8 "$BUILD_FILE"

echo "== Fix concluido =="

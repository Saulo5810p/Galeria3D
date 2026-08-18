#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, subprocess

os.chdir(os.path.expanduser("~/Galeria3D"))
DATA = "app/src/main/java/com/android/gallery3d/data"
path = os.path.join(DATA, "LocalSource.java")

if not os.path.isfile(path):
    print("ERRO: " + path + " nao existe. Confirme que esta na pasta certa (~/Galeria3D).")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "                        LocalAlbumSet.PATH_VIDEO.getChild(bucketId));\n"
new = "                        LocalAlbumSet.PATH_AUDIO.getChild(bucketId));\n"

count = content.count(old)
if count != 1:
    print("ERRO: encontrei " + str(count) + " ocorrencia(s) do trecho esperado (esperava 1).")
    print("Isso pode significar que o arquivo ja foi corrigido, ou que esta diferente do previsto.")
    print("Trecho procurado:")
    print(old)
    sys.exit(1)

content = content.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: LocalSource.java corrigido (PATH_VIDEO -> PATH_AUDIO, dentro do caso LOCAL_ALL_ALBUM)")

print()
print("=== Verificacao final: nenhum PATH_VIDEO deve sobrar no projeto ===")
leftover = subprocess.run(
    ["grep", "-rn", "PATH_VIDEO", "app/src/main/java/"],
    capture_output=True, text=True
).stdout
if leftover.strip():
    print("!!! AINDA HA PATH_VIDEO NO PROJETO !!!")
    print(leftover)
else:
    print("OK: nenhum resto de PATH_VIDEO no projeto")

print()
print("Hotfix aplicado. Agora rode: ./gradlew assembleDebug")

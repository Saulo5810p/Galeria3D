#!/usr/bin/env python3
"""
Fix: Crash NullPointerException ao abrir a primeira musica no filtro de Musicas.
Arquivo: app/src/main/java/com/android/gallery3d/ui/AlbumSlidingWindow.java

Rode este script de dentro de ~/Galeria3D (raiz do repo clonado).
Idempotente: pode rodar 2x sem quebrar nada.
"""

import os
import sys
import shutil

REL_PATH = "app/src/main/java/com/android/gallery3d/ui/AlbumSlidingWindow.java"

OLD = """            AlbumEntry entry = mData[mSlotIndex % mData.length];
            entry.bitmapTexture = new TiledTexture(bitmap);
            entry.content = entry.bitmapTexture;"""

NEW = """            AlbumEntry entry = mData[mSlotIndex % mData.length];
            // Passo 6 (fix crash): o slot pode ter sido reciclado (rolagem/lista
            // trocada) enquanto este carregamento assincrono ainda estava em voo.
            // Nesse caso 'entry' pode ser nulo, ou pode ja pertencer a outro item
            // (contentLoader != this). Descarta o resultado obsoleto nos dois casos.
            if (entry == null || entry.contentLoader != this) {
                return;
            }
            entry.bitmapTexture = new TiledTexture(bitmap);
            entry.content = entry.bitmapTexture;"""

MARKER = "// Passo 6 (fix crash): o slot pode ter sido reciclado"


def main():
    if not os.path.isfile(REL_PATH):
        print(f"ERRO: nao encontrei {REL_PATH}")
        print("Rode este script de dentro da pasta raiz do repo (~/Galeria3D).")
        sys.exit(1)

    with open(REL_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER in content:
        print("Fix ja aplicado anteriormente — nada a fazer (script e idempotente).")
        sys.exit(0)

    if OLD not in content:
        print("ERRO: nao encontrei o trecho esperado no arquivo.")
        print("O arquivo pode ja ter sido modificado de outra forma. Abortando sem tocar em nada.")
        sys.exit(1)

    backup_path = REL_PATH + ".bak"
    shutil.copyfile(REL_PATH, backup_path)
    print(f"Backup criado em: {backup_path}")

    new_content = content.replace(OLD, NEW)

    with open(REL_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Fix aplicado com sucesso em:")
    print(f"  {REL_PATH}")
    print()
    print("O que mudou: updateEntry() agora descarta o resultado do carregamento")
    print("de capa se o slot foi reciclado (entry nulo) ou ja pertence a outra")
    print("faixa (contentLoader != this) — mesmo padrao do fix anterior em")
    print("AlbumSetSlidingWindow, aplicado agora na lista de faixas do filtro Musicas.")
    print()
    print("Proximo passo: recompile o app e teste abrir a primeira musica no filtro de Musicas.")


if __name__ == "__main__":
    main()

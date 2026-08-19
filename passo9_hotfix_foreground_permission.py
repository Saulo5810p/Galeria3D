#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotfix do Passo 9 - permissoes de Foreground Service faltando (Player3D)

Sintoma: app crasha ao tocar a primeira faixa com
    SecurityException: Permission Denial: startForeground from pid=...
    requires android.permission.FOREGROUND_SERVICE

Causa: o Passo 9 declarou o <service ... foregroundServiceType="mediaPlayback">
no AndroidManifest.xml, mas nao declarou as permissoes que esse tipo de
foreground service exige:
- android.permission.FOREGROUND_SERVICE: obrigatoria desde o Android 9
  (API 28) para qualquer chamada a startForeground().
- android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK: obrigatoria desde
  o Android 14 (API 34) especificamente para foregroundServiceType=
  "mediaPlayback" (o projeto tem targetSdk=34). Sem ela, o sistema recusa
  o startForeground() mesmo com a primeira permissao presente.

Este script adiciona as duas <uses-permission> no AndroidManifest.xml, logo
apos a ultima permissao ja existente (POST_NOTIFICATIONS, adicionada no
proprio Passo 9).

Rode este script na RAIZ do projeto (~/Galeria3D no Termux):
    python3 passo9_hotfix_foreground_permission.py

Regras seguidas (workflow combinado): falha cedo se o marcador esperado nao
for encontrado; backup fora da arvore res/ (nao se aplica aqui, o arquivo
editado e o AndroidManifest.xml, fora de res/ de qualquer forma, mas o
backup ainda vai para passo9_backups/ pra manter o padrao ja usado no
projeto); idempotente (rodar de novo nao duplica); termina com verificacao.
"""

import os
import sys

MANIFEST_PATH = "app/src/main/AndroidManifest.xml"
BACKUP_DIR = "passo9_backups"

FOREGROUND_SERVICE_PERM = (
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n'
)
FOREGROUND_SERVICE_MEDIA_PERM = (
    '    <uses-permission android:name='
    '"android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />\n'
)


def fail(msg):
    print("ERRO: " + msg)
    sys.exit(1)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def backup(path):
    bak = os.path.join(BACKUP_DIR, path + ".bak_hotfix_foreground")
    if not os.path.isfile(bak):
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        write(bak, read(path))
        print("Backup criado: %s" % bak)
    else:
        print("Backup ja existia, mantido: %s" % bak)


def main():
    if not os.path.isfile(MANIFEST_PATH):
        fail(
            "arquivo esperado nao encontrado: %s\n"
            "Rode este script na raiz do projeto (~/Galeria3D)." % MANIFEST_PATH
        )

    content = read(MANIFEST_PATH)

    has_foreground = "android.permission.FOREGROUND_SERVICE\"" in content
    has_foreground_media = "android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK\"" in content

    if has_foreground and has_foreground_media:
        print("Aviso: as duas permissoes ja existem em %s, nada a fazer." % MANIFEST_PATH)
        return

    anchor = '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n'
    count = content.count(anchor)
    if count == 0:
        fail(
            "marcador esperado (permissao POST_NOTIFICATIONS) nao encontrado em %s.\n"
            "O arquivo mudou desde a especificacao - nada foi alterado."
            % MANIFEST_PATH
        )
    if count > 1:
        fail(
            "marcador apareceu %d vezes em %s (esperado exatamente 1). "
            "Nada foi alterado, script parou por seguranca." % (count, MANIFEST_PATH)
        )

    backup(MANIFEST_PATH)

    addition = ""
    if not has_foreground:
        addition += FOREGROUND_SERVICE_PERM
    if not has_foreground_media:
        addition += FOREGROUND_SERVICE_MEDIA_PERM

    content = content.replace(anchor, anchor + addition, 1)
    write(MANIFEST_PATH, content)
    print("OK: permissoes de foreground service adicionadas em %s" % MANIFEST_PATH)

    # Verificacao final
    final = read(MANIFEST_PATH)
    problems = []
    if "android.permission.FOREGROUND_SERVICE\"" not in final:
        problems.append("FOREGROUND_SERVICE ainda ausente")
    if "android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK\"" not in final:
        problems.append("FOREGROUND_SERVICE_MEDIA_PLAYBACK ainda ausente")
    if problems:
        print("Encontrados problemas na verificacao final:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("Tudo certo: as duas permissoes estao presentes.")
    print("\nAgora rode: ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

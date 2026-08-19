#!/usr/bin/env python3
"""
Fix: tela de reprodução não abre mais ao clicar na capa de uma música.

Causa raiz: em PhotoPage.java, o método playVideo() monta um Intent
implícito com .setDataAndType(uri, "video/*") para abrir a MovieActivity.
Quando os intent-filters de vídeo foram removidos do AndroidManifest.xml
(deixando só mimetypes de áudio), o Android parou de encontrar qualquer
Activity que aceite "video/*" -> ActivityNotFoundException capturada
silenciosamente (só mostra um Toast de erro), então a tela nunca abre.

Correção: trocar "video/*" por "audio/*" no único ponto onde esse Intent
é montado, já que o app não é mais uma galeria de vídeo.

Uso (Termux, dentro de ~/Galeria3D):
    python3 passo_fix_intent_playvideo_audio.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path.home() / "Galeria3D"
TARGET = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/PhotoPage.java"

OLD = '.setDataAndType(uri, "video/*")'
NEW = '.setDataAndType(uri, "audio/*")'


def fail(msg):
    print(f"ERRO: {msg}")
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"Arquivo não encontrado: {TARGET}\n"
             f"Rode este script de dentro de ~/Galeria3D (ou ajuste PROJECT_ROOT).")

    original = TARGET.read_text(encoding="utf-8")

    count_new = original.count(NEW)
    count_old = original.count(OLD)

    if count_old == 0 and count_new >= 1:
        print("Já aplicado antes — nada a fazer (idempotente). "
              f"'{NEW}' já está presente em PhotoPage.java.")
        return

    if count_old == 0:
        fail(f"Não encontrei o padrão esperado ('{OLD}') em PhotoPage.java. "
             f"O arquivo pode já ter sido alterado de outra forma — "
             f"verifique manualmente o método playVideo() antes de prosseguir.")

    if count_old > 1:
        fail(f"Padrão '{OLD}' encontrado {count_old} vezes — esperado exatamente 1. "
             f"Corrija manualmente para evitar uma substituição ambígua.")

    # backup (arquivo é texto/Java, modo texto é seguro aqui)
    backup = TARGET.with_suffix(TARGET.suffix + ".bak")
    backup.write_text(original, encoding="utf-8")
    print(f"Backup salvo em: {backup}")

    patched = original.replace(OLD, NEW)
    if patched.count(OLD) != 0:
        fail("Substituição não removeu o padrão antigo — abortando sem escrever.")
    if patched.count(NEW) != count_new + 1:
        fail("Contagem pós-substituição inesperada — abortando sem escrever.")

    TARGET.write_text(patched, encoding="utf-8")

    # verificação final
    final = TARGET.read_text(encoding="utf-8")
    if OLD in final:
        fail("Verificação pós-escrita falhou: padrão antigo ainda presente.")
    if NEW not in final:
        fail("Verificação pós-escrita falhou: padrão novo não encontrado.")

    print("OK — PhotoPage.java corrigido:")
    print(f'  antes: {OLD}')
    print(f'  agora: {NEW}')
    print("\nPróximo passo: compilar.")
    print("  cd ~/Galeria3D && ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

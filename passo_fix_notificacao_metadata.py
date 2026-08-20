#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: notificacao perdeu o slider de avanco de tempo e os botoes de
Repetir Uma/Repetir Todas na visao expandida, apos a migracao da fila
de MoviePlayer para MusicPlaybackService.

Causa raiz encontrada em MusicPlaybackService.java:
  1. mMediaSession.setMetadata() NUNCA e chamado em lugar nenhum do
     arquivo. Sem MediaMetadata com METADATA_KEY_DURATION, o sistema
     Android nao tem como desenhar o slider de progresso na notificacao
     MediaStyle - ele nao sabe o "fim" da barra.
  2. updatePlaybackState() existe e monta as actions certas, mas nunca
     era chamado a partir de playTrackFromQueue()/playTrack() (so em
     onPrepared, pause, resume, seekTo, onCompletion com repeat ONE) -
     ou seja, ficava desatualizado nos momentos de troca de faixa via
     fila, o que faz o sistema achar o estado da sessao inconsistente
     e degradar a notificacao (esconder acoes extras na view expandida).

Fix: cria um metodo publishMediaMetadata() que seta titulo/artista/
duracao/capa via MediaMetadata.Builder e chama mMediaSession.setMetadata()
- chamado junto de updatePlaybackState() sempre que a faixa muda ou o
estado muda, garantindo que MediaSession sempre tenha metadata+state
consistentes antes de toda atualizacao de notificacao.

Idempotente: se o metodo publishMediaMetadata ja existir, o script nao
faz nada (idempotente == seguro rodar 2x).
"""
import re
import shutil
import sys
from pathlib import Path

REPO = Path.home() / "Galeria3D"
TARGET = REPO / "app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java"


def fail(msg):
    print(f"[ERRO] {msg}")
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"Arquivo nao encontrado: {TARGET}")

    src = TARGET.read_text(encoding="utf-8")

    if "publishMediaMetadata" in src:
        print("[OK] Fix ja aplicado antes (publishMediaMetadata ja existe). Nada a fazer.")
        return

    backup_dir = REPO / "passo_fix_notificacao_metadata_backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / TARGET.name
    shutil.copy2(TARGET, backup_path)
    print(f"[OK] Backup salvo em {backup_path}")

    original = src

    # 1) Import de MediaMetadata
    marker_import = "import android.media.session.MediaSession;"
    if marker_import not in src:
        fail("Import de MediaSession nao encontrado - arquivo mudou de estrutura, abortando sem tocar em nada.")
    src = src.replace(
        marker_import,
        "import android.media.MediaMetadata;\n" + marker_import,
        1,
    )

    # 2) Metodo publishMediaMetadata(), inserido logo antes de updatePlaybackState()
    marker_method = "    private void updatePlaybackState() {"
    if marker_method not in src:
        fail("Metodo updatePlaybackState() nao encontrado - abortando sem tocar em nada.")

    new_method = '''    // Fix (Player3D): publica titulo/artista/capa/duracao na MediaSession.
    // Sem isso, o sistema Android nao consegue desenhar o slider de
    // progresso na notificacao (MediaStyle) porque nao sabe a duracao
    // total da faixa - o slider simplesmente some. Chamado sempre junto
    // de updatePlaybackState(), nunca sozinho, para manter metadata e
    // estado sempre consistentes antes de toda atualizacao da notificacao.
    private void publishMediaMetadata() {
        if (mMediaSession == null) return;
        MediaMetadata.Builder builder = new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, mCurrentTitle)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, mCurrentArtist)
                .putLong(MediaMetadata.METADATA_KEY_DURATION, getDuration());
        if (mCurrentCover != null) {
            builder.putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART, mCurrentCover);
        }
        mMediaSession.setMetadata(builder.build());
    }

''' + marker_method

    src = src.replace(marker_method, new_method, 1)

    # 3) Faz updatePlaybackState() sempre publicar metadata junto (fonte
    #    unica de verdade - assim toda chamada existente a
    #    updatePlaybackState() ja ganha o fix automaticamente, sem
    #    precisar caçar cada callsite individualmente).
    marker_body_open = "    private void updatePlaybackState() {\n        long actions = PlaybackState.ACTION_PLAY_PAUSE"
    if marker_body_open not in src:
        fail("Corpo de updatePlaybackState() no formato esperado nao encontrado - abortando sem tocar em nada.")
    src = src.replace(
        marker_body_open,
        "    private void updatePlaybackState() {\n        publishMediaMetadata();\n        long actions = PlaybackState.ACTION_PLAY_PAUSE",
        1,
    )

    # 4) playTrackFromQueue() e playTrack() trocam de faixa mas nem sempre
    #    chamavam updatePlaybackState() logo em seguida (so onPrepared()
    #    chamava, de forma assincrona). Garante chamada imediata tambem
    #    ao iniciar o carregamento da nova faixa, para a notificacao ja
    #    nascer com titulo/artista corretos (duracao ainda 0 ate preparar,
    #    tudo bem - onPrepared() atualiza de novo com o valor real).
    marker_playtrack_end = "        startForeground(NOTIFICATION_ID, buildNotification());\n    }"
    if marker_playtrack_end not in src:
        fail("Fim de playTrack() no formato esperado nao encontrado - abortando sem tocar em nada.")
    src = src.replace(
        marker_playtrack_end,
        "        updatePlaybackState();\n        startForeground(NOTIFICATION_ID, buildNotification());\n    }",
        1,
    )

    if src == original:
        fail("Nenhuma substituicao efetivamente mudou o arquivo - abortando por seguranca.")

    # Sanidade: chaves balanceadas
    if src.count("{") != src.count("}"):
        fail("Chaves desbalanceadas apos o patch - abortando, arquivo NAO foi escrito.")

    TARGET.write_text(src, encoding="utf-8")
    print(f"[OK] Patch aplicado em {TARGET}")
    print("[OK] Chaves balanceadas, import adicionado, publishMediaMetadata() criado,")
    print("     chamado a partir de updatePlaybackState() e de playTrack().")
    print("\nRode de novo este script a qualquer momento: e idempotente e nao vai duplicar nada.")


if __name__ == "__main__":
    main()

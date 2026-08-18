#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passo 2 - Grade principal (Player3D / ex-Galeria3D)

O que este script faz:
1. Troca a raiz da tela inicial (GalleryActivity.startDefaultPage) de
   "todas as midias + Picasa" para /local/audio (INCLUDE_LOCAL_VIDEO_ONLY,
   que ja aponta pra /local/audio desde o Passo 1).
2. Cria o recurso app/src/main/res/drawable-nodpi/ic_audio_cover_placeholder.png
   (icone de nota musical, cinza monocromatico, fundo transparente).
3. Liga esse recurso como capa de fallback em dois lugares da grade 3D
   (AlbumSetSlidingWindow.java e AlbumSlidingWindow.java), onde hoje um
   album/faixa sem capa fica cinza pra sempre (bug conhecido do handoff).

Rode este script na RAIZ do projeto (~/Galeria3D no Termux):
    python3 passo2_grade_principal.py

Regras seguidas (workflow combinado):
- Falha cedo se os arquivos-alvo nao existirem, sem tocar em nada.
- Faz backup de cada arquivo Java antes de editar (sufixo .bak_passo2).
- So aplica cada substituicao se ela bater EXATAMENTE 1 vez no arquivo;
  caso contrario, para e mostra o erro sem tocar no arquivo.
- Termina com um grep de verificacao confirmando que nao sobrou nada do
  padrao antigo.
"""

import base64
import os
import sys

PLACEHOLDER_PNG_B64 = (
    "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"
)

GALLERY_ACTIVITY = "app/src/main/java/com/android/gallery3d/app/GalleryActivity.java"
ALBUM_SET_SLIDING_WINDOW = "app/src/main/java/com/android/gallery3d/ui/AlbumSetSlidingWindow.java"
ALBUM_SLIDING_WINDOW = "app/src/main/java/com/android/gallery3d/ui/AlbumSlidingWindow.java"
PLACEHOLDER_PATH = "app/src/main/res/drawable-nodpi/ic_audio_cover_placeholder.png"

REQUIRED_FILES = [GALLERY_ACTIVITY, ALBUM_SET_SLIDING_WINDOW, ALBUM_SLIDING_WINDOW]


def fail(msg):
    print("ERRO: " + msg)
    sys.exit(1)


def check_prereqs():
    for f in REQUIRED_FILES:
        if not os.path.isfile(f):
            fail(
                "arquivo esperado nao encontrado: %s\n"
                "Rode este script na raiz do projeto (~/Galeria3D) e confirme "
                "que o Passo 1 ja foi aplicado." % f
            )
    if os.path.isfile(PLACEHOLDER_PATH):
        print("Aviso: %s ja existe, nao vou sobrescrever (idempotente)." % PLACEHOLDER_PATH)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def backup(path):
    bak = path + ".bak_passo2"
    if not os.path.isfile(bak):
        write(bak, read(path))
        print("Backup criado: %s" % bak)
    else:
        print("Backup ja existia, mantido: %s" % bak)


def replace_exactly_once(path, old, new, label):
    content = read(path)
    count = content.count(old)
    if count == 0:
        fail(
            "%s: trecho esperado nao encontrado em %s.\n"
            "Isso costuma significar que o Passo 2 ja foi aplicado, ou que o "
            "arquivo mudou desde a especificacao. Nada foi alterado."
            % (label, path)
        )
    if count > 1:
        fail(
            "%s: trecho apareceu %d vezes em %s (esperado exatamente 1). "
            "Nada foi alterado, script parou por seguranca."
            % (label, count, path)
        )
    content = content.replace(old, new, 1)
    write(path, content)
    print("OK: %s (%s)" % (label, path))


def create_placeholder_png():
    if os.path.isfile(PLACEHOLDER_PATH):
        return
    os.makedirs(os.path.dirname(PLACEHOLDER_PATH), exist_ok=True)
    data = base64.b64decode(PLACEHOLDER_PNG_B64)
    with open(PLACEHOLDER_PATH, "wb") as fh:
        fh.write(data)
    print("Criado: %s (%d bytes)" % (PLACEHOLDER_PATH, len(data)))


def patch_gallery_activity():
    path = GALLERY_ACTIVITY
    backup(path)
    old = (
        "    public void startDefaultPage() {\n"
        "        PicasaSource.showSignInReminder(this);\n"
        "        Bundle data = new Bundle();\n"
        "        data.putString(AlbumSetPage.KEY_MEDIA_PATH,\n"
        "                getDataManager().getTopSetPath(DataManager.INCLUDE_ALL));\n"
        "        getStateManager().startState(AlbumSetPage.class, data);\n"
    )
    new = (
        "    public void startDefaultPage() {\n"
        "        PicasaSource.showSignInReminder(this);\n"
        "        Bundle data = new Bundle();\n"
        "        // Passo 2: a tela inicial agora abre direto em /local/audio\n"
        "        // (INCLUDE_LOCAL_VIDEO_ONLY ja aponta pra la desde o Passo 1),\n"
        "        // em vez do combo de todas as midias + Picasa.\n"
        "        data.putString(AlbumSetPage.KEY_MEDIA_PATH,\n"
        "                getDataManager().getTopSetPath(DataManager.INCLUDE_LOCAL_VIDEO_ONLY));\n"
        "        getStateManager().startState(AlbumSetPage.class, data);\n"
    )
    replace_exactly_once(path, old, new, "raiz da tela inicial -> /local/audio")


def patch_album_set_sliding_window():
    path = ALBUM_SET_SLIDING_WINDOW
    backup(path)

    # import do BitmapFactory
    replace_exactly_once(
        path,
        "import android.graphics.Bitmap;\nimport android.os.Message;\n",
        "import android.graphics.Bitmap;\nimport android.graphics.BitmapFactory;\nimport android.os.Message;\n",
        "import BitmapFactory",
    )

    # campo mActivity
    replace_exactly_once(
        path,
        "    private final AlbumSetDataLoader mSource;\n    private int mSize;\n",
        "    private final AlbumSetDataLoader mSource;\n    private final AbstractGalleryActivity mActivity;\n    private int mSize;\n",
        "campo mActivity",
    )

    # atribuicao no construtor
    replace_exactly_once(
        path,
        "        source.setModelListener(this);\n        mSource = source;\n",
        "        source.setModelListener(this);\n        mActivity = activity;\n        mSource = source;\n",
        "mActivity = activity no construtor",
    )

    # metodo auxiliar getPlaceholderCoverBitmap, logo apos setListener
    replace_exactly_once(
        path,
        "    public void setListener(Listener listener) {\n        mListener = listener;\n    }\n",
        (
            "    public void setListener(Listener listener) {\n"
            "        mListener = listener;\n"
            "    }\n\n"
            "    // Passo 2: capa generica de fallback para faixas/albuns sem capa\n"
            "    // (LocalAudio retorna null de proposito nesse caso - ver comentario\n"
            "    // em LocalAudio.LocalAudioRequest.onDecodeOriginal). Decodificada uma\n"
            "    // vez e reaproveitada: TiledTexture nunca recicla o Bitmap de origem\n"
            "    // que recebe, entao compartilhar essa mesma instancia entre varios\n"
            "    // slots e seguro.\n"
            "    private Bitmap mPlaceholderCoverBitmap;\n"
            "    private Bitmap getPlaceholderCoverBitmap() {\n"
            "        if (mPlaceholderCoverBitmap == null) {\n"
            "            mPlaceholderCoverBitmap = BitmapFactory.decodeResource(\n"
            "                    mActivity.getAndroidContext().getResources(),\n"
            "                    R.drawable.ic_audio_cover_placeholder);\n"
            "        }\n"
            "        return mPlaceholderCoverBitmap;\n"
            "    }\n"
        ),
        "metodo getPlaceholderCoverBitmap",
    )

    # fallback dentro de AlbumCoverLoader.updateEntry()
    replace_exactly_once(
        path,
        (
            "        @Override\n"
            "        public void updateEntry() {\n"
            "            Bitmap bitmap = getBitmap();\n"
            "            if (bitmap == null) return; // error or recycled\n"
            "\n"
            "            AlbumSetEntry entry = mData[mSlotIndex % mData.length];\n"
        ),
        (
            "        @Override\n"
            "        public void updateEntry() {\n"
            "            Bitmap bitmap = getBitmap();\n"
            "            if (bitmap == null) {\n"
            "                // Passo 2: sem capa real, usa a generica em vez de deixar\n"
            "                // o slot cinza pra sempre.\n"
            "                bitmap = getPlaceholderCoverBitmap();\n"
            "                if (bitmap == null) return; // recurso do placeholder ausente/corrompido\n"
            "            }\n"
            "\n"
            "            AlbumSetEntry entry = mData[mSlotIndex % mData.length];\n"
        ),
        "fallback em AlbumCoverLoader.updateEntry",
    )


def patch_album_sliding_window():
    path = ALBUM_SLIDING_WINDOW
    backup(path)

    # imports
    replace_exactly_once(
        path,
        "import android.graphics.Bitmap;\nimport android.os.Message;\n\nimport com.android.gallery3d.app.AbstractGalleryActivity;\n",
        "import android.graphics.Bitmap;\nimport android.graphics.BitmapFactory;\nimport android.os.Message;\n\nimport com.android.gallery3d.R;\nimport com.android.gallery3d.app.AbstractGalleryActivity;\n",
        "imports BitmapFactory + R",
    )

    # campo mActivity
    replace_exactly_once(
        path,
        "    private final TiledTexture.Uploader mTileUploader;\n\n    private int mSize;\n",
        "    private final TiledTexture.Uploader mTileUploader;\n    private final AbstractGalleryActivity mActivity;\n\n    private int mSize;\n",
        "campo mActivity",
    )

    # atribuicao no construtor
    replace_exactly_once(
        path,
        "        source.setDataListener(this);\n        mSource = source;\n",
        "        source.setDataListener(this);\n        mActivity = activity;\n        mSource = source;\n",
        "mActivity = activity no construtor",
    )

    # metodo auxiliar, logo antes de setListener
    replace_exactly_once(
        path,
        (
            "        mThreadPool = new JobLimiter(activity.getThreadPool(), JOB_LIMIT);\n"
            "        mTileUploader = new TiledTexture.Uploader(activity.getGLRoot());\n"
            "    }\n"
            "\n"
            "    public void setListener(Listener listener) {\n"
        ),
        (
            "        mThreadPool = new JobLimiter(activity.getThreadPool(), JOB_LIMIT);\n"
            "        mTileUploader = new TiledTexture.Uploader(activity.getGLRoot());\n"
            "    }\n"
            "\n"
            "    // Passo 2: capa generica de fallback para faixas sem capa. Decodificada\n"
            "    // uma vez e reaproveitada entre slots (TiledTexture nunca recicla o\n"
            "    // Bitmap de origem que recebe, entao isso e seguro).\n"
            "    private Bitmap mPlaceholderCoverBitmap;\n"
            "    private Bitmap getPlaceholderCoverBitmap() {\n"
            "        if (mPlaceholderCoverBitmap == null) {\n"
            "            mPlaceholderCoverBitmap = BitmapFactory.decodeResource(\n"
            "                    mActivity.getAndroidContext().getResources(),\n"
            "                    R.drawable.ic_audio_cover_placeholder);\n"
            "        }\n"
            "        return mPlaceholderCoverBitmap;\n"
            "    }\n"
            "\n"
            "    public void setListener(Listener listener) {\n"
        ),
        "metodo getPlaceholderCoverBitmap",
    )

    # fallback dentro de ThumbnailLoader.updateEntry()
    replace_exactly_once(
        path,
        (
            "        public void updateEntry() {\n"
            "            Bitmap bitmap = getBitmap();\n"
            "            if (bitmap == null) return; // error or recycled\n"
            "            AlbumEntry entry = mData[mSlotIndex % mData.length];\n"
        ),
        (
            "        public void updateEntry() {\n"
            "            Bitmap bitmap = getBitmap();\n"
            "            if (bitmap == null) {\n"
            "                // Passo 2: sem capa real, usa a generica em vez de deixar\n"
            "                // o slot cinza pra sempre.\n"
            "                bitmap = getPlaceholderCoverBitmap();\n"
            "                if (bitmap == null) return; // recurso do placeholder ausente/corrompido\n"
            "            }\n"
            "            AlbumEntry entry = mData[mSlotIndex % mData.length];\n"
        ),
        "fallback em ThumbnailLoader.updateEntry",
    )


def verify():
    print("\n--- Verificacao final ---")
    problems = []

    ga = read(GALLERY_ACTIVITY)
    if "DataManager.INCLUDE_ALL" in ga and "startDefaultPage" in ga:
        # aceitavel se INCLUDE_ALL sobrar em outro metodo (ex: startGetContent),
        # so nao pode sobrar dentro de startDefaultPage.
        start = ga.index("public void startDefaultPage")
        end = ga.index("\n    }", start)
        if "INCLUDE_ALL" in ga[start:end]:
            problems.append("GalleryActivity.startDefaultPage ainda usa INCLUDE_ALL")
    if "INCLUDE_LOCAL_VIDEO_ONLY" not in ga:
        problems.append("GalleryActivity nao ficou apontando pra INCLUDE_LOCAL_VIDEO_ONLY")

    assw = read(ALBUM_SET_SLIDING_WINDOW)
    if "if (bitmap == null) return; // error or recycled" in assw:
        problems.append("AlbumSetSlidingWindow ainda tem o retorno antigo sem fallback")
    if "getPlaceholderCoverBitmap" not in assw:
        problems.append("AlbumSetSlidingWindow sem getPlaceholderCoverBitmap")

    asw = read(ALBUM_SLIDING_WINDOW)
    if "if (bitmap == null) return; // error or recycled" in asw:
        problems.append("AlbumSlidingWindow ainda tem o retorno antigo sem fallback")
    if "getPlaceholderCoverBitmap" not in asw:
        problems.append("AlbumSlidingWindow sem getPlaceholderCoverBitmap")

    if not os.path.isfile(PLACEHOLDER_PATH):
        problems.append("PNG do placeholder nao foi criado")

    if problems:
        print("Encontrados problemas na verificacao final:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)

    print("Tudo certo: nenhum resto do padrao antigo encontrado.")


def main():
    check_prereqs()
    create_placeholder_png()
    patch_gallery_activity()
    patch_album_set_sliding_window()
    patch_album_sliding_window()
    verify()
    print("\nPasso 2 aplicado. Agora rode: ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

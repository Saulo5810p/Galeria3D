#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passo 8 - Transforma o widget de home screen original (que mostrava fotos
aleatorias do celular) em widget de musica: as capas exibidas passam a ser
as das faixas do app, e deslizar/tocar num card faz aquela faixa comecar a
tocar de verdade (sem precisar abrir o app).

Rodar dentro de ~/Galeria3D (Termux):
    python3 fix_step8_music_widget.py

Idempotente: pode rodar 2x sem quebrar. Faz backup .bak (uma vez so, do
original) de cada arquivo antes de mexer.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
JAVA = os.path.join(ROOT, "app", "src", "main", "java", "com", "android", "gallery3d")


def backup(path):
    # Atencao: este repo tem VARIOS .bak antigos ja commitados no GitHub
    # (sobras de scripts de outras sessoes). Um .bak.bak_stepN novo, com
    # sufixo proprio deste script, evita reusar/confundir com um .bak
    # desatualizado que ja existia antes de rodar.
    bak = path + ".bak_step8"
    if not os.path.exists(bak):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(bak, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  backup criado: {bak}")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def ensure_once(content, marker, insertion, after=None, before=None):
    """Insere `insertion` uma unica vez (se `marker` ainda nao estiver no
    arquivo), logo depois de `after` ou logo antes de `before`."""
    if marker in content:
        return content, False
    if after is not None:
        idx = content.index(after) + len(after)
        return content[:idx] + insertion + content[idx:], True
    if before is not None:
        idx = content.index(before)
        return content[:idx] + insertion + content[idx:], True
    raise ValueError("ensure_once precisa de after= ou before=")


def step_music_playback_service():
    path = os.path.join(JAVA, "app", "MusicPlaybackService.java")
    print(f"[1/4] {os.path.relpath(path, ROOT)}")
    content = read(path)
    backup(path)
    changed = False

    # --- 1. Nova ACTION_PLAY_URI + extras, ao lado das outras ACTIONs ---
    marker = 'public static final String ACTION_PLAY_URI ='
    if marker not in content:
        anchor = '    public static final String ACTION_STOP =\n            "com.android.gallery3d.app.action.STOP";\n'
        insertion = (
            '    // Fix (Player3D, Passo 8 - widget de home screen): permite comecar a\n'
            '    // tocar uma faixa diretamente por Intent (PendingIntent do widget),\n'
            '    // sem precisar de bindService() nem abrir a Activity.\n'
            '    public static final String ACTION_PLAY_URI =\n'
            '            "com.android.gallery3d.app.action.PLAY_URI";\n'
            '    public static final String EXTRA_TRACK_URI = "extra_track_uri";\n'
            '    public static final String EXTRA_TRACK_TITLE = "extra_track_title";\n'
            '    public static final String EXTRA_TRACK_ARTIST = "extra_track_artist";\n'
            '    public static final String EXTRA_TRACK_ALBUM_ID = "extra_track_album_id";\n'
            '    public static final String EXTRA_TRACK_BUCKET_ID = "extra_track_bucket_id";\n'
        )
        assert anchor in content, "ACTION_STOP nao encontrado (MusicPlaybackService.java)"
        content = content.replace(anchor, anchor + insertion, 1)
        changed = True

    # --- 2. handleAction(): novo case ACTION_PLAY_URI ---
    marker = "case ACTION_PLAY_URI:"
    if marker not in content:
        anchor = "            case ACTION_STOP:\n                stopPlaybackAndService();\n                break;\n"
        insertion = (
            "            case ACTION_PLAY_URI:\n"
            "                break; // tratado em onStartCommand() (precisa do Intent completo, nao so da action)\n"
        )
        assert anchor in content, "case ACTION_STOP nao encontrado em handleAction()"
        content = content.replace(anchor, anchor + insertion, 1)
        changed = True

    # --- 3. onStartCommand(): trata ACTION_PLAY_URI com os extras, antes do handleAction generico ---
    marker = "handlePlayUriIntent(intent)"
    if marker not in content:
        old = (
            "    public int onStartCommand(Intent intent, int flags, int startId) {\n"
            "        if (intent != null && intent.getAction() != null) {\n"
            "            handleAction(intent.getAction());\n"
            "        }\n"
            "        return START_NOT_STICKY;\n"
            "    }\n"
        )
        new = (
            "    public int onStartCommand(Intent intent, int flags, int startId) {\n"
            "        if (intent != null && intent.getAction() != null) {\n"
            "            if (ACTION_PLAY_URI.equals(intent.getAction())) {\n"
            "                handlePlayUriIntent(intent);\n"
            "            } else {\n"
            "                handleAction(intent.getAction());\n"
            "            }\n"
            "        }\n"
            "        return START_NOT_STICKY;\n"
            "    }\n"
            "\n"
            "    // Fix (Player3D, Passo 8 - widget de home screen): recebido via\n"
            "    // PendingIntent.getService() disparado ao deslizar/tocar um card no\n"
            "    // widget. Comeca a tocar a faixa direto (sem bindService/Activity) e\n"
            "    // carrega a fila normalmente, igual a qualquer outra faixa tocada\n"
            "    // dentro do app - depois disso, next/previous/notificacao funcionam\n"
            "    // normalmente.\n"
            "    private void handlePlayUriIntent(Intent intent) {\n"
            "        Uri uri = intent.getParcelableExtra(EXTRA_TRACK_URI);\n"
            "        if (uri == null) return;\n"
            "        String title = intent.getStringExtra(EXTRA_TRACK_TITLE);\n"
            "        String artist = intent.getStringExtra(EXTRA_TRACK_ARTIST);\n"
            "        long albumId = intent.getLongExtra(EXTRA_TRACK_ALBUM_ID, -1);\n"
            "        long bucketId = intent.getLongExtra(EXTRA_TRACK_BUCKET_ID, -1);\n"
            "        Bitmap cover = decodeEmbeddedCover(getApplicationContext(), uri);\n"
            "        if (cover == null && albumId >= 0) {\n"
            "            cover = decodeAlbumArtFallback(getApplicationContext().getContentResolver(), albumId);\n"
            "        }\n"
            "        playTrack(uri, title, artist, cover);\n"
            "        loadQueueForTrack(albumId, bucketId, uri);\n"
            "    }\n"
        )
        assert old in content, "onStartCommand() original nao encontrado (formato inesperado)"
        content = content.replace(old, new, 1)
        changed = True

    if changed:
        write(path, content)
        print("  atualizado.")
    else:
        print("  ja aplicado, nada a fazer.")


def step_local_audio_widget_source():
    path = os.path.join(JAVA, "gadget", "LocalAudioWidgetSource.java")
    print(f"[2/4] {os.path.relpath(path, ROOT)}")
    if os.path.exists(path):
        print("  ja existe, nada a fazer.")
        return

    content = '''/*
 * Fix (Player3D, Passo 8 - widget de home screen): substitui
 * LocalPhotoSource (que listava fotos aleatorias do MediaStore de Imagens,
 * sem nenhuma relacao com o app) como fonte de dados do widget. Agora o
 * widget lista as MESMAS faixas de audio que aparecem no grid principal do
 * app, usando a capa de cada uma (embutida no arquivo, com fallback para a
 * capa de album do MediaStore) como imagem do card.
 */

package com.android.gallery3d.gadget;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.Context;
import android.database.ContentObserver;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.provider.MediaStore.Audio.Albums;
import android.provider.MediaStore.Audio.AudioColumns;
import android.provider.MediaStore.Audio.Media;

import com.android.gallery3d.data.ContentListener;

import java.util.ArrayList;

public class LocalAudioWidgetSource implements WidgetSource {

    private static final String TAG = "LocalAudioWidgetSource";
    private static final int MAX_TRACK_COUNT = 128;
    private static final int COVER_TARGET_SIZE = 512;

    private static final Uri CONTENT_URI = Media.EXTERNAL_CONTENT_URI;
    private static final String[] PROJECTION = {
            AudioColumns._ID, AudioColumns.TITLE, AudioColumns.ARTIST,
            AudioColumns.ALBUM_ID, AudioColumns.BUCKET_ID,
    };
    private static final String ORDER = AudioColumns.TITLE + " ASC";

    private final Context mContext;
    private final ArrayList<Entry> mTracks = new ArrayList<Entry>();
    private ContentListener mContentListener;
    private final ContentObserver mContentObserver;
    private boolean mContentDirty = true;

    private static final class Entry {
        long id;
        String title;
        String artist;
        long albumId;
        long bucketId;
    }

    public LocalAudioWidgetSource(Context context) {
        mContext = context;
        mContentObserver = new ContentObserver(new Handler()) {
            @Override
            public void onChange(boolean selfChange) {
                mContentDirty = true;
                if (mContentListener != null) mContentListener.onContentDirty();
            }
        };
        mContext.getContentResolver()
                .registerContentObserver(CONTENT_URI, true, mContentObserver);
    }

    @Override
    public void close() {
        mContext.getContentResolver().unregisterContentObserver(mContentObserver);
    }

    @Override
    public Uri getContentUri(int index) {
        if (index < 0 || index >= mTracks.size()) return null;
        return ContentUris.withAppendedId(CONTENT_URI, mTracks.get(index).id);
    }

    @Override
    public Bitmap getImage(int index) {
        if (index < 0 || index >= mTracks.size()) return null;
        Entry entry = mTracks.get(index);
        Uri uri = ContentUris.withAppendedId(CONTENT_URI, entry.id);
        Bitmap cover = decodeEmbeddedCover(mContext, uri);
        if (cover == null && entry.albumId >= 0) {
            cover = decodeAlbumArtFallback(mContext.getContentResolver(), entry.albumId);
        }
        return cover;
    }

    /** Usado por PhotoAppWidgetProvider pra montar o PendingIntent de tocar a faixa. */
    public String getTitle(int index) {
        if (index < 0 || index >= mTracks.size()) return null;
        return mTracks.get(index).title;
    }

    public String getArtist(int index) {
        if (index < 0 || index >= mTracks.size()) return null;
        return mTracks.get(index).artist;
    }

    public long getAlbumId(int index) {
        if (index < 0 || index >= mTracks.size()) return -1;
        return mTracks.get(index).albumId;
    }

    public long getBucketId(int index) {
        if (index < 0 || index >= mTracks.size()) return -1;
        return mTracks.get(index).bucketId;
    }

    @Override
    public void reload() {
        if (!mContentDirty) return;
        mContentDirty = false;

        mTracks.clear();
        ContentResolver resolver = mContext.getContentResolver();
        Cursor cursor = resolver.query(CONTENT_URI, PROJECTION, null, null, ORDER);
        if (cursor == null) return;
        try {
            while (cursor.moveToNext() && mTracks.size() < MAX_TRACK_COUNT) {
                Entry entry = new Entry();
                entry.id = cursor.getLong(0);
                entry.title = cursor.getString(1);
                entry.artist = cursor.getString(2);
                entry.albumId = cursor.getLong(3);
                entry.bucketId = cursor.getLong(4);
                mTracks.add(entry);
            }
        } finally {
            cursor.close();
        }
    }

    @Override
    public int size() {
        reload();
        return mTracks.size();
    }

    @Override
    public void setContentListener(ContentListener listener) {
        mContentListener = listener;
    }

    // Mesma tecnica usada em MusicPlaybackService (Passo 4/9): capa
    // embutida no arquivo, com fallback pra capa de album do MediaStore.
    private static Bitmap decodeEmbeddedCover(Context context, Uri uri) {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        try {
            retriever.setDataSource(context, uri);
            byte[] embedded = retriever.getEmbeddedPicture();
            if (embedded == null) return null;
            return android.graphics.BitmapFactory.decodeByteArray(embedded, 0, embedded.length);
        } catch (Throwable t) {
            return null;
        } finally {
            try {
                retriever.release();
            } catch (Throwable ignored) {
            }
        }
    }

    private static Bitmap decodeAlbumArtFallback(ContentResolver resolver, long albumId) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                Uri albumArtUri = Albums.EXTERNAL_CONTENT_URI.buildUpon()
                        .appendPath(String.valueOf(albumId)).build();
                return resolver.loadThumbnail(albumArtUri,
                        new android.util.Size(COVER_TARGET_SIZE, COVER_TARGET_SIZE), null);
            }
            return null;
        } catch (Throwable t) {
            return null;
        }
    }
}
'''
    write(path, content)
    print("  criado.")


def step_widget_service():
    path = os.path.join(JAVA, "gadget", "WidgetService.java")
    print(f"[3/4] {os.path.relpath(path, ROOT)}")
    content = read(path)
    backup(path)
    changed = False

    if "new LocalAudioWidgetSource(" not in content:
        old = (
            "            if (mType == WidgetDatabaseHelper.TYPE_ALBUM) {\n"
            "                mSource = new MediaSetSource(mApp.getDataManager(), mAlbumPath);\n"
            "            } else {\n"
            "                mSource = new LocalPhotoSource(mApp.getAndroidContext());\n"
            "            }\n"
        )
        new = (
            "            if (mType == WidgetDatabaseHelper.TYPE_ALBUM) {\n"
            "                mSource = new MediaSetSource(mApp.getDataManager(), mAlbumPath);\n"
            "            } else {\n"
            "                // Fix (Player3D, Passo 8): widget de musica - lista as faixas\n"
            "                // do app (mesma fonte do grid principal), nao mais fotos\n"
            "                // aleatorias do celular inteiro.\n"
            "                mSource = new LocalAudioWidgetSource(mApp.getAndroidContext());\n"
            "            }\n"
        )
        assert old in content, "bloco de escolha de fonte nao encontrado em WidgetService.java"
        content = content.replace(old, new, 1)
        changed = True

    if changed:
        write(path, content)
        print("  atualizado.")
    else:
        print("  ja aplicado, nada a fazer.")


def step_widget_provider():
    path = os.path.join(JAVA, "gadget", "PhotoAppWidgetProvider.java")
    print(f"[4/4] {os.path.relpath(path, ROOT)}")
    content = read(path)
    backup(path)
    changed = False

    # imports novos necessarios
    if "import com.android.gallery3d.app.MusicPlaybackService;" not in content:
        anchor = "import com.android.gallery3d.onetimeinitializer.GalleryWidgetMigrator;\n"
        insertion = "import com.android.gallery3d.app.MusicPlaybackService;\n"
        assert anchor in content, "bloco de imports nao encontrado (PhotoAppWidgetProvider.java)"
        content = content.replace(anchor, anchor + insertion, 1)
        changed = True

    # buildStackWidget: troca o clique generico (WidgetClickHandler) por um
    # PendingIntentTemplate que manda ACTION_PLAY_URI direto pro Service.
    old = (
        '        Intent clickIntent = new Intent(context, WidgetClickHandler.class);\n'
        '        PendingIntent pendingIntent = PendingIntent.getActivity(\n'
        '                context, 0, clickIntent, PendingIntent.FLAG_UPDATE_CURRENT);\n'
        '        views.setPendingIntentTemplate(R.id.appwidget_stack_view, pendingIntent);\n'
    )
    new = (
        '        // Fix (Player3D, Passo 8): deslizar/tocar um card agora manda a\n'
        '        // faixa correspondente comecar a tocar de verdade (ACTION_PLAY_URI\n'
        '        // no MusicPlaybackService), em vez de abrir uma Activity de foto.\n'
        '        // Os extras variam por item, entao cada item preenche o restante do\n'
        '        // Intent via setOnClickFillInIntent() (ver WidgetService/getViewAt).\n'
        '        Intent clickIntent = new Intent(context, MusicPlaybackService.class);\n'
        '        clickIntent.setAction(MusicPlaybackService.ACTION_PLAY_URI);\n'
        '        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;\n'
        '        if (ApiHelper.HAS_ANDROID_M) {\n'
        '            pendingFlags |= PendingIntent.FLAG_MUTABLE;\n'
        '        }\n'
        '        PendingIntent pendingIntent = PendingIntent.getService(\n'
        '                context, 0, clickIntent, pendingFlags);\n'
        '        views.setPendingIntentTemplate(R.id.appwidget_stack_view, pendingIntent);\n'
    )
    if new not in content:
        assert old in content, "bloco de PendingIntentTemplate nao encontrado (formato inesperado)"
        content = content.replace(old, new, 1)
        changed = True

    if changed:
        write(path, content)
        print("  atualizado.")
    else:
        print("  ja aplicado, nada a fazer.")


def step_widget_service_getviewat():
    """Ajusta getViewAt() em WidgetService.java pra preencher o
    fill-in-intent com os extras da faixa (uri/titulo/artista/album/bucket)
    quando a fonte for de audio."""
    path = os.path.join(JAVA, "gadget", "WidgetService.java")
    print("[3b/4] WidgetService.java (getViewAt - extras da faixa)")
    content = read(path)
    changed = False

    old = (
        '        @Override\n'
        '        public RemoteViews getViewAt(int position) {\n'
        '            Bitmap bitmap = mSource.getImage(position);\n'
        '            if (bitmap == null) return getLoadingView();\n'
        '            RemoteViews views = new RemoteViews(\n'
        '                    mApp.getAndroidContext().getPackageName(),\n'
        '                    R.layout.appwidget_photo_item);\n'
        '            views.setImageViewBitmap(R.id.appwidget_photo_item, bitmap);\n'
        '            views.setOnClickFillInIntent(R.id.appwidget_photo_item, new Intent()\n'
        '                    .setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)\n'
        '                    .setData(mSource.getContentUri(position)));\n'
        '            return views;\n'
        '        }\n'
    )
    new = (
        '        @Override\n'
        '        public RemoteViews getViewAt(int position) {\n'
        '            Bitmap bitmap = mSource.getImage(position);\n'
        '            if (bitmap == null) return getLoadingView();\n'
        '            RemoteViews views = new RemoteViews(\n'
        '                    mApp.getAndroidContext().getPackageName(),\n'
        '                    R.layout.appwidget_photo_item);\n'
        '            views.setImageViewBitmap(R.id.appwidget_photo_item, bitmap);\n'
        '            // Fix (Player3D, Passo 8): fonte de audio manda os extras que o\n'
        '            // MusicPlaybackService precisa pra tocar a faixa direto\n'
        '            // (ACTION_PLAY_URI). Fonte de foto/album antiga mantem o\n'
        '            // comportamento original (so a Uri, sem extras de audio).\n'
        '            Intent fillInIntent = new Intent()\n'
        '                    .setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)\n'
        '                    .setData(mSource.getContentUri(position));\n'
        '            if (mSource instanceof LocalAudioWidgetSource) {\n'
        '                LocalAudioWidgetSource audioSource = (LocalAudioWidgetSource) mSource;\n'
        '                fillInIntent.putExtra(com.android.gallery3d.app.MusicPlaybackService.EXTRA_TRACK_URI,\n'
        '                        mSource.getContentUri(position));\n'
        '                fillInIntent.putExtra(com.android.gallery3d.app.MusicPlaybackService.EXTRA_TRACK_TITLE,\n'
        '                        audioSource.getTitle(position));\n'
        '                fillInIntent.putExtra(com.android.gallery3d.app.MusicPlaybackService.EXTRA_TRACK_ARTIST,\n'
        '                        audioSource.getArtist(position));\n'
        '                fillInIntent.putExtra(com.android.gallery3d.app.MusicPlaybackService.EXTRA_TRACK_ALBUM_ID,\n'
        '                        audioSource.getAlbumId(position));\n'
        '                fillInIntent.putExtra(com.android.gallery3d.app.MusicPlaybackService.EXTRA_TRACK_BUCKET_ID,\n'
        '                        audioSource.getBucketId(position));\n'
        '            }\n'
        '            views.setOnClickFillInIntent(R.id.appwidget_photo_item, fillInIntent);\n'
        '            return views;\n'
        '        }\n'
    )
    if new not in content:
        assert old in content, "getViewAt() original nao encontrado (formato inesperado)"
        content = content.replace(old, new, 1)
        changed = True

    if changed:
        write(path, content)
        print("  atualizado.")
    else:
        print("  ja aplicado, nada a fazer.")


def main():
    print("=== Passo 8: widget de home screen -> widget de musica ===\n")
    step_music_playback_service()
    step_local_audio_widget_source()
    step_widget_service()
    step_widget_service_getviewat()
    step_widget_provider()
    print("\nConcluido. Recompile e reinstale o app; pode ser necessario remover")
    print("e recolocar o widget na tela inicial para o Android recarregar o layout.")


if __name__ == "__main__":
    main()

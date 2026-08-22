/*
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

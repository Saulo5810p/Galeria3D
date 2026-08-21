/*
 * Copyright (C) 2010 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.gallery3d.data;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.BitmapRegionDecoder;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.Build;
import android.provider.MediaStore.Audio;
import android.provider.MediaStore.Audio.AudioColumns;
import android.provider.MediaStore.Audio.Albums;

import com.android.gallery3d.app.GalleryApp;
import com.android.gallery3d.util.GalleryUtils;
import com.android.gallery3d.util.ThreadPool.Job;
import com.android.gallery3d.util.ThreadPool.JobContext;
import com.android.gallery3d.util.UpdateHelper;

// LocalAudio represents an audio track in the local storage.
public class LocalAudio extends LocalMediaItem {
    private static final String TAG = "LocalAudio";
    static final Path ITEM_PATH = Path.fromString("/local/audio/item");

    // Must preserve order between these indices and the order of the terms in
    // the following PROJECTION array.
    private static final int INDEX_ID = 0;
    private static final int INDEX_CAPTION = 1;
    private static final int INDEX_MIME_TYPE = 2;
    private static final int INDEX_DATE_ADDED = 3;
    private static final int INDEX_DATE_MODIFIED = 4;
    private static final int INDEX_DATA = 5;
    private static final int INDEX_DURATION = 6;
    private static final int INDEX_BUCKET_ID = 7;
    private static final int INDEX_SIZE = 8;
    private static final int INDEX_ARTIST = 9;
    private static final int INDEX_ALBUM = 10;
    private static final int INDEX_ALBUM_ID = 11;
    private static final int INDEX_TRACK = 12;

    // Audio has no LATITUDE/LONGITUDE/RESOLUTION columns (video/image-only), and
    // no DATE_TAKEN column (see loadFromCursor: we derive it from DATE_ADDED).
    static final String[] PROJECTION = new String[] {
            AudioColumns._ID,
            AudioColumns.TITLE,
            AudioColumns.MIME_TYPE,
            AudioColumns.DATE_ADDED,
            AudioColumns.DATE_MODIFIED,
            AudioColumns.DATA,
            AudioColumns.DURATION,
            AudioColumns.BUCKET_ID,
            AudioColumns.SIZE,
            AudioColumns.ARTIST,
            AudioColumns.ALBUM,
            AudioColumns.ALBUM_ID,
            AudioColumns.TRACK,
    };

    private final GalleryApp mApplication;

    public int durationInSec;
    public String artist;
    public String album;
    public long albumId;
    public int track;

    public LocalAudio(Path path, GalleryApp application, Cursor cursor) {
        super(path, nextVersionNumber());
        mApplication = application;
        loadFromCursor(cursor);
    }

    public LocalAudio(Path path, GalleryApp context, int id) {
        super(path, nextVersionNumber());
        mApplication = context;
        ContentResolver resolver = mApplication.getContentResolver();
        Uri uri = Audio.Media.EXTERNAL_CONTENT_URI;
        Cursor cursor = LocalAlbum.getItemCursor(resolver, uri, PROJECTION, id);
        if (cursor == null) {
            throw new RuntimeException("cannot get cursor for: " + path);
        }
        try {
            if (cursor.moveToNext()) {
                loadFromCursor(cursor);
            } else {
                throw new RuntimeException("cannot find data for: " + path);
            }
        } finally {
            cursor.close();
        }
    }

    private void loadFromCursor(Cursor cursor) {
        id = cursor.getInt(INDEX_ID);
        caption = cursor.getString(INDEX_CAPTION);
        mimeType = cursor.getString(INDEX_MIME_TYPE);
        dateAddedInSec = cursor.getLong(INDEX_DATE_ADDED);
        // Audio has no "date taken" concept; reuse date added (converted to ms)
        // so the rest of the app, which expects dateTakenInMs, keeps working.
        dateTakenInMs = dateAddedInSec * 1000L;
        dateModifiedInSec = cursor.getLong(INDEX_DATE_MODIFIED);
        filePath = cursor.getString(INDEX_DATA);
        durationInSec = cursor.getInt(INDEX_DURATION) / 1000;
        bucketId = cursor.getInt(INDEX_BUCKET_ID);
        fileSize = cursor.getLong(INDEX_SIZE);
        artist = cursor.getString(INDEX_ARTIST);
        album = cursor.getString(INDEX_ALBUM);
        albumId = cursor.getLong(INDEX_ALBUM_ID);
        track = cursor.getInt(INDEX_TRACK);
    }

    @Override
    protected boolean updateFromCursor(Cursor cursor) {
        UpdateHelper uh = new UpdateHelper();
        id = uh.update(id, cursor.getInt(INDEX_ID));
        caption = uh.update(caption, cursor.getString(INDEX_CAPTION));
        mimeType = uh.update(mimeType, cursor.getString(INDEX_MIME_TYPE));
        dateAddedInSec = uh.update(
                dateAddedInSec, cursor.getLong(INDEX_DATE_ADDED));
        dateTakenInMs = uh.update(dateTakenInMs, dateAddedInSec * 1000L);
        dateModifiedInSec = uh.update(
                dateModifiedInSec, cursor.getLong(INDEX_DATE_MODIFIED));
        filePath = uh.update(filePath, cursor.getString(INDEX_DATA));
        durationInSec = uh.update(
                durationInSec, cursor.getInt(INDEX_DURATION) / 1000);
        bucketId = uh.update(bucketId, cursor.getInt(INDEX_BUCKET_ID));
        fileSize = uh.update(fileSize, cursor.getLong(INDEX_SIZE));
        artist = uh.update(artist, cursor.getString(INDEX_ARTIST));
        album = uh.update(album, cursor.getString(INDEX_ALBUM));
        albumId = uh.update(albumId, cursor.getLong(INDEX_ALBUM_ID));
        track = uh.update(track, cursor.getInt(INDEX_TRACK));
        return uh.isUpdated();
    }

    @Override
    public Job<Bitmap> requestImage(int type) {
        return new LocalAudioRequest(mApplication, getPath(), dateModifiedInSec,
                type, filePath, albumId);
    }

    // Cover art request for an audio track. Unlike video, the cache key is
    // based on the ALBUM_ID (not the individual track's path/id): every track
    // in the same album shares one decoded cover instead of the app trying to
    // decode/cache it once per file. This is both a performance fix and the
    // fix for the pre-existing bug where albums with 150+ tracks show empty
    // gray boxes (the old per-item cache was thrashing/timing out).
    public static class LocalAudioRequest extends ImageCacheRequest {
        private final String mLocalFilePath;
        private final long mAlbumId;

        LocalAudioRequest(GalleryApp application, Path path, long timeModified,
                int type, String localFilePath, long albumId) {
            super(application, albumArtCacheKey(albumId), timeModified, type,
                    MediaItem.getTargetSize(type));
            mLocalFilePath = localFilePath;
            mAlbumId = albumId;
        }

        private static Path albumArtCacheKey(long albumId) {
            return Path.fromString("/local/audio/albumart/" + albumId);
        }

        @Override
        public Bitmap onDecodeOriginal(JobContext jc, int type) {
            Bitmap bitmap = decodeEmbeddedPicture(jc);
            if (bitmap == null && !jc.isCancelled()) {
                bitmap = decodeAlbumArtFallback(jc, type);
            }
            // Falling through to null here (instead of throwing) is intentional:
            // a swallowed decode failure with no callback is exactly what leaves
            // an item stuck on the gray placeholder forever. The caller/adapter
            // (Passo 2) is responsible for showing the generic placeholder when
            // this returns null.
            if (jc.isCancelled()) return null;
            return bitmap;
        }

        private Bitmap decodeEmbeddedPicture(JobContext jc) {
            MediaMetadataRetriever retriever = new MediaMetadataRetriever();
            try {
                retriever.setDataSource(mLocalFilePath);
                byte[] embedded = retriever.getEmbeddedPicture();
                if (embedded == null || jc.isCancelled()) return null;
                return BitmapFactory.decodeByteArray(embedded, 0, embedded.length);
            } catch (OutOfMemoryError e) {
                Log.w(TAG, "OOM decoding embedded cover for " + mLocalFilePath);
                return null;
            } catch (Throwable t) {
                // MediaMetadataRetriever throws RuntimeException for unreadable/
                // corrupt files. Treat as "no embedded cover", not a crash.
                Log.w(TAG, "no embedded cover for " + mLocalFilePath);
                return null;
            } finally {
                try {
                    retriever.release();
                } catch (Throwable ignored) {
                }
            }
        }

        private Bitmap decodeAlbumArtFallback(JobContext jc, int type) {
            if (mAlbumId <= 0) return null;
            ContentResolver resolver = mApplication.getContentResolver();
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    Uri albumArtUri = ContentUris.withAppendedId(
                            Albums.EXTERNAL_CONTENT_URI, mAlbumId);
                    int size = MediaItem.getTargetSize(type);
                    return resolver.loadThumbnail(
                            albumArtUri, new android.util.Size(size, size), null);
                } else {
                    return decodeAlbumArtLegacy(resolver);
                }
            } catch (OutOfMemoryError e) {
                Log.w(TAG, "OOM decoding album art fallback for album " + mAlbumId);
                return null;
            } catch (Throwable t) {
                Log.w(TAG, "no album art for album " + mAlbumId);
                return null;
            }
        }

        // Pre-Android 10: MediaStore.Audio.Albums.ALBUM_ART is a file path
        // column pointing directly at the cached album art file on disk.
        private Bitmap decodeAlbumArtLegacy(ContentResolver resolver) {
            String[] projection = {Albums.ALBUM_ART};
            Cursor cursor = resolver.query(Albums.EXTERNAL_CONTENT_URI, projection,
                    Albums._ID + "=?", new String[]{String.valueOf(mAlbumId)}, null);
            if (cursor == null) return null;
            try {
                if (cursor.moveToFirst()) {
                    String path = cursor.getString(0);
                    if (path != null) {
                        return BitmapFactory.decodeFile(path);
                    }
                }
            } finally {
                cursor.close();
            }
            return null;
        }
    }

    @Override
    public Job<BitmapRegionDecoder> requestLargeImage() {
        throw new UnsupportedOperationException("Cannot regquest a large image"
                + " to a local audio track!");
    }

    @Override
    public int getSupportedOperations() {
        // Passo 4.3 (Player3D): SUPPORT_EDIT habilita o botao do editor de
        // fotos na tela de reproducao, apontando pra capa da faixa (ver
        // getCoverUriForEdit() abaixo), nao pro arquivo de audio em si.
        // Passo 7 (Player3D): SUPPORT_MOVE habilita "Mover para album" no
        // menu de selecao multipla.
        return SUPPORT_DELETE | SUPPORT_SHARE | SUPPORT_PLAY | SUPPORT_INFO | SUPPORT_TRIM | SUPPORT_MUTE | SUPPORT_EDIT | SUPPORT_MOVE;
    }

    // Passo 4.3 (Player3D): resolve a capa atual da faixa (mesma logica de
    // LocalAudioRequest.onDecodeOriginal, capa embutida > capa do album >
    // null) de forma SINCRONA, persiste num arquivo temporario em cache e
    // devolve uma Uri de conteudo (via FileProvider ja configurado no
    // projeto, mesmo authority ".provider" usado em TrimVideo/MuteVideo)
    // para o FilterShowActivity poder abrir como imagem editavel. Retorna
    // null se nao houver capa nenhuma (nem embutida nem de album) - quem
    // chama deve tratar null (ex.: nao abrir o editor / avisar o usuario).
    public android.net.Uri getCoverUriForEdit(android.content.Context context) {
        Bitmap cover = decodeCoverForEditSync();
        if (cover == null) return null;
        java.io.File cacheDir = new java.io.File(context.getCacheDir(), "audio_covers");
        if (!cacheDir.exists() && !cacheDir.mkdirs()) {
            Log.w(TAG, "nao foi possivel criar cache dir para capa: " + cacheDir);
            return null;
        }
        java.io.File coverFile = new java.io.File(cacheDir, "cover_" + id + ".jpg");
        try (java.io.FileOutputStream out = new java.io.FileOutputStream(coverFile)) {
            cover.compress(Bitmap.CompressFormat.JPEG, 92, out);
        } catch (java.io.IOException e) {
            Log.w(TAG, "falha ao salvar capa temporaria para edicao: " + coverFile, e);
            return null;
        }
        return androidx.core.content.FileProvider.getUriForFile(
                context, context.getPackageName() + ".provider", coverFile);
    }

    // Mesma cadeia de fallback de LocalAudioRequest (capa embutida no
    // arquivo, senao capa do album via MediaStore), mas chamada direto na
    // thread de chamada (o clique no botao de editar), sem passar pelo
    // ImageCacheRequest/JobContext assincrono do carregamento de grade.
    private Bitmap decodeCoverForEditSync() {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        try {
            retriever.setDataSource(filePath);
            byte[] embedded = retriever.getEmbeddedPicture();
            if (embedded != null) {
                Bitmap decoded = BitmapFactory.decodeByteArray(embedded, 0, embedded.length);
                if (decoded != null) return decoded;
            }
        } catch (OutOfMemoryError e) {
            Log.w(TAG, "OOM decoding embedded cover for edit: " + filePath);
        } catch (Throwable t) {
            Log.w(TAG, "sem capa embutida para edicao: " + filePath);
        } finally {
            try {
                retriever.release();
            } catch (Throwable ignored) {
            }
        }
        if (albumId <= 0) return null;
        ContentResolver resolver = mApplication.getContentResolver();
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                Uri albumArtUri = ContentUris.withAppendedId(
                        Albums.EXTERNAL_CONTENT_URI, albumId);
                int size = MediaItem.getTargetSize(MediaItem.TYPE_THUMBNAIL);
                return resolver.loadThumbnail(
                        albumArtUri, new android.util.Size(size, size), null);
            }
            String[] projection = {Albums.ALBUM_ART};
            Cursor cursor = resolver.query(Albums.EXTERNAL_CONTENT_URI, projection,
                    Albums._ID + "=?", new String[]{String.valueOf(albumId)}, null);
            if (cursor == null) return null;
            try {
                if (cursor.moveToFirst()) {
                    String path = cursor.getString(0);
                    if (path != null) return BitmapFactory.decodeFile(path);
                }
            } finally {
                cursor.close();
            }
        } catch (OutOfMemoryError e) {
            Log.w(TAG, "OOM decoding album art fallback for edit, album " + albumId);
        } catch (Throwable t) {
            Log.w(TAG, "no album art for edit, album " + albumId);
        }
        return null;
    }

    @Override
    public void delete() {
        GalleryUtils.assertNotInRenderThread();
        Uri baseUri = Audio.Media.EXTERNAL_CONTENT_URI;
        mApplication.getContentResolver().delete(baseUri, "_id=?",
                new String[]{String.valueOf(id)});
    }

    @Override
    public void rotate(int degrees) {
        // TODO
    }

    @Override
    public Uri getContentUri() {
        Uri baseUri = Audio.Media.EXTERNAL_CONTENT_URI;
        return baseUri.buildUpon().appendPath(String.valueOf(id)).build();
    }

    @Override
    public Uri getPlayUri() {
        return getContentUri();
    }

    @Override
    public int getMediaType() {
        // MEDIA_TYPE_VIDEO is intentionally kept (not renamed, per instruction):
        // every item that carries it is now an audio track, not a video.
        return MEDIA_TYPE_VIDEO;
    }

    @Override
    public MediaDetails getDetails() {
        MediaDetails details = super.getDetails();
        int s = durationInSec;
        if (s > 0) {
            details.addDetail(MediaDetails.INDEX_DURATION, GalleryUtils.formatDuration(
                    mApplication.getAndroidContext(), durationInSec));
        }
        return details;
    }

    @Override
    public int getWidth() {
        return width;
    }

    @Override
    public int getHeight() {
        return height;
    }

    @Override
    public String getFilePath() {
        return filePath;
    }
}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, datetime, shutil

os.chdir(os.path.expanduser("~/Galeria3D"))

DATA = "app/src/main/java/com/android/gallery3d/data"
UTIL = "app/src/main/java/com/android/gallery3d/util"

required = ["LocalVideo.java", "LocalSource.java", "LocalAlbumSet.java", "MediaObject.java",
            "LocalAlbum.java", "SecureAlbum.java", "BucketHelper.java", "DataManager.java",
            "LocalMediaItem.java"]
for f in required:
    if not os.path.isfile(os.path.join(DATA, f)):
        print("ERRO: " + os.path.join(DATA, f) + " nao existe. O projeto precisa estar no estado limpo antes de rodar.")
        sys.exit(1)

BK = os.path.expanduser("~/Galeria3D_backups/passo1_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(BK, exist_ok=True)
for f in required:
    shutil.copy(os.path.join(DATA, f), os.path.join(BK, f))
shutil.copy(os.path.join(UTIL, "MediaSetUtils.java"), os.path.join(BK, "MediaSetUtils.java"))
print("Backup salvo em " + BK)

LOCAL_AUDIO_JAVA = """/*
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
        return SUPPORT_DELETE | SUPPORT_SHARE | SUPPORT_PLAY | SUPPORT_INFO | SUPPORT_TRIM | SUPPORT_MUTE;
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
"""

with open(os.path.join(DATA, "LocalAudio.java"), "w", encoding="utf-8") as f:
    f.write(LOCAL_AUDIO_JAVA)
os.remove(os.path.join(DATA, "LocalVideo.java"))
print("LocalVideo.java removido, LocalAudio.java criado")


def patch(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        count = content.count(old)
        if count != 1:
            print("ERRO: em " + path + ", encontrei " + str(count) + " ocorrencia(s) (esperava 1) para o trecho abaixo:")
            print("---")
            print(old)
            print("---")
            sys.exit(1)
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: " + path + " (" + str(len(replacements)) + " substituicoes aplicadas)")


patch(os.path.join(DATA, "LocalSource.java"), [
    ("    private static final int LOCAL_IMAGE_ALBUMSET = 0;\n"
     "    private static final int LOCAL_VIDEO_ALBUMSET = 1;\n"
     "    private static final int LOCAL_IMAGE_ALBUM = 2;\n"
     "    private static final int LOCAL_VIDEO_ALBUM = 3;\n"
     "    private static final int LOCAL_IMAGE_ITEM = 4;\n"
     "    private static final int LOCAL_VIDEO_ITEM = 5;\n",
     "    private static final int LOCAL_IMAGE_ALBUMSET = 0;\n"
     "    private static final int LOCAL_AUDIO_ALBUMSET = 1;\n"
     "    private static final int LOCAL_IMAGE_ALBUM = 2;\n"
     "    private static final int LOCAL_AUDIO_ALBUM = 3;\n"
     "    private static final int LOCAL_IMAGE_ITEM = 4;\n"
     "    private static final int LOCAL_AUDIO_ITEM = 5;\n"),

    ("        mMatcher.add(\"/local/image\", LOCAL_IMAGE_ALBUMSET);\n"
     "        mMatcher.add(\"/local/video\", LOCAL_VIDEO_ALBUMSET);\n",
     "        mMatcher.add(\"/local/image\", LOCAL_IMAGE_ALBUMSET);\n"
     "        mMatcher.add(\"/local/audio\", LOCAL_AUDIO_ALBUMSET);\n"),

    ("        mMatcher.add(\"/local/image/*\", LOCAL_IMAGE_ALBUM);\n"
     "        mMatcher.add(\"/local/video/*\", LOCAL_VIDEO_ALBUM);\n"
     "        mMatcher.add(\"/local/all/*\", LOCAL_ALL_ALBUM);\n"
     "        mMatcher.add(\"/local/image/item/*\", LOCAL_IMAGE_ITEM);\n"
     "        mMatcher.add(\"/local/video/item/*\", LOCAL_VIDEO_ITEM);\n",
     "        mMatcher.add(\"/local/image/*\", LOCAL_IMAGE_ALBUM);\n"
     "        mMatcher.add(\"/local/audio/*\", LOCAL_AUDIO_ALBUM);\n"
     "        mMatcher.add(\"/local/all/*\", LOCAL_ALL_ALBUM);\n"
     "        mMatcher.add(\"/local/image/item/*\", LOCAL_IMAGE_ITEM);\n"
     "        mMatcher.add(\"/local/audio/item/*\", LOCAL_AUDIO_ITEM);\n"),

    ("        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/images/media/#\", LOCAL_IMAGE_ITEM);\n"
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/video/media/#\", LOCAL_VIDEO_ITEM);\n"
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/images/media\", LOCAL_IMAGE_ALBUM);\n"
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/video/media\", LOCAL_VIDEO_ALBUM);\n",
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/images/media/#\", LOCAL_IMAGE_ITEM);\n"
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/audio/media/#\", LOCAL_AUDIO_ITEM);\n"
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/images/media\", LOCAL_IMAGE_ALBUM);\n"
     "        mUriMatcher.addURI(MediaStore.AUTHORITY,\n"
     "                \"external/audio/media\", LOCAL_AUDIO_ALBUM);\n"),

    ("            case LOCAL_ALL_ALBUMSET:\n"
     "            case LOCAL_IMAGE_ALBUMSET:\n"
     "            case LOCAL_VIDEO_ALBUMSET:\n",
     "            case LOCAL_ALL_ALBUMSET:\n"
     "            case LOCAL_IMAGE_ALBUMSET:\n"
     "            case LOCAL_AUDIO_ALBUMSET:\n"),

    ("            case LOCAL_VIDEO_ALBUM:\n"
     "                return new LocalAlbum(path, app, mMatcher.getIntVar(0), false);\n",
     "            case LOCAL_AUDIO_ALBUM:\n"
     "                return new LocalAlbum(path, app, mMatcher.getIntVar(0), false);\n"),

    ("            case LOCAL_VIDEO_ITEM:\n"
     "                return new LocalVideo(path, mApplication, mMatcher.getIntVar(0));\n",
     "            case LOCAL_AUDIO_ITEM:\n"
     "                return new LocalAudio(path, mApplication, mMatcher.getIntVar(0));\n"),

    ("            case MEDIA_TYPE_VIDEO:\n"
     "                return Path.fromString(\"/local/video\").getChild(id);\n",
     "            case MEDIA_TYPE_VIDEO:\n"
     "                return Path.fromString(\"/local/audio\").getChild(id);\n"),

    ("                case LOCAL_VIDEO_ITEM: {\n"
     "                    long id = ContentUris.parseId(uri);\n"
     "                    return id >= 0 ? LocalVideo.ITEM_PATH.getChild(id) : null;\n"
     "                }\n",
     "                case LOCAL_AUDIO_ITEM: {\n"
     "                    long id = ContentUris.parseId(uri);\n"
     "                    return id >= 0 ? LocalAudio.ITEM_PATH.getChild(id) : null;\n"
     "                }\n"),

    ("                case LOCAL_VIDEO_ALBUM: {\n"
     "                    return getAlbumPath(uri, MEDIA_TYPE_VIDEO);\n"
     "                }\n",
     "                case LOCAL_AUDIO_ALBUM: {\n"
     "                    return getAlbumPath(uri, MEDIA_TYPE_VIDEO);\n"
     "                }\n"),

    ("            // We assume the form is: \"/local/{image,video}/item/#\"\n",
     "            // We assume the form is: \"/local/{image,audio}/item/#\"\n"),

    ("            } else if (parent == LocalVideo.ITEM_PATH) {\n",
     "            } else if (parent == LocalAudio.ITEM_PATH) {\n"),
])

patch(os.path.join(DATA, "LocalAlbumSet.java"), [
    ("import android.provider.MediaStore.Images;\n"
     "import android.provider.MediaStore.Video;\n",
     "import android.provider.MediaStore.Images;\n"
     "import android.provider.MediaStore.Audio;\n"),

    ("// LocalAlbumSet lists all image or video albums in the local storage.\n"
     "// The path should be \"/local/image\", \"local/video\" or \"/local/all\"\n",
     "// LocalAlbumSet lists all image or audio albums in the local storage.\n"
     "// The path should be \"/local/image\", \"local/audio\" or \"/local/all\"\n"),

    ("    public static final Path PATH_VIDEO = Path.fromString(\"/local/video\");\n",
     "    public static final Path PATH_AUDIO = Path.fromString(\"/local/audio\");\n"),

    ("    private static final Uri[] mWatchUris =\n"
     "        {Images.Media.EXTERNAL_CONTENT_URI, Video.Media.EXTERNAL_CONTENT_URI};\n",
     "    private static final Uri[] mWatchUris =\n"
     "        {Images.Media.EXTERNAL_CONTENT_URI, Audio.Media.EXTERNAL_CONTENT_URI};\n"),

    ("                    Comparator<MediaItem> comp = DataManager.sDateTakenComparator;\n"
     "                    return new LocalMergeAlbum(path, comp, new MediaSet[] {\n"
     "                            getLocalAlbum(manager, MEDIA_TYPE_IMAGE, PATH_IMAGE, id, name),\n"
     "                            getLocalAlbum(manager, MEDIA_TYPE_VIDEO, PATH_VIDEO, id, name)}, id);\n",
     "                    Comparator<MediaItem> comp = DataManager.sDateTakenComparator;\n"
     "                    return new LocalMergeAlbum(path, comp, new MediaSet[] {\n"
     "                            getLocalAlbum(manager, MEDIA_TYPE_IMAGE, PATH_IMAGE, id, name),\n"
     "                            getLocalAlbum(manager, MEDIA_TYPE_VIDEO, PATH_AUDIO, id, name)}, id);\n"),
])

patch(os.path.join(DATA, "MediaObject.java"), [
    ("    public static final String MEDIA_TYPE_IMAGE_STRING = \"image\";\n"
     "    public static final String MEDIA_TYPE_VIDEO_STRING = \"video\";\n"
     "    public static final String MEDIA_TYPE_ALL_STRING = \"all\";\n",
     "    public static final String MEDIA_TYPE_IMAGE_STRING = \"image\";\n"
     "    // Value changed from \"video\" to \"audio\": PATH_VIDEO/PATH_AUDIO (see\n"
     "    // LocalAlbumSet) now uses \"/local/audio\", and getTypeFromPath() parses\n"
     "    // that path segment through this string. The constant NAME is kept\n"
     "    // unchanged (MEDIA_TYPE_VIDEO_STRING) per instruction, only the value\n"
     "    // it holds changed to match the new path.\n"
     "    public static final String MEDIA_TYPE_VIDEO_STRING = \"audio\";\n"
     "    public static final String MEDIA_TYPE_ALL_STRING = \"all\";\n"),
])

patch(os.path.join(DATA, "LocalAlbum.java"), [
    ("            mProjection = LocalVideo.PROJECTION;\n"
     "            mItemPath = LocalVideo.ITEM_PATH;\n",
     "            mProjection = LocalAudio.PROJECTION;\n"
     "            mItemPath = LocalAudio.ITEM_PATH;\n"),

    ("                    item = new LocalVideo(path, app, cursor);\n",
     "                    item = new LocalAudio(path, app, cursor);\n"),

    ("            projection = LocalVideo.PROJECTION;\n"
     "            itemPath = LocalVideo.ITEM_PATH;\n",
     "            projection = LocalAudio.PROJECTION;\n"
     "            itemPath = LocalAudio.ITEM_PATH;\n"),
])

patch(os.path.join(DATA, "SecureAlbum.java"), [
    ("            pathBase = LocalVideo.ITEM_PATH;\n",
     "            pathBase = LocalAudio.ITEM_PATH;\n"),
])

patch(os.path.join(DATA, "BucketHelper.java"), [
    ("import android.provider.MediaStore.Video;\n",
     "import android.provider.MediaStore.Audio;\n"),

    ("        if ((type & MediaObject.MEDIA_TYPE_VIDEO) != 0) {\n"
     "            updateBucketEntriesFromTable(\n"
     "                    jc, resolver, Video.Media.EXTERNAL_CONTENT_URI, buckets);\n"
     "        }\n",
     "        if ((type & MediaObject.MEDIA_TYPE_VIDEO) != 0) {\n"
     "            updateBucketEntriesFromTable(\n"
     "                    jc, resolver, Audio.Media.EXTERNAL_CONTENT_URI, buckets);\n"
     "        }\n"),

    ("        if ((type & MediaObject.MEDIA_TYPE_VIDEO) != 0) {\n"
     "            typeBits |= (1 << FileColumns.MEDIA_TYPE_VIDEO);\n"
     "        }\n",
     "        if ((type & MediaObject.MEDIA_TYPE_VIDEO) != 0) {\n"
     "            // Files-table media_type must point at the real audio rows, even\n"
     "            // though our app-level flag keeps the name MEDIA_TYPE_VIDEO.\n"
     "            typeBits |= (1 << FileColumns.MEDIA_TYPE_AUDIO);\n"
     "        }\n"),

    ("            result = getBucketNameInTable(\n"
     "                    resolver, Video.Media.EXTERNAL_CONTENT_URI, bucketId);\n",
     "            result = getBucketNameInTable(\n"
     "                    resolver, Audio.Media.EXTERNAL_CONTENT_URI, bucketId);\n"),
])

patch(os.path.join(DATA, "DataManager.java"), [
    ("    private static final String TOP_LOCAL_VIDEO_SET_PATH = \"/local/video\";\n",
     "    private static final String TOP_LOCAL_VIDEO_SET_PATH = \"/local/audio\";\n"),
])

patch(os.path.join(UTIL, "MediaSetUtils.java"), [
    ("            Path.fromString(\"/local/video/\" + CAMERA_BUCKET_ID)};\n",
     "            Path.fromString(\"/local/audio/\" + CAMERA_BUCKET_ID)};\n"),
])

patch(os.path.join(DATA, "LocalMediaItem.java"), [
    ("// in LocalImage and LocalVideo.\n",
     "// in LocalImage and LocalAudio.\n"),
])

print()
print("TODOS OS PATCHES APLICADOS COM SUCESSO.")
print()
print("=== Verificacao final ===")
import subprocess
leftover_path = subprocess.run(["grep", "-rn", "\"/local/video", "app/src/main/java/"], capture_output=True, text=True).stdout
leftover_class = subprocess.run(["grep", "-rln", "LocalVideo", "app/src/main/java/"], capture_output=True, text=True).stdout
if leftover_path.strip():
    print("!!! ACHOU RESTO DE /local/video !!!")
    print(leftover_path)
else:
    print("OK: nenhum resto de /local/video")
if leftover_class.strip():
    print("!!! ACHOU RESTO DE LocalVideo !!!")
    print(leftover_class)
else:
    print("OK: nenhum resto de LocalVideo")
print()
print("Passo 1 aplicado. Agora rode: ./gradlew assembleDebug")

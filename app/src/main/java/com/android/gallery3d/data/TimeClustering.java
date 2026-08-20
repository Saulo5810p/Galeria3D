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
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.provider.MediaStore.Audio;
import android.provider.MediaStore.Audio.Playlists;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

// Passo 5 (Player3D): reescrito por dentro para agrupar faixas de audio
// por PLAYLIST do dispositivo, no lugar do agrupamento original por
// data/hora. Le as playlists via MediaStore.Audio.Playlists e os membros
// de cada uma via Playlists.Members, na ordem de PLAY_ORDER. Mantem
// apenas a assinatura publica da classe base Clustering.
public class TimeClustering extends Clustering {
    @SuppressWarnings("unused")
    private static final String TAG = "TimeClustering";

    private final Context mContext;
    private ArrayList<ArrayList<Path>> mClusters;
    private ArrayList<String> mNames;

    public TimeClustering(Context context) {
        mContext = context;
        mClusters = new ArrayList<ArrayList<Path>>();
        mNames = new ArrayList<String>();
    }

    @Override
    public void run(MediaSet baseSet) {
        mClusters = new ArrayList<ArrayList<Path>>();
        mNames = new ArrayList<String>();

        // Mapa _id (MediaStore) -> Path, para so incluir na playlist as
        // faixas que tambem existem na arvore /local/audio atual (evita
        // listar faixas apagadas/movidas que ainda estejam na playlist).
        final HashMap<Long, Path> idToPath = new HashMap<Long, Path>();
        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                if (item instanceof LocalAudio) {
                    idToPath.put((long) ((LocalAudio) item).id, item.getPath());
                }
            }
        });

        ContentResolver resolver = mContext.getContentResolver();
        LinkedHashMap<Long, String> playlists = queryPlaylists(resolver);

        for (Map.Entry<Long, String> playlist : playlists.entrySet()) {
            ArrayList<Path> members = queryPlaylistMembers(resolver, playlist.getKey(), idToPath);
            if (members.isEmpty()) continue;
            mNames.add(playlist.getValue());
            mClusters.add(members);
        }
    }

    private LinkedHashMap<Long, String> queryPlaylists(ContentResolver resolver) {
        LinkedHashMap<Long, String> result = new LinkedHashMap<Long, String>();
        String[] projection = {Playlists._ID, Playlists.NAME};
        Cursor cursor = resolver.query(Playlists.EXTERNAL_CONTENT_URI, projection,
                null, null, Playlists.NAME + " ASC");
        if (cursor == null) return result;
        try {
            while (cursor.moveToNext()) {
                long id = cursor.getLong(0);
                String name = cursor.getString(1);
                if (name == null) continue;
                result.put(id, name);
            }
        } finally {
            cursor.close();
        }
        return result;
    }

    private ArrayList<Path> queryPlaylistMembers(ContentResolver resolver, long playlistId,
            HashMap<Long, Path> idToPath) {
        ArrayList<Path> result = new ArrayList<Path>();
        Uri membersUri = Playlists.Members.getContentUri("external", playlistId);
        String[] projection = {Playlists.Members.AUDIO_ID};
        Cursor cursor = resolver.query(membersUri, projection, null, null,
                Playlists.Members.PLAY_ORDER + " ASC");
        if (cursor == null) return result;
        try {
            while (cursor.moveToNext()) {
                long audioId = cursor.getLong(0);
                Path path = idToPath.get(audioId);
                if (path != null) {
                    result.add(path);
                }
            }
        } finally {
            cursor.close();
        }
        return result;
    }

    @Override
    public int getNumberOfClusters() {
        return mClusters.size();
    }

    @Override
    public ArrayList<Path> getCluster(int index) {
        return mClusters.get(index);
    }

    @Override
    public String getClusterName(int index) {
        return mNames.get(index);
    }
}

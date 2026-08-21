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
import java.util.Collections;
import java.util.Comparator;
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

        // Mapa _id (MediaStore) -> Path/titulo, para so incluir na
        // playlist as faixas que tambem existem na arvore /local/audio
        // atual (evita listar faixas apagadas/movidas que ainda estejam
        // na playlist) e para poder ordenar os membros por titulo.
        final HashMap<Long, Path> idToPath = new HashMap<Long, Path>();
        final HashMap<Long, String> idToTitle = new HashMap<Long, String>();
        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                if (item instanceof LocalAudio) {
                    long id = (long) ((LocalAudio) item).id;
                    idToPath.put(id, item.getPath());
                    idToTitle.put(id, item.getName() != null ? item.getName() : "");
                }
            }
        });

        ContentResolver resolver = mContext.getContentResolver();
        LinkedHashMap<Long, String> playlists = queryPlaylists(resolver);

        for (Map.Entry<Long, String> playlist : playlists.entrySet()) {
            ArrayList<Path> members = queryPlaylistMembers(
                    resolver, playlist.getKey(), idToPath, idToTitle);
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

    private static class TitledPath {
        Path path;
        String title;
    }

    private ArrayList<Path> queryPlaylistMembers(ContentResolver resolver, long playlistId,
            HashMap<Long, Path> idToPath, HashMap<Long, String> idToTitle) {
        final ArrayList<TitledPath> titled = new ArrayList<TitledPath>();
        Uri membersUri = Playlists.Members.getContentUri("external", playlistId);
        String[] projection = {Playlists.Members.AUDIO_ID};
        // Fix (Player3D): o PLAY_ORDER (ordem manual que o usuario deu a
        // playlist) deixou de ser usado para exibir/ordenar - as faixas
        // agora sao reordenadas por titulo logo abaixo, para ficar igual
        // a ordem alfabetica usada pela fila de reproducao e pelas outras
        // abas (Musicas/Artistas). O ORDER BY aqui so mantem a consulta
        // deterministica antes da reordenacao.
        Cursor cursor = resolver.query(membersUri, projection, null, null,
                Playlists.Members.PLAY_ORDER + " ASC");
        if (cursor == null) return new ArrayList<Path>();
        try {
            while (cursor.moveToNext()) {
                long audioId = cursor.getLong(0);
                Path path = idToPath.get(audioId);
                if (path != null) {
                    TitledPath tp = new TitledPath();
                    tp.path = path;
                    String title = idToTitle.get(audioId);
                    tp.title = (title != null) ? title : "";
                    titled.add(tp);
                }
            }
        } finally {
            cursor.close();
        }

        Collections.sort(titled, new Comparator<TitledPath>() {
            @Override
            public int compare(TitledPath a, TitledPath b) {
                return a.title.compareToIgnoreCase(b.title);
            }
        });

        ArrayList<Path> result = new ArrayList<Path>(titled.size());
        for (TitledPath tp : titled) {
            result.add(tp.path);
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

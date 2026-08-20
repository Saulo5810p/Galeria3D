/*
 * Copyright (C) 2011 The Android Open Source Project
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

import android.content.Context;

import com.android.gallery3d.R;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

// Passo 5 (Player3D): reescrito por dentro para listar as N ultimas
// faixas reproduzidas (historico local, PlaybackHistoryDatabase), no
// lugar do agrupamento original por rosto detectado. Lista PLANA (um
// unico "cluster"), sem subpastas, ordenada da mais recente para a mais
// antiga. Mantem apenas a assinatura publica da classe base Clustering.
public class FaceClustering extends Clustering {
    @SuppressWarnings("unused")
    private static final String TAG = "FaceClustering";

    private static final int HISTORY_LIMIT = 100;

    private final Context mContext;
    private String mRecentlyPlayedString;
    private ArrayList<Path> mRecent;

    public FaceClustering(Context context) {
        mContext = context;
        mRecentlyPlayedString = context.getResources().getString(R.string.filter_recently_played);
    }

    @Override
    public void run(MediaSet baseSet) {
        // Mapa id (MediaStore, o mesmo usado em LocalAudio.id) -> Path,
        // restrito as faixas que ainda existem na arvore /local/audio
        // atual (evita listar historico de faixas apagadas).
        final HashMap<Integer, Path> idToPath = new HashMap<Integer, Path>();
        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                if (item instanceof LocalAudio) {
                    idToPath.put(((LocalAudio) item).id, item.getPath());
                }
            }
        });

        PlaybackHistoryDatabase db = new PlaybackHistoryDatabase(mContext);
        List<Long> recentIds;
        try {
            recentIds = db.getRecentDistinctTrackIds(HISTORY_LIMIT);
        } finally {
            db.close();
        }

        mRecent = new ArrayList<Path>();
        for (long trackId : recentIds) {
            Path path = idToPath.get((int) trackId);
            if (path != null) {
                mRecent.add(path);
            }
        }
    }

    @Override
    public int getNumberOfClusters() {
        // Lista plana: 1 cluster so (se houver historico), sem subpastas.
        return mRecent != null && !mRecent.isEmpty() ? 1 : 0;
    }

    @Override
    public ArrayList<Path> getCluster(int index) {
        return mRecent;
    }

    @Override
    public String getClusterName(int index) {
        return mRecentlyPlayedString;
    }
}

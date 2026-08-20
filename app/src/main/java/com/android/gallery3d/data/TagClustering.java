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

import android.content.Context;

import com.android.gallery3d.R;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

// Passo 5 (Player3D): simplificado para ser a pasta raiz "Musicas" - todas
// as faixas de /local/audio em ordem alfabetica por TITLE, sem nenhum
// agrupamento. No lugar do agrupamento original por etiqueta/tag.
public class TagClustering extends Clustering {
    @SuppressWarnings("unused")
    private static final String TAG = "TagClustering";

    private String mAllTracksString;
    private ArrayList<Path> mAllTracks;

    private static class TitledPath {
        Path path;
        String title;
    }

    public TagClustering(Context context) {
        mAllTracksString = context.getResources().getString(R.string.filter_all_tracks);
    }

    @Override
    public void run(MediaSet baseSet) {
        final ArrayList<TitledPath> items = new ArrayList<TitledPath>();
        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                TitledPath tp = new TitledPath();
                tp.path = item.getPath();
                tp.title = (item instanceof LocalAudio && ((LocalAudio) item).caption != null)
                        ? ((LocalAudio) item).caption
                        : "";
                items.add(tp);
            }
        });

        Collections.sort(items, new Comparator<TitledPath>() {
            @Override
            public int compare(TitledPath a, TitledPath b) {
                return a.title.compareToIgnoreCase(b.title);
            }
        });

        mAllTracks = new ArrayList<Path>(items.size());
        for (TitledPath tp : items) {
            mAllTracks.add(tp.path);
        }
    }

    @Override
    public int getNumberOfClusters() {
        return mAllTracks != null && !mAllTracks.isEmpty() ? 1 : 0;
    }

    @Override
    public ArrayList<Path> getCluster(int index) {
        return mAllTracks;
    }

    @Override
    public String getClusterName(int index) {
        return mAllTracksString;
    }
}

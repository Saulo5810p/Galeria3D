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
import java.util.Map;
import java.util.TreeMap;

// Passo 5 (Player3D): reescrito por dentro para agrupar faixas de audio
// por artista (AudioColumns.ARTIST), no lugar do algoritmo original de
// k-means + reverse geocoding por lat/long (que nao faz sentido para
// audio). Mantem apenas a assinatura publica da classe base Clustering.
//
// Artista com mais de 1 musica: gera uma pasta com o nome do artista.
// Artista com so 1 musica: a faixa aparece solta na listagem (nao cria
// pasta de artista com 1 item so), conforme especificado.
class LocationClustering extends Clustering {
    @SuppressWarnings("unused")
    private static final String TAG = "LocationClustering";

    private String mUnknownArtistString;
    private ArrayList<ArrayList<Path>> mClusters;
    private ArrayList<String> mNames;

    public LocationClustering(Context context) {
        mUnknownArtistString = context.getResources().getString(R.string.unknown);
    }

    private static class TitledPath {
        Path path;
        String title;
    }

    @Override
    public void run(MediaSet baseSet) {
        // Agrupa por nome de artista. Usa TreeMap para ordem alfabetica
        // estavel entre reloads (o path do cluster e por indice, entao a
        // ordem precisa ser deterministica).
        final TreeMap<String, ArrayList<TitledPath>> byArtist =
                new TreeMap<String, ArrayList<TitledPath>>();

        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                String artist = mUnknownArtistString;
                if (item instanceof LocalAudio) {
                    String a = ((LocalAudio) item).artist;
                    if (a != null && a.trim().length() > 0) {
                        artist = a;
                    }
                }
                ArrayList<TitledPath> list = byArtist.get(artist);
                if (list == null) {
                    list = new ArrayList<TitledPath>();
                    byArtist.put(artist, list);
                }
                TitledPath tp = new TitledPath();
                tp.path = item.getPath();
                tp.title = (item.getName() != null) ? item.getName() : "";
                list.add(tp);
            }
        });

        // Fix (Player3D): dentro de cada artista, ordena as faixas por
        // titulo (mesmo criterio alfabetico usado pela fila de reproducao
        // e pelas outras abas), em vez de deixar na ordem de enumeracao
        // do MediaStore.
        Comparator<TitledPath> byTitle = new Comparator<TitledPath>() {
            @Override
            public int compare(TitledPath a, TitledPath b) {
                return a.title.compareToIgnoreCase(b.title);
            }
        };

        // Artistas com 1 unica faixa: a faixa fica solta (sem subpasta) -
        // colocamos cada uma dessas faixas em seu proprio "cluster" de
        // tamanho 1 cujo nome e o TITULO da faixa, nao o nome do artista,
        // para nao criar uma pasta de artista com um item so. Artistas
        // com 2+ faixas viram uma pasta de verdade com o nome do artista.
        mClusters = new ArrayList<ArrayList<Path>>();
        mNames = new ArrayList<String>();
        for (Map.Entry<String, ArrayList<TitledPath>> entry : byArtist.entrySet()) {
            ArrayList<TitledPath> titledPaths = entry.getValue();
            Collections.sort(titledPaths, byTitle);

            ArrayList<Path> paths = new ArrayList<Path>(titledPaths.size());
            for (TitledPath tp : titledPaths) {
                paths.add(tp.path);
            }

            mNames.add(entry.getKey());
            mClusters.add(paths);
        }
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

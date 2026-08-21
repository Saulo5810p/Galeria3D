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
import android.net.Uri;

import com.android.gallery3d.app.GalleryApp;

import java.util.ArrayList;
import java.util.HashSet;

public class ClusterAlbumSet extends MediaSet implements ContentListener {
    @SuppressWarnings("unused")
    private static final String TAG = "ClusterAlbumSet";
    private GalleryApp mApplication;
    private MediaSet mBaseSet;
    private int mKind;
    // Passo 6: mAllAlbums e a lista completa de pastas/artistas/playlists,
    // exatamente como o clustering monta. mAlbums e o que getSubMediaSet*
    // realmente expoe para a grade -- vira a versao filtrada (por nome do
    // proprio card, ex: nome do artista/album/playlist) quando ha busca
    // ativa, senao e uma copia de mAllAlbums.
    private ArrayList<ClusterAlbum> mAllAlbums = new ArrayList<ClusterAlbum>();
    private ArrayList<ClusterAlbum> mAlbums = new ArrayList<ClusterAlbum>();
    private String mSearchQuery = "";
    private boolean mFirstReloadDone;

    public ClusterAlbumSet(Path path, GalleryApp application,
            MediaSet baseSet, int kind) {
        super(path, INVALID_DATA_VERSION);
        mApplication = application;
        mBaseSet = baseSet;
        mKind = kind;
        baseSet.addContentListener(this);
    }

    @Override
    public MediaSet getSubMediaSet(int index) {
        return mAlbums.get(index);
    }

    @Override
    public int getSubMediaSetCount() {
        return mAlbums.size();
    }

    // Passo 6: recebe o texto da barra de busca holo e refaz mAlbums a
    // partir de mAllAlbums, escondendo da grade os cards cujo nome (nome
    // do artista/album/playlist, via getName()) nao contem o texto --
    // case-insensitive, sem nova consulta ao MediaStore. Tambem repassa a
    // mesma query para dentro de cada ClusterAlbum restante, para o caso
    // de o usuario abrir esse card em seguida (AlbumPage) e a busca por
    // faixa/artista dentro dele continuar coerente com o que foi digitado.
    public void setSearchFilter(String query) {
        mSearchQuery = (query == null) ? "" : query.trim();
        applySearchFilter();
        // Passo 6 (correcao): applySearchFilter() so troca a lista mAlbums
        // em memoria - sem isso, reload() (chamado pela thread de
        // carregamento da grade) so incrementa mDataVersion quando o
        // MediaStore muda, entao a busca nunca aparecia na tela mesmo
        // filtrando certo por baixo dos panos. Forcamos aqui uma nova
        // versao para o loader perceber a mudanca e redesenhar a grade.
        mDataVersion = nextVersionNumber();
        notifyContentChanged();
    }

    private void applySearchFilter() {
        if (mSearchQuery.isEmpty()) {
            mAlbums = new ArrayList<ClusterAlbum>(mAllAlbums);
            for (ClusterAlbum album : mAllAlbums) {
                album.setSearchFilter("");
            }
            return;
        }
        String needle = mSearchQuery.toLowerCase();
        ArrayList<ClusterAlbum> filtered = new ArrayList<ClusterAlbum>();
        for (ClusterAlbum album : mAllAlbums) {
            String name = album.getName();
            if (name != null && name.toLowerCase().contains(needle)) {
                filtered.add(album);
            }
            // Passo 6: independente do card em si bater com a busca, o
            // conteudo (faixas) dele tambem e filtrado -- assim, ao abrir
            // qualquer album (mesmo um que nao tenha sido escondido), a
            // lista de faixas la dentro reflete a mesma busca ativa aqui.
            album.setSearchFilter(mSearchQuery);
        }
        mAlbums = filtered;
    }

    @Override
    public String getName() {
        return mBaseSet.getName();
    }

    @Override
    public long reload() {
        if (mBaseSet.reload() > mDataVersion) {
            if (mFirstReloadDone) {
                updateClustersContents();
            } else {
                updateClusters();
                mFirstReloadDone = true;
            }
            mDataVersion = nextVersionNumber();
        }
        return mDataVersion;
    }

    @Override
    public void onContentDirty() {
        notifyContentChanged();
    }

    private void updateClusters() {
        mAllAlbums.clear();
        Clustering clustering;
        Context context = mApplication.getAndroidContext();
        switch (mKind) {
            case ClusterSource.CLUSTER_ALBUMSET_TIME:
                clustering = new TimeClustering(context);
                break;
            case ClusterSource.CLUSTER_ALBUMSET_LOCATION:
                clustering = new LocationClustering(context);
                break;
            case ClusterSource.CLUSTER_ALBUMSET_TAG:
                clustering = new TagClustering(context);
                break;
            case ClusterSource.CLUSTER_ALBUMSET_FACE:
                clustering = new FaceClustering(context);
                break;
            default: /* CLUSTER_ALBUMSET_SIZE */
                clustering = new SizeClustering(context);
                break;
        }

        clustering.run(mBaseSet);
        int n = clustering.getNumberOfClusters();
        DataManager dataManager = mApplication.getDataManager();
        for (int i = 0; i < n; i++) {
            Path childPath;
            String childName = clustering.getClusterName(i);
            if (mKind == ClusterSource.CLUSTER_ALBUMSET_TAG) {
                childPath = mPath.getChild(Uri.encode(childName));
            } else if (mKind == ClusterSource.CLUSTER_ALBUMSET_SIZE) {
                long minSize = ((SizeClustering) clustering).getMinSize(i);
                childPath = mPath.getChild(minSize);
            } else {
                childPath = mPath.getChild(i);
            }

            ClusterAlbum album;
            synchronized (DataManager.LOCK) {
                album = (ClusterAlbum) dataManager.peekMediaObject(childPath);
                if (album == null) {
                    album = new ClusterAlbum(childPath, dataManager, this);
                }
            }
            album.setMediaItems(clustering.getCluster(i));
            album.setName(childName);
            album.setCoverMediaItem(clustering.getClusterCover(i));
            mAllAlbums.add(album);
        }
        // Passo 6: reaplica a busca ativa (se houver) sobre a lista recem
        // montada, para derivar mAlbums.
        applySearchFilter();
    }

    private void updateClustersContents() {
        final HashSet<Path> existing = new HashSet<Path>();
        mBaseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                existing.add(item.getPath());
            }
        });

        int n = mAllAlbums.size();

        // The loop goes backwards because we may remove empty albums from
        // mAllAlbums.
        for (int i = n - 1; i >= 0; i--) {
            ArrayList<Path> oldPaths = mAllAlbums.get(i).getMediaItems();
            ArrayList<Path> newPaths = new ArrayList<Path>();
            int m = oldPaths.size();
            for (int j = 0; j < m; j++) {
                Path p = oldPaths.get(j);
                if (existing.contains(p)) {
                    newPaths.add(p);
                }
            }
            mAllAlbums.get(i).setMediaItems(newPaths);
            if (newPaths.isEmpty()) {
                mAllAlbums.remove(i);
            }
        }
        // Passo 6: reaplica a busca ativa (se houver) sobre a lista
        // reconciliada, para derivar mAlbums.
        applySearchFilter();
    }
}

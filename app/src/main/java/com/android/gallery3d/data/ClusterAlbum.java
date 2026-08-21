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

import java.util.ArrayList;

public class ClusterAlbum extends MediaSet implements ContentListener {
    @SuppressWarnings("unused")
    private static final String TAG = "ClusterAlbum";
    // Passo 6: mAllPaths guarda a lista completa (sem filtro) exatamente
    // como veio do clustering. mPaths e o que os metodos publicos
    // (getMediaItemCount/getMediaItem/etc) de fato leem -- vira a versao
    // filtrada quando ha uma busca ativa, ou uma copia de mAllPaths
    // quando nao ha. Nenhuma nova query ao MediaStore: e so um filtro
    // in-memory sobre o que ja foi carregado.
    private ArrayList<Path> mAllPaths = new ArrayList<Path>();
    private ArrayList<Path> mPaths = new ArrayList<Path>();
    private String mSearchQuery = "";
    private String mName = "";
    private DataManager mDataManager;
    private MediaSet mClusterAlbumSet;
    private MediaItem mCover;

    public ClusterAlbum(Path path, DataManager dataManager,
            MediaSet clusterAlbumSet) {
        super(path, nextVersionNumber());
        mDataManager = dataManager;
        mClusterAlbumSet = clusterAlbumSet;
        mClusterAlbumSet.addContentListener(this);
    }

    public void setCoverMediaItem(MediaItem cover) {
        mCover = cover;
    }

    @Override
    public MediaItem getCoverMediaItem() {
        return mCover != null ? mCover : super.getCoverMediaItem();
    }

    // Passo 6: recebe o texto digitado na barra de busca holo e refaz
    // mPaths a partir de mAllPaths, comparando TITLE (getName()) e, para
    // faixas de audio (LocalAudio), tambem o artista -- ambos via
    // String.contains() case-insensitive, sem nova consulta ao MediaStore.
    // query vazia/nula reseta para a lista completa.
    public void setSearchFilter(String query) {
        mSearchQuery = (query == null) ? "" : query.trim();
        applySearchFilter();
        // Passo 6 (correcao): mesmo motivo do ClusterAlbumSet - sem isso,
        // reload() nunca detecta a mudanca (o MediaStore em si nao mudou)
        // e a lista de faixas na tela nunca e atualizada apos filtrar.
        mDataVersion = nextVersionNumber();
        notifyContentChanged();
    }

    private void applySearchFilter() {
        if (mSearchQuery.isEmpty()) {
            mPaths = new ArrayList<Path>(mAllPaths);
            return;
        }
        String needle = mSearchQuery.toLowerCase();
        ArrayList<Path> filtered = new ArrayList<Path>();
        ArrayList<MediaItem> items = getMediaItemFromPath(
                mAllPaths, 0, mAllPaths.size(), mDataManager);
        for (MediaItem item : items) {
            if (item == null) continue;
            boolean matches = false;
            String title = item.getName();
            if (title != null && title.toLowerCase().contains(needle)) {
                matches = true;
            }
            if (!matches && item instanceof LocalAudio) {
                String artist = ((LocalAudio) item).artist;
                if (artist != null && artist.toLowerCase().contains(needle)) {
                    matches = true;
                }
            }
            if (matches) {
                filtered.add(item.getPath());
            }
        }
        mPaths = filtered;
    }

    void setMediaItems(ArrayList<Path> paths) {
        mAllPaths = paths;
        applySearchFilter();
    }

    ArrayList<Path> getMediaItems() {
        // Passo 6: usa mAllPaths (nao filtrado) -- este metodo alimenta a
        // reconciliacao de updateClustersContents() em ClusterAlbumSet, que
        // precisa ver todos os itens reais para decidir o que foi apagado,
        // independente de uma busca estar ativa ou nao.
        return mAllPaths;
    }

    public void setName(String name) {
        mName = name;
    }

    @Override
    public String getName() {
        return mName;
    }

    @Override
    public int getMediaItemCount() {
        return mPaths.size();
    }

    @Override
    public ArrayList<MediaItem> getMediaItem(int start, int count) {
        return getMediaItemFromPath(mPaths, start, count, mDataManager);
    }

    public static ArrayList<MediaItem> getMediaItemFromPath(
            ArrayList<Path> paths, int start, int count,
            DataManager dataManager) {
        if (start >= paths.size()) {
            return new ArrayList<MediaItem>();
        }
        int end = Math.min(start + count, paths.size());
        ArrayList<Path> subset = new ArrayList<Path>(paths.subList(start, end));
        final MediaItem[] buf = new MediaItem[end - start];
        ItemConsumer consumer = new ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                buf[index] = item;
            }
        };
        dataManager.mapMediaItems(subset, consumer, 0);
        ArrayList<MediaItem> result = new ArrayList<MediaItem>(end - start);
        for (int i = 0; i < buf.length; i++) {
            result.add(buf[i]);
        }
        return result;
    }

    @Override
    protected int enumerateMediaItems(ItemConsumer consumer, int startIndex) {
        mDataManager.mapMediaItems(mPaths, consumer, startIndex);
        return mPaths.size();
    }

    @Override
    public int getTotalMediaItemCount() {
        return mPaths.size();
    }

    @Override
    public long reload() {
        if (mClusterAlbumSet.reload() > mDataVersion) {
            mDataVersion = nextVersionNumber();
        }
        return mDataVersion;
    }

    @Override
    public void onContentDirty() {
        notifyContentChanged();
    }

    @Override
    public int getSupportedOperations() {
        return SUPPORT_SHARE | SUPPORT_DELETE | SUPPORT_INFO;
    }

    @Override
    public void delete() {
        ItemConsumer consumer = new ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                if ((item.getSupportedOperations() & SUPPORT_DELETE) != 0) {
                    item.delete();
                }
            }
        };
        mDataManager.mapMediaItems(mPaths, consumer, 0);
    }

    @Override
    public boolean isLeafAlbum() {
        return true;
    }
}

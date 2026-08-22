/*
 * Fix (Player3D, Passo 8b - popup de tipo de widget): novo picker de
 * playlist para o widget de home screen, irmao de AlbumPicker (que escolhe
 * uma pasta/album). Reaproveita o MESMO mecanismo usado pela aba
 * "Playlists" do grid principal (Passo 5) - AlbumSetPage com o filtro
 * CLUSTER_BY_TIME (TimeClustering foi reescrito nesse passo para agrupar
 * por playlist do MediaStore, nao mais por data).
 */

package com.android.gallery3d.app;

import android.content.Intent;
import android.os.Bundle;

import com.android.gallery3d.R;
import com.android.gallery3d.data.DataManager;
import com.android.gallery3d.util.FilterUtils;

public class PlaylistPicker extends PickerActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle(R.string.select_playlist);
        Intent intent = getIntent();
        Bundle extras = intent.getExtras();
        Bundle data = extras == null ? new Bundle() : new Bundle(extras);

        data.putBoolean(GalleryActivity.KEY_GET_ALBUM, true);
        data.putString(AlbumSetPage.KEY_MEDIA_PATH,
                getDataManager().getTopSetPath(DataManager.INCLUDE_IMAGE));
        data.putInt(AlbumSetPage.KEY_SELECTED_CLUSTER_TYPE, FilterUtils.CLUSTER_BY_TIME);
        getStateManager().startState(AlbumSetPage.class, data);
    }
}

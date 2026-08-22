/*
 * Passo 7 v2 (Player3D): file manager proprio, com a cara da grade 3D,
 * para escolher a pasta destino de "Mover para album". Substitui o
 * fluxo antigo (Passo 7 v1) que navegava a grade de Albuns do proprio
 * MediaStore -- problema real relatado pelo usuario: uma pasta recem
 * criada nao aparecia/nao abria na grade principal por causa de como o
 * MediaStore deriva "albuns" (buckets) so a partir de arquivos de midia
 * ja existentes, o que tornava o fluxo antigo confuso.
 *
 * Aqui a navegacao e 100% via java.io.File, fora do MediaStore -- entao
 * qualquer pasta do sdcard (vazia ou nao) pode ser navegada, criada e
 * escolhida como destino livremente, exatamente como um file manager de
 * verdade funcionaria. Reaproveita o motor visual (SlotView) da grade
 * 3D do app, mas com um renderer proprio e leve (FilePickerSlotRenderer)
 * ja que pastas de sdcard nao tem capa.
 */
package com.android.gallery3d.app;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.widget.EditText;
import android.widget.Toast;

import com.android.gallery3d.R;
import com.android.gallery3d.ui.FilePickerSlotRenderer;
import com.android.gallery3d.ui.FilePickerSlotRenderer.Entry;
import com.android.gallery3d.ui.GLView;
import com.android.gallery3d.ui.SlotView;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;

public class FilePickerPage extends ActivityState {
    @SuppressWarnings("unused")
    private static final String TAG = "FilePickerPage";

    // Passo 7 v2 (Player3D): caminho absoluto (String) da pasta onde a
    // navegacao deve comecar. Se ausente, comeca na raiz do sdcard
    // (decisao do usuario -- navegacao totalmente livre, nao restrita a
    // Music/).
    public static final String KEY_START_PATH = "file-picker-start-path";
    // Passo 7 v2 (Player3D): caminho absoluto (String) devolvido via
    // setStateResult()/finishState() quando o usuario confirma "OK" --
    // ver AlbumPage.onStateResult(REQUEST_MOVE_DESTINATION).
    public static final String KEY_RESULT_PATH = "file-picker-result-path";

    private static final int FOLDER_ICON_RES_ID = R.drawable.frame_overlay_gallery_folder;

    private final GLView mRootPane = new GLView() {
        @Override
        protected void onLayout(
                boolean changed, int left, int top, int right, int bottom) {
            int slotViewTop = mActivity.getGalleryActionBar().getHeight();
            mSlotView.layout(0, slotViewTop, right - left, bottom - top);
        }
    };

    private SlotView mSlotView;
    private FilePickerSlotRenderer mRenderer;
    private GalleryActionBar mActionBar;

    private File mCurrentDir;
    private File mStartDir;
    private ArrayList<File> mChildDirs = new ArrayList<File>();

    @Override
    public void onCreate(Bundle data, Bundle restoreState) {
        super.onCreate(data, restoreState);

        String startPath = data.getString(KEY_START_PATH);
        mStartDir = (startPath != null) ? new File(startPath)
                : android.os.Environment.getExternalStorageDirectory();
        mCurrentDir = mStartDir;

        mActionBar = mActivity.getGalleryActionBar();

        mSlotView = new SlotView(mActivity, Config.AlbumSetPage.get(mActivity).slotViewSpec);
        mRenderer = new FilePickerSlotRenderer(
                mActivity.getAndroidContext(), mSlotView, FOLDER_ICON_RES_ID);
        mSlotView.setSlotRenderer(mRenderer);
        mSlotView.setListener(new SlotView.SimpleListener() {
            @Override
            public void onSingleTapUp(int index) {
                FilePickerPage.this.onSingleTapUp(index);
            }
        });
        mRootPane.addComponent(mSlotView);
    }

    @Override
    protected void onBackPressed() {
        if (mCurrentDir.equals(mStartDir)) {
            super.onBackPressed();
            return;
        }
        File parent = mCurrentDir.getParentFile();
        if (parent == null) {
            super.onBackPressed();
            return;
        }
        mCurrentDir = parent;
        reloadCurrentDir();
    }

    @Override
    public void onResume() {
        super.onResume();
        setContentPane(mRootPane);
        mActionBar.setTitle(mCurrentDir.getName().isEmpty()
                ? "/" : mCurrentDir.getName());
        reloadCurrentDir();
    }

    @Override
    protected boolean onCreateActionBar(Menu menu) {
        MenuInflater inflater = getSupportMenuInflater();
        inflater.inflate(R.menu.filepicker, menu);
        return true;
    }

    @Override
    protected boolean onItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.action_new_folder: {
                showCreateFolderDialog();
                return true;
            }
            case R.id.action_confirm_move: {
                confirmSelection();
                return true;
            }
        }
        return false;
    }

    private void onSingleTapUp(int index) {
        Entry entry = mRenderer.getEntry(index);
        if (entry == null) return;
        mCurrentDir = entry.file;
        reloadCurrentDir();
    }

    // Passo 7 v2 (Player3D): recarrega a lista de subpastas do diretorio
    // atual, ordenadas por nome (mesmo criterio de ordenacao alfabetica
    // ja adotado no resto do app). Sem MediaStore -- File.listFiles()
    // direto, sincrono (nomes de pasta sao leves, nao ha necessidade de
    // carregamento assincrono aqui).
    private void reloadCurrentDir() {
        mActionBar.setTitle(mCurrentDir.getName().isEmpty()
                ? "/" : mCurrentDir.getName());

        File[] children = mCurrentDir.listFiles();
        mChildDirs.clear();
        if (children != null) {
            for (File f : children) {
                if (f.isDirectory() && !f.isHidden()) {
                    mChildDirs.add(f);
                }
            }
        }
        java.util.Collections.sort(mChildDirs, new Comparator<File>() {
            @Override
            public int compare(File a, File b) {
                return a.getName().compareToIgnoreCase(b.getName());
            }
        });

        ArrayList<Entry> entries = new ArrayList<Entry>();
        for (File dir : mChildDirs) {
            entries.add(new Entry(dir, dir.getName()));
        }
        mRenderer.setEntries(entries);
    }

    private void showCreateFolderDialog() {
        final EditText input = new EditText(mActivity);
        input.setSingleLine(true);
        input.setHint(R.string.create_album_hint);

        new AlertDialog.Builder(mActivity)
                .setTitle(R.string.create_album_title)
                .setView(input)
                .setPositiveButton(R.string.confirm, new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        String name = input.getText().toString().trim();
                        if (name.isEmpty() || name.contains(File.separator)
                                || name.contains("..")) {
                            Toast.makeText(mActivity,
                                    R.string.create_album_invalid_name,
                                    Toast.LENGTH_SHORT).show();
                            return;
                        }
                        File newDir = new File(mCurrentDir, name);
                        if (newDir.exists()) {
                            Toast.makeText(mActivity,
                                    R.string.create_album_exists,
                                    Toast.LENGTH_SHORT).show();
                            return;
                        }
                        if (!newDir.mkdirs()) {
                            Toast.makeText(mActivity,
                                    R.string.create_album_failure,
                                    Toast.LENGTH_SHORT).show();
                            return;
                        }
                        reloadCurrentDir();
                    }
                })
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    // Passo 7 v2 (Player3D): usuario tocou "OK" -- o diretorio atual (a
    // pasta que ele esta navegando agora, nao uma subpasta especifica)
    // e o destino escolhido. Devolve via setStateResult()/finishState(),
    // mecanismo interno do StateManager (ver AlbumPage.onStateResult).
    private void confirmSelection() {
        Intent result = new Intent();
        result.putExtra(KEY_RESULT_PATH, mCurrentDir.getAbsolutePath());
        setStateResult(android.app.Activity.RESULT_OK, result);
        mActivity.getStateManager().finishState(this);
    }
}

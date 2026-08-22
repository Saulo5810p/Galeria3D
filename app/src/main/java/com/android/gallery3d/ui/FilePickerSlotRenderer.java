/*
 * Passo 7 v2 (Player3D): renderer da grade do file manager proprio
 * ("Mover para album"). Ao contrario de AlbumSetSlotRenderer (que
 * carrega capas de fotos/audio de forma assincrona, via
 * AlbumSetSlidingWindow + ThreadPool), aqui os itens sao pastas puras
 * do sdcard -- sem capa nenhuma (sdcard nao guarda capa de pasta) --
 * entao o desenho e simples e sincrono:
 *   - um icone de pasta fixo (mesmo ResourceTexture para todas)
 *   - o nome da pasta, via StringTexture (tambem sincrono, cacheado
 *     apos o primeiro desenho)
 * Sem sliding window, sem fila assincrona: a lista inteira de
 * subpastas do diretorio atual cabe em memoria de uma vez (nomes de
 * pasta sao leves), montada por FilePickerPage e passada via
 * setEntries().
 */
package com.android.gallery3d.ui;

import java.io.File;
import java.util.List;

import com.android.gallery3d.glrenderer.ResourceTexture;
import com.android.gallery3d.glrenderer.StringTexture;
import com.android.gallery3d.glrenderer.GLCanvas;
import com.android.gallery3d.glrenderer.Texture;

public class FilePickerSlotRenderer extends AbstractSlotRenderer {

    public static class Entry {
        public final File file;
        public final String label;
        private StringTexture labelTexture;

        public Entry(File file, String label) {
            this.file = file;
            this.label = label;
        }
    }

    private static final float LABEL_TEXT_SIZE = 28f;
    private static final int LABEL_TEXT_COLOR = 0xffffffff;

    private final ResourceTexture mFolderIcon;
    private final SlotView mSlotView;

    private List<Entry> mEntries;
    private int mPressedIndex = -1;
    private boolean mAnimatePressedUp;
    private java.util.Set<Integer> mSelectedIndexes;

    public FilePickerSlotRenderer(android.content.Context context, SlotView slotView,
            int folderIconResId) {
        super(context);
        mSlotView = slotView;
        mFolderIcon = new ResourceTexture(context, folderIconResId);
    }

    public void setEntries(List<Entry> entries) {
        mEntries = entries;
        mSlotView.setSlotCount(entries == null ? 0 : entries.size());
        mSlotView.invalidate();
    }

    public Entry getEntry(int index) {
        if (mEntries == null || index < 0 || index >= mEntries.size()) return null;
        return mEntries.get(index);
    }

    public void setPressedIndex(int index) {
        if (mPressedIndex == index) return;
        mPressedIndex = index;
        mSlotView.invalidate();
    }

    public void setPressedUp() {
        if (mPressedIndex == -1) return;
        mAnimatePressedUp = true;
        mSlotView.invalidate();
    }

    public void setSelectedIndexes(java.util.Set<Integer> selected) {
        mSelectedIndexes = selected;
        mSlotView.invalidate();
    }

    @Override
    public void prepareDrawing() {
        // Nada a preparar -- sem estado assincrono para sincronizar aqui.
    }

    @Override
    public void onVisibleRangeChanged(int visibleStart, int visibleEnd) {
        // Sem sliding window: todas as entradas ja estao em memoria.
    }

    @Override
    public void onSlotSizeChanged(int width, int height) {
        // Nao ha texturas dependentes do tamanho do slot aqui.
    }

    @Override
    public int renderSlot(GLCanvas canvas, int index, int pass, int width, int height) {
        Entry entry = getEntry(index);
        if (entry == null) return 0;

        int iconSize = Math.min(width, height) * 3 / 5;
        int iconX = (width - iconSize) / 2;
        int iconY = (height - iconSize) / 2 - (height / 8);
        mFolderIcon.draw(canvas, iconX, iconY, iconSize, iconSize);

        if (entry.labelTexture == null) {
            entry.labelTexture = StringTexture.newInstance(
                    entry.label, LABEL_TEXT_SIZE, LABEL_TEXT_COLOR,
                    width - 16, false);
        }
        Texture label = entry.labelTexture;
        int labelX = (width - label.getWidth()) / 2;
        int labelY = iconY + iconSize + 12;
        label.draw(canvas, labelX, labelY);

        if (mPressedIndex == index) {
            if (mAnimatePressedUp) {
                drawPressedUpFrame(canvas, width, height);
                if (isPressedUpFrameFinished()) {
                    mAnimatePressedUp = false;
                    mPressedIndex = -1;
                }
            } else {
                drawPressedFrame(canvas, width, height);
            }
        } else if (mSelectedIndexes != null && mSelectedIndexes.contains(index)) {
            drawSelectedFrame(canvas, width, height);
        }

        return 0;
    }
}

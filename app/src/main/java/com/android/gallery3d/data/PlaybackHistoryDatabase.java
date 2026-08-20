/*
 * Passo 5 (Player3D) - novo arquivo.
 *
 * Historico local de reproducao, usado pelo filtro "Ultimos Reproduzidos"
 * (FaceClustering.java). Mesmo padrao de SQLiteOpenHelper ja usado em
 * gadget/WidgetDatabaseHelper.java, para manter consistencia de estilo.
 */
package com.android.gallery3d.data;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.util.Log;

import java.util.ArrayList;
import java.util.List;

public class PlaybackHistoryDatabase extends SQLiteOpenHelper {
    private static final String TAG = "PlaybackHistoryDatabase";
    private static final String DATABASE_NAME = "playback_history.db";
    private static final int DATABASE_VERSION = 1;

    private static final String TABLE_HISTORY = "history";
    private static final String FIELD_TRACK_ID = "track_id";
    private static final String FIELD_PLAYED_AT = "played_at_timestamp";

    public PlaybackHistoryDatabase(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE " + TABLE_HISTORY + " ("
                + FIELD_TRACK_ID + " INTEGER NOT NULL, "
                + FIELD_PLAYED_AT + " INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX idx_history_played_at ON " + TABLE_HISTORY
                + " (" + FIELD_PLAYED_AT + " DESC)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // Sem versoes anteriores ainda - nada a migrar.
    }

    /** Grava que a faixa trackId comecou a tocar agora. */
    public void recordPlay(long trackId) {
        try {
            ContentValues values = new ContentValues();
            values.put(FIELD_TRACK_ID, trackId);
            values.put(FIELD_PLAYED_AT, System.currentTimeMillis());
            getWritableDatabase().insert(TABLE_HISTORY, null, values);
        } catch (Throwable e) {
            Log.e(TAG, "falha ao gravar historico de reproducao", e);
        }
    }

    /**
     * Devolve ate `limit` track_id distintos, mais recente primeiro,
     * baseado na entrada mais recente de cada track_id no historico.
     */
    public List<Long> getRecentDistinctTrackIds(int limit) {
        ArrayList<Long> result = new ArrayList<Long>();
        String sql = "SELECT " + FIELD_TRACK_ID + ", MAX(" + FIELD_PLAYED_AT + ") AS latest "
                + "FROM " + TABLE_HISTORY
                + " GROUP BY " + FIELD_TRACK_ID
                + " ORDER BY latest DESC LIMIT ?";
        Cursor cursor = null;
        try {
            cursor = getReadableDatabase().rawQuery(sql, new String[]{String.valueOf(limit)});
            while (cursor.moveToNext()) {
                result.add(cursor.getLong(0));
            }
        } catch (Throwable e) {
            Log.e(TAG, "falha ao ler historico de reproducao", e);
        } finally {
            if (cursor != null) cursor.close();
        }
        return result;
    }
}

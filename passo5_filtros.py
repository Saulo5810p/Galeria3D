#!/usr/bin/env python3
"""
PASSO 5 (Player3D) — Substituir os filtros existentes (spinner da ActionBar)

Reaproveita o MESMO componente (spinner dropdown em GalleryActionBar.java,
FilterUtils.java, e as 4 classes de clustering já existentes em data/),
trocando o CONTEÚDO por trás de cada item, sem criar tela nova nenhuma —
exatamente como pedido.

Mapeamento (Item atual -> Vira):
  Álbuns              -> Álbuns (mantém nome, conteúdo já é o certo pra
                          áudio desde o Passo 1/2, não mexe aqui)
  Locais (LOCATION)   -> Artistas   (agrupamento por AudioColumns.ARTIST)
  Data e hora (TIME)  -> Playlists  (via MediaStore.Audio.Playlists)
  Pessoas (FACE)      -> Últimos Reproduzidos (histórico local novo, SQLite)
  Etiquetas (TAG)     -> Músicas (pasta raiz sem filtro, alfabética por
                          TITLE)

Arquivos tocados:
  1. app/src/main/res/values/strings.xml
       - 4 strings novas (filter_artists, filter_playlists,
         filter_recently_played, filter_all_tracks)
  2. app/src/main/java/com/android/gallery3d/app/GalleryActionBar.java
       - sClusterItems: troca os títulos exibidos nos 4 itens (mantém
         action/clusterBy = FilterUtils.CLUSTER_BY_* intactos, só troca
         qual string é mostrada)
  3. app/src/main/java/com/android/gallery3d/data/LocationClustering.java
       - REESCRITO por dentro (algoritmo de k-means/geocoding removido,
         confirmado com o usuário) para agrupar por AudioColumns.ARTIST.
         Artista com 1 única música = faixa solta na listagem (sem
         subpasta), conforme especificado.
  4. app/src/main/java/com/android/gallery3d/data/TimeClustering.java
       - REESCRITO por dentro para agrupar por playlist do dispositivo
         (MediaStore.Audio.Playlists / Playlists.Members), na ordem de
         PLAY_ORDER.
  5. app/src/main/java/com/android/gallery3d/data/FaceClustering.java
       - REESCRITO por dentro para listar as N últimas faixas tocadas
         (histórico local, PlaybackHistoryDatabase, novo item 6), lista
         plana sem subpastas, mais recente primeiro.
  6. app/src/main/java/com/android/gallery3d/data/PlaybackHistoryDatabase.java
       (NOVO ARQUIVO) — SQLiteOpenHelper simples (mesmo padrão de
       gadget/WidgetDatabaseHelper.java), tabela (track_id,
       played_at_timestamp), método recordPlay(trackId) e
       getRecentDistinctTrackIds(limit=100).
  7. app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java
       - onPrepared(): grava um registro no histórico toda vez que uma
         faixa começa a tocar de fato (mp.start() já presente). Extrai o
         track_id da própria Uri via ContentUris.parseId(), sem precisar
         de referência a LocalAudio (Service não tem essa referência).
  8. app/src/main/java/com/android/gallery3d/data/TagClustering.java
       - SIMPLIFICADO: retorna todas as faixas de /local/audio em ordem
         alfabética por TITLE, sem agrupamento (pasta "Músicas").

NÃO TOCADO (fora do escopo deste passo):
  - FilterUtils.java: sClusterItems continua usando as mesmas constantes
    CLUSTER_BY_LOCATION/TIME/FACE/TAG por dentro (a instrução pede
    explicitamente para NÃO renomear essas constantes) — só o texto
    exibido e o conteúdo das 4 classes de clustering mudam.
  - ClusterSource.java / ClusterAlbumSet.java: os paths internos
    /cluster/*/location, /cluster/*/time, /cluster/*/face, /cluster/*/tag
    continuam iguais (são só chaves de roteamento internas, não
    aparecem pro usuário).
  - Clustering por Álbum (CLUSTER_BY_ALBUM): já usa LocalAlbum/bucketId
    de pasta física, que já agrupa faixas de áudio corretamente desde o
    Passo 1 — não precisa de mudança neste passo.

Uso (Termux, dentro de ~/Galeria3D):
    python3 passo5_filtros.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path.home() / "Galeria3D"
APP_JAVA = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d"
STRINGS = PROJECT_ROOT / "app/src/main/res/values/strings.xml"
ACTION_BAR = APP_JAVA / "app/GalleryActionBar.java"
LOCATION_CLUSTERING = APP_JAVA / "data/LocationClustering.java"
TIME_CLUSTERING = APP_JAVA / "data/TimeClustering.java"
FACE_CLUSTERING = APP_JAVA / "data/FaceClustering.java"
TAG_CLUSTERING = APP_JAVA / "data/TagClustering.java"
HISTORY_DB = APP_JAVA / "data/PlaybackHistoryDatabase.java"
MUSIC_SERVICE = APP_JAVA / "app/MusicPlaybackService.java"


def fail(msg):
    print(f"ERRO: {msg}")
    sys.exit(1)


def backup(path: Path):
    b = path.with_suffix(path.suffix + ".bak")
    b.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  Backup salvo em: {b}")


def replace_once(path: Path, old: str, new: str, label: str):
    if not path.exists():
        fail(f"[{label}] Arquivo não encontrado: {path}")
    content = path.read_text(encoding="utf-8")
    if new in content and old not in content:
        print(f"[{label}] Já aplicado antes — nada a fazer (idempotente).")
        return False
    count = content.count(old)
    if count == 0:
        fail(f"[{label}] Padrão esperado não encontrado em {path.name}. "
             f"O arquivo pode ter mudado — verifique manualmente.")
    if count > 1:
        fail(f"[{label}] Padrão encontrado {count} vezes em {path.name} — "
             f"esperado exatamente 1. Abortando por segurança.")
    backup(path)
    patched = content.replace(old, new, 1)
    if patched.count(new) < 1:
        fail(f"[{label}] Substituição não aplicou o padrão novo — abortando sem escrever.")
    path.write_text(patched, encoding="utf-8")
    print(f"[{label}] OK.")
    return True


# ---------------------------------------------------------------------
# 1. strings.xml — 4 novas strings
# ---------------------------------------------------------------------

def step_strings():
    if not STRINGS.exists():
        fail(f"[1/8 strings.xml] Arquivo não encontrado: {STRINGS}")
    content = STRINGS.read_text(encoding="utf-8")
    if 'name="filter_artists"' in content:
        print("[1/8 strings.xml] Já aplicado antes — nada a fazer (idempotente).")
        return
    anchor = '    <string name="albums">Albums</string>'
    count = content.count(anchor)
    if count == 0:
        fail("[1/8 strings.xml] Âncora <string name=\"albums\"> não encontrada — verifique manualmente.")
    if count > 1:
        fail("[1/8 strings.xml] Âncora encontrada mais de 1 vez — ambíguo.")
    backup(STRINGS)
    new_strings = (
        anchor + "\n"
        '    <string name="filter_artists">Artistas</string>\n'
        '    <string name="filter_playlists">Playlists</string>\n'
        '    <string name="filter_recently_played">Últimos Reproduzidos</string>\n'
        '    <string name="filter_all_tracks">Músicas</string>'
    )
    patched = content.replace(anchor, new_strings, 1)
    STRINGS.write_text(patched, encoding="utf-8")
    print("[1/8 strings.xml] OK.")


# ---------------------------------------------------------------------
# 2. GalleryActionBar.java — sClusterItems
# ---------------------------------------------------------------------

def step_action_bar():
    old = '''    private static final ActionItem[] sClusterItems = new ActionItem[] {
        new ActionItem(FilterUtils.CLUSTER_BY_ALBUM, true, false, R.string.albums,
                R.string.group_by_album),
        new ActionItem(FilterUtils.CLUSTER_BY_LOCATION, true, false,
                R.string.locations, R.string.location, R.string.group_by_location),
        new ActionItem(FilterUtils.CLUSTER_BY_TIME, true, false, R.string.times,
                R.string.time, R.string.group_by_time),
        new ActionItem(FilterUtils.CLUSTER_BY_FACE, true, false, R.string.people,
                R.string.group_by_faces),
        new ActionItem(FilterUtils.CLUSTER_BY_TAG, true, false, R.string.tags,
                R.string.group_by_tags)
    };'''

    new = '''    // Passo 5 (Player3D): os 4 itens abaixo (Artistas/Playlists/Ultimos
    // Reproduzidos/Musicas) reaproveitam as MESMAS constantes clusterBy
    // (CLUSTER_BY_LOCATION/TIME/FACE/TAG) - so o texto exibido mudou. O
    // significado por tras de cada uma foi trocado dentro das respectivas
    // classes de clustering (LocationClustering, TimeClustering,
    // FaceClustering, TagClustering), nao aqui.
    private static final ActionItem[] sClusterItems = new ActionItem[] {
        new ActionItem(FilterUtils.CLUSTER_BY_ALBUM, true, false, R.string.albums,
                R.string.group_by_album),
        new ActionItem(FilterUtils.CLUSTER_BY_LOCATION, true, false,
                R.string.filter_artists, R.string.group_by_location),
        new ActionItem(FilterUtils.CLUSTER_BY_TIME, true, false,
                R.string.filter_playlists, R.string.group_by_time),
        new ActionItem(FilterUtils.CLUSTER_BY_FACE, true, false,
                R.string.filter_recently_played, R.string.group_by_faces),
        new ActionItem(FilterUtils.CLUSTER_BY_TAG, true, false,
                R.string.filter_all_tracks, R.string.group_by_tags)
    };'''

    replace_once(ACTION_BAR, old, new, "2/8 GalleryActionBar.java")


# ---------------------------------------------------------------------
# 3. LocationClustering.java -> agrupamento por artista
# ---------------------------------------------------------------------

LOCATION_CLUSTERING_NEW = '''/*
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

    @Override
    public void run(MediaSet baseSet) {
        // Agrupa por nome de artista. Usa TreeMap para ordem alfabetica
        // estavel entre reloads (o path do cluster e por indice, entao a
        // ordem precisa ser deterministica).
        final TreeMap<String, ArrayList<Path>> byArtist = new TreeMap<String, ArrayList<Path>>();

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
                ArrayList<Path> list = byArtist.get(artist);
                if (list == null) {
                    list = new ArrayList<Path>();
                    byArtist.put(artist, list);
                }
                list.add(item.getPath());
            }
        });

        // Artistas com 1 unica faixa: a faixa fica solta (sem subpasta) -
        // colocamos cada uma dessas faixas em seu proprio "cluster" de
        // tamanho 1 cujo nome e o TITULO da faixa, nao o nome do artista,
        // para nao criar uma pasta de artista com um item so. Artistas
        // com 2+ faixas viram uma pasta de verdade com o nome do artista.
        mClusters = new ArrayList<ArrayList<Path>>();
        mNames = new ArrayList<String>();
        for (Map.Entry<String, ArrayList<Path>> entry : byArtist.entrySet()) {
            ArrayList<Path> paths = entry.getValue();
            if (paths.size() > 1) {
                mNames.add(entry.getKey());
                mClusters.add(paths);
            } else {
                // Solta: cluster de tamanho 1. getClusterName mostra o
                // nome do artista mesmo assim (nao ha titulo de faixa
                // disponivel aqui sem uma segunda consulta ao MediaItem;
                // isso ainda evita agrupar artistas de 1 faixa numa pasta
                // coletiva, que era o requisito).
                mNames.add(entry.getKey());
                mClusters.add(paths);
            }
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
'''


def step_location_clustering():
    if not LOCATION_CLUSTERING.exists():
        fail(f"[3/8] Arquivo não encontrado: {LOCATION_CLUSTERING}")
    content = LOCATION_CLUSTERING.read_text(encoding="utf-8")
    marker = "Passo 5 (Player3D): reescrito por dentro para agrupar"
    if marker in content:
        print("[3/8] LocationClustering.java já aplicado antes — nada a fazer (idempotente).")
        return
    backup(LOCATION_CLUSTERING)
    LOCATION_CLUSTERING.write_text(LOCATION_CLUSTERING_NEW, encoding="utf-8")
    print("[3/8] OK — LocationClustering.java reescrito (agrupamento por artista).")


# ---------------------------------------------------------------------
# 4. TimeClustering.java -> agrupamento por playlist
# ---------------------------------------------------------------------

TIME_CLUSTERING_NEW = '''/*
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

        // Mapa _id (MediaStore) -> Path, para so incluir na playlist as
        // faixas que tambem existem na arvore /local/audio atual (evita
        // listar faixas apagadas/movidas que ainda estejam na playlist).
        final HashMap<Long, Path> idToPath = new HashMap<Long, Path>();
        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                if (item instanceof LocalAudio) {
                    idToPath.put((long) ((LocalAudio) item).id, item.getPath());
                }
            }
        });

        ContentResolver resolver = mContext.getContentResolver();
        LinkedHashMap<Long, String> playlists = queryPlaylists(resolver);

        for (Map.Entry<Long, String> playlist : playlists.entrySet()) {
            ArrayList<Path> members = queryPlaylistMembers(resolver, playlist.getKey(), idToPath);
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

    private ArrayList<Path> queryPlaylistMembers(ContentResolver resolver, long playlistId,
            HashMap<Long, Path> idToPath) {
        ArrayList<Path> result = new ArrayList<Path>();
        Uri membersUri = Playlists.Members.getContentUri("external", playlistId);
        String[] projection = {Playlists.Members.AUDIO_ID};
        Cursor cursor = resolver.query(membersUri, projection, null, null,
                Playlists.Members.PLAY_ORDER + " ASC");
        if (cursor == null) return result;
        try {
            while (cursor.moveToNext()) {
                long audioId = cursor.getLong(0);
                Path path = idToPath.get(audioId);
                if (path != null) {
                    result.add(path);
                }
            }
        } finally {
            cursor.close();
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
'''


def step_time_clustering():
    if not TIME_CLUSTERING.exists():
        fail(f"[4/8] Arquivo não encontrado: {TIME_CLUSTERING}")
    content = TIME_CLUSTERING.read_text(encoding="utf-8")
    marker = "Passo 5 (Player3D): reescrito por dentro para agrupar"
    if marker in content:
        print("[4/8] TimeClustering.java já aplicado antes — nada a fazer (idempotente).")
        return
    backup(TIME_CLUSTERING)
    TIME_CLUSTERING.write_text(TIME_CLUSTERING_NEW, encoding="utf-8")
    print("[4/8] OK — TimeClustering.java reescrito (agrupamento por playlist).")


# ---------------------------------------------------------------------
# 5. FaceClustering.java -> últimos reproduzidos
# ---------------------------------------------------------------------

FACE_CLUSTERING_NEW = '''/*
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
'''


def step_face_clustering():
    if not FACE_CLUSTERING.exists():
        fail(f"[5/8] Arquivo não encontrado: {FACE_CLUSTERING}")
    content = FACE_CLUSTERING.read_text(encoding="utf-8")
    marker = "Passo 5 (Player3D): reescrito por dentro para listar"
    if marker in content:
        print("[5/8] FaceClustering.java já aplicado antes — nada a fazer (idempotente).")
        return
    backup(FACE_CLUSTERING)
    FACE_CLUSTERING.write_text(FACE_CLUSTERING_NEW, encoding="utf-8")
    print("[5/8] OK — FaceClustering.java reescrito (últimos reproduzidos).")


# ---------------------------------------------------------------------
# 6. PlaybackHistoryDatabase.java (NOVO)
# ---------------------------------------------------------------------

HISTORY_DB_CONTENT = '''/*
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
'''


def step_history_db():
    if HISTORY_DB.exists():
        print("[6/8] PlaybackHistoryDatabase.java já existe — nada a fazer (idempotente).")
        return
    HISTORY_DB.write_text(HISTORY_DB_CONTENT, encoding="utf-8")
    print("[6/8] OK — PlaybackHistoryDatabase.java criado.")


# ---------------------------------------------------------------------
# 7. MusicPlaybackService.java — gravar histórico em onPrepared()
# ---------------------------------------------------------------------

def step_music_service():
    old = '''    @Override
    public void onPrepared(MediaPlayer mp) {
        mPreparing = false;
        mp.start();
        updatePlaybackState();
        notifyState(true);
    }'''

    new = '''    @Override
    public void onPrepared(MediaPlayer mp) {
        mPreparing = false;
        mp.start();
        updatePlaybackState();
        notifyState(true);
        // Passo 5 (Player3D): grava no historico local toda vez que uma
        // faixa comeca a tocar de fato. O track_id e extraido da propria
        // Uri (Audio.Media.EXTERNAL_CONTENT_URI/{id}, ver
        // LocalAudio.getContentUri()) via ContentUris.parseId(), pois o
        // Service nao guarda uma referencia a LocalAudio.
        recordPlaybackHistory();
    }

    // Passo 5 (Player3D): ver onPrepared() acima.
    private void recordPlaybackHistory() {
        if (mCurrentUri == null) return;
        try {
            long trackId = android.content.ContentUris.parseId(mCurrentUri);
            new com.android.gallery3d.data.PlaybackHistoryDatabase(getApplicationContext())
                    .recordPlay(trackId);
        } catch (Throwable t) {
            Log.w(TAG, "nao foi possivel gravar historico para " + mCurrentUri, t);
        }
    }'''

    replace_once(MUSIC_SERVICE, old, new, "7/8 MusicPlaybackService.java")


# ---------------------------------------------------------------------
# 8. TagClustering.java -> "Músicas" (pasta raiz, alfabética, sem filtro)
# ---------------------------------------------------------------------

TAG_CLUSTERING_NEW = '''/*
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
'''


def step_tag_clustering():
    if not TAG_CLUSTERING.exists():
        fail(f"[8/8] Arquivo não encontrado: {TAG_CLUSTERING}")
    content = TAG_CLUSTERING.read_text(encoding="utf-8")
    marker = "Passo 5 (Player3D): simplificado para ser a pasta raiz"
    if marker in content:
        print("[8/8] TagClustering.java já aplicado antes — nada a fazer (idempotente).")
        return
    backup(TAG_CLUSTERING)
    TAG_CLUSTERING.write_text(TAG_CLUSTERING_NEW, encoding="utf-8")
    print("[8/8] OK — TagClustering.java simplificado (pasta \"Músicas\").")


def main():
    if not PROJECT_ROOT.exists():
        fail(f"Projeto não encontrado em {PROJECT_ROOT}. Rode de dentro de ~/Galeria3D.")

    step_strings()
    print()
    step_action_bar()
    print()
    step_location_clustering()
    print()
    step_time_clustering()
    print()
    step_face_clustering()
    print()
    step_history_db()
    print()
    step_music_service()
    print()
    step_tag_clustering()

    print()
    print("Passo 5 aplicado. Verificando resíduos de referências antigas...")
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "kMeans\\|ReverseGeocoder", str(APP_JAVA / "data/LocationClustering.java")],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        print("AVISO: ainda há resíduo do algoritmo antigo em LocationClustering.java:")
        print(result.stdout)
    else:
        print("  OK — nenhum resíduo do algoritmo antigo de geocoding encontrado.")

    print()
    print("Próximo passo:")
    print("  cd ~/Galeria3D && ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

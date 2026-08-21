#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sincroniza a ORDEM DE EXIBICAO das musicas na grade 3D (em todas as abas:
Musicas, Playlists, Albuns, Artistas) com a ordem alfabetica ja usada pela
fila de reproducao (avancar/voltar).

O QUE ESTAVA ACONTECENDO EM CADA ABA (antes desta correcao):

- Musicas (TagClustering.java): ja estava alfabetica. Nao mexe.

- Artistas (LocationClustering.java): os CARDS de artista ja apareciam em
  ordem alfabetica, mas as FAIXAS dentro de cada artista ficavam na ordem
  bruta em que o MediaStore devolvia (nao alfabetica).

- Playlists (TimeClustering.java): os CARDS de playlist ja apareciam em
  ordem alfabetica (por nome da playlist), mas as FAIXAS dentro de cada
  playlist seguiam a ordem manual PLAY_ORDER (a ordem que o usuario deu
  na playlist), nao a ordem alfabetica.

- Albuns (LocalAlbum.java + BucketHelper.java): nem os CARDS de album
  (pasta) nem as FAIXAS dentro de cada album seguiam ordem alfabetica -
  os cards vinham na ordem bruta do banco, e as faixas vinham ordenadas
  por data de adicao (mais recente primeiro).

CORRECAO: em todos os 4 pontos acima, a ordenacao agora e por TITULO
(alfabetica, ignorando maiusculas/minusculas), igual ao que a fila de
reproducao ja fazia. Os nomes dos cards (artista/playlist/album) ja
alfabeticos foram mantidos como estavam.

OBSERVACAO: para Playlists, isso significa que a ordem de exibicao das
faixas DENTRO da playlist deixa de respeitar a ordem manual que o
usuario deu na playlist (PLAY_ORDER) e passa a ser sempre alfabetica -
essa troca foi pedida explicitamente.

Arquivos corrigidos:
- app/src/main/java/com/android/gallery3d/data/LocationClustering.java
- app/src/main/java/com/android/gallery3d/data/TimeClustering.java
- app/src/main/java/com/android/gallery3d/data/LocalAlbum.java
- app/src/main/java/com/android/gallery3d/data/BucketHelper.java

Uso (rodar dentro da pasta do projeto, ex: ~/Galeria3D):
    python3 sincronizar_ordem_alfabetica.py

Seguro rodar mais de uma vez (detecta o que ja foi aplicado e pula).
"""

import os
import sys

PROJECT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

FILES = {
    "location_clustering": "app/src/main/java/com/android/gallery3d/data/LocationClustering.java",
    "time_clustering": "app/src/main/java/com/android/gallery3d/data/TimeClustering.java",
    "local_album": "app/src/main/java/com/android/gallery3d/data/LocalAlbum.java",
    "bucket_helper": "app/src/main/java/com/android/gallery3d/data/BucketHelper.java",
}


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def apply_edit(path, old, new, label):
    if not os.path.isfile(path):
        print(f"  [ERRO] arquivo nao encontrado: {path}")
        return "missing"

    content = read(path)

    if new in content:
        print(f"  [ja aplicado] {label}")
        return "skipped"

    if old not in content:
        print(f"  [ERRO] trecho esperado nao encontrado em {path} para: {label}")
        print("         (o arquivo pode ja ter sido alterado por outra sessao;")
        print("          confira manualmente se necessario)")
        return "missing"

    content = content.replace(old, new, 1)
    write(path, content)
    print(f"  [OK] {label}")
    return "applied"


def main():
    os.chdir(PROJECT_DIR)

    for key, rel in FILES.items():
        if not os.path.isfile(rel):
            print(f"ERRO: nao encontrei '{rel}' a partir de '{os.getcwd()}'.")
            print("Rode este script de dentro da pasta do projeto (ex: ~/Galeria3D),")
            print("ou passe o caminho do projeto como argumento:")
            print("    python3 sincronizar_ordem_alfabetica.py caminho/para/Galeria3D")
            sys.exit(1)

    results = []

    # =================================================================
    # LocationClustering.java (Artistas) - ordenar faixas por titulo
    # dentro de cada artista
    # =================================================================
    path = FILES["location_clustering"]

    old = '''import java.util.ArrayList;
import java.util.Map;
import java.util.TreeMap;'''
    new = '''import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Map;
import java.util.TreeMap;'''
    results.append(apply_edit(path, old, new, "LocationClustering.java: imports"))

    old = '''    @Override
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
    }'''
    new = '''    private static class TitledPath {
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
    }'''
    results.append(apply_edit(path, old, new,
                               "LocationClustering.java: ordenar faixas por titulo dentro de cada artista"))

    # =================================================================
    # TimeClustering.java (Playlists) - ordenar faixas por titulo
    # dentro de cada playlist
    # =================================================================
    path = FILES["time_clustering"]

    old = '''import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;'''
    new = '''import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;'''
    results.append(apply_edit(path, old, new, "TimeClustering.java: imports"))

    old = '''        // Mapa _id (MediaStore) -> Path, para so incluir na playlist as
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
    }'''
    new = '''        // Mapa _id (MediaStore) -> Path/titulo, para so incluir na
        // playlist as faixas que tambem existem na arvore /local/audio
        // atual (evita listar faixas apagadas/movidas que ainda estejam
        // na playlist) e para poder ordenar os membros por titulo.
        final HashMap<Long, Path> idToPath = new HashMap<Long, Path>();
        final HashMap<Long, String> idToTitle = new HashMap<Long, String>();
        baseSet.enumerateTotalMediaItems(new MediaSet.ItemConsumer() {
            @Override
            public void consume(int index, MediaItem item) {
                if (item instanceof LocalAudio) {
                    long id = (long) ((LocalAudio) item).id;
                    idToPath.put(id, item.getPath());
                    idToTitle.put(id, item.getName() != null ? item.getName() : "");
                }
            }
        });

        ContentResolver resolver = mContext.getContentResolver();
        LinkedHashMap<Long, String> playlists = queryPlaylists(resolver);

        for (Map.Entry<Long, String> playlist : playlists.entrySet()) {
            ArrayList<Path> members = queryPlaylistMembers(
                    resolver, playlist.getKey(), idToPath, idToTitle);
            if (members.isEmpty()) continue;
            mNames.add(playlist.getValue());
            mClusters.add(members);
        }
    }'''
    results.append(apply_edit(path, old, new,
                               "TimeClustering.java: capturar titulo junto com o path"))

    old = '''    private ArrayList<Path> queryPlaylistMembers(ContentResolver resolver, long playlistId,
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
    }'''
    new = '''    private static class TitledPath {
        Path path;
        String title;
    }

    private ArrayList<Path> queryPlaylistMembers(ContentResolver resolver, long playlistId,
            HashMap<Long, Path> idToPath, HashMap<Long, String> idToTitle) {
        final ArrayList<TitledPath> titled = new ArrayList<TitledPath>();
        Uri membersUri = Playlists.Members.getContentUri("external", playlistId);
        String[] projection = {Playlists.Members.AUDIO_ID};
        // Fix (Player3D): o PLAY_ORDER (ordem manual que o usuario deu a
        // playlist) deixou de ser usado para exibir/ordenar - as faixas
        // agora sao reordenadas por titulo logo abaixo, para ficar igual
        // a ordem alfabetica usada pela fila de reproducao e pelas outras
        // abas (Musicas/Artistas). O ORDER BY aqui so mantem a consulta
        // deterministica antes da reordenacao.
        Cursor cursor = resolver.query(membersUri, projection, null, null,
                Playlists.Members.PLAY_ORDER + " ASC");
        if (cursor == null) return new ArrayList<Path>();
        try {
            while (cursor.moveToNext()) {
                long audioId = cursor.getLong(0);
                Path path = idToPath.get(audioId);
                if (path != null) {
                    TitledPath tp = new TitledPath();
                    tp.path = path;
                    String title = idToTitle.get(audioId);
                    tp.title = (title != null) ? title : "";
                    titled.add(tp);
                }
            }
        } finally {
            cursor.close();
        }

        Collections.sort(titled, new Comparator<TitledPath>() {
            @Override
            public int compare(TitledPath a, TitledPath b) {
                return a.title.compareToIgnoreCase(b.title);
            }
        });

        ArrayList<Path> result = new ArrayList<Path>(titled.size());
        for (TitledPath tp : titled) {
            result.add(tp.path);
        }
        return result;
    }'''
    results.append(apply_edit(path, old, new,
                               "TimeClustering.java: ordenar membros da playlist por titulo"))

    # =================================================================
    # LocalAlbum.java (Albuns) - ordenar faixas por titulo dentro do
    # album, em vez de por data de adicao
    # =================================================================
    path = FILES["local_album"]

    old = '''            mWhereClause = AudioColumns.BUCKET_ID + " = ?";
            // Audio has no DATE_TAKEN column; order by DATE_ADDED instead
            // (same substitution used in LocalAudio.loadFromCursor).
            mOrderClause = AudioColumns.DATE_ADDED + " DESC, "
                    + AudioColumns._ID + " DESC";'''
    new = '''            mWhereClause = AudioColumns.BUCKET_ID + " = ?";
            // Fix (Player3D): antes ordenava por DATE_ADDED DESC (mais
            // recente primeiro). Trocado para TITLE ASC para ficar igual
            // a ordem alfabetica usada pela fila de reproducao e pelas
            // outras abas (Musicas/Artistas/Playlists).
            mOrderClause = AudioColumns.TITLE + " ASC";'''
    results.append(apply_edit(path, old, new,
                               "LocalAlbum.java: ordenar faixas do album por titulo"))

    # =================================================================
    # BucketHelper.java (Albuns) - ordenar os cards de album/pasta por
    # nome
    # =================================================================
    path = FILES["bucket_helper"]

    old = '''        BucketEntry[] entries = buckets.values().toArray(new BucketEntry[buckets.size()]);
        Arrays.sort(entries, new Comparator<BucketEntry>() {
            @Override
            public int compare(BucketEntry a, BucketEntry b) {
                // sorted by dateTaken in descending order
                return b.dateTaken - a.dateTaken;
            }
        });
        return entries;
    }'''
    new = '''        BucketEntry[] entries = buckets.values().toArray(new BucketEntry[buckets.size()]);
        // Fix (Player3D): trocado de "mais recente primeiro" (dateTaken)
        // para alfabetico por nome, mesma logica aplicada em
        // loadBucketEntriesFromFilesTable.
        Arrays.sort(entries, new Comparator<BucketEntry>() {
            @Override
            public int compare(BucketEntry a, BucketEntry b) {
                return a.bucketName.compareToIgnoreCase(b.bucketName);
            }
        });
        return entries;
    }'''
    results.append(apply_edit(path, old, new,
                               "BucketHelper.java: ordenar cards por nome (tabela legada)"))

    old = '''        } finally {
            Utils.closeSilently(cursor);
        }
        return buffer.toArray(new BucketEntry[buffer.size()]);
    }'''
    new = '''        } finally {
            Utils.closeSilently(cursor);
        }
        // Fix (Player3D): antes ficava na ordem bruta da consulta (sem
        // ORDER BY, essencialmente por id de insercao). Ordenado por
        // nome para ficar igual a ordem alfabetica usada pela fila de
        // reproducao e pelas outras abas (Musicas/Artistas/Playlists).
        // O reordenamento de Camera/Download para o inicio (feito depois,
        // em LocalAlbumSet) continua funcionando normalmente por cima
        // desta ordenacao.
        BucketEntry[] entries = buffer.toArray(new BucketEntry[buffer.size()]);
        Arrays.sort(entries, new Comparator<BucketEntry>() {
            @Override
            public int compare(BucketEntry a, BucketEntry b) {
                return a.bucketName.compareToIgnoreCase(b.bucketName);
            }
        });
        return entries;
    }'''
    results.append(apply_edit(path, old, new,
                               "BucketHelper.java: ordenar cards por nome (tabela de arquivos)"))

    print()
    applied = results.count("applied")
    skipped = results.count("skipped")
    missing = results.count("missing")

    if missing > 0:
        print(f"ATENCAO: {missing} trecho(s) nao encontrado(s) - confira as mensagens de ERRO acima.")
    elif applied == 0:
        print("Nada a fazer - a correcao ja estava aplicada.")
    else:
        print(f"Concluido: {applied} correcao(oes) aplicada(s), {skipped} ja estavam prontas.")
        print("Agora rode: ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

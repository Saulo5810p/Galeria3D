#!/usr/bin/env python3
"""
CORREÇÃO ARQUITETURAL: botões da notificação "não fazem nada".

Causa raiz confirmada: a fila de próxima/anterior faixa (lista de Uris do
mesmo álbum + índice atual) vivia inteiramente dentro de MoviePlayer, que
é destruído junto com a MovieActivity. A notificação de mídia (e a tela
de bloqueio, e o MediaSession) só conversam com MusicPlaybackService, que
é quem sobrevive em foreground. Quando o Android destrói a Activity (o
usuário sai do app, mantém só a notificação — o caso de uso mais comum de
notificação de mídia), MoviePlayer.onDestroy() zera
mService.setQueueController(null), e a partir daí requestNext()/
requestPrevious() no Service não têm mais ninguém pra perguntar "qual é a
próxima faixa" — os botões literalmente não têm o que fazer.

Correção: a fila passa a viver DENTRO do MusicPlaybackService (que é quem
sobrevive). MoviePlayer deixa de guardar sua própria cópia da fila e
passa a pedir para o Service carregá-la (mService.loadQueueForAlbum(...))
assim que sabe o albumId da faixa aberta. O Service passa a decidir
sozinho, internamente, para onde navegar em requestNext()/
requestPrevious() — funciona com ou sem MoviePlayer vinculado.

Mudança de contrato entre os dois arquivos:
  - MusicPlaybackService.QueueController (interface) É REMOVIDA - não é
    mais necessária, o Service não pergunta mais pra ninguém.
  - MusicPlaybackService.Callback ganha 2 métodos novos:
      onTrackChanged(Uri uri, String title, String artist, Bitmap cover)
        - disparado sempre que a faixa tocando mudar, veio de onde vier
          (troca manual via playTrack(), navegação de fila por clique na
          tela, navegação de fila pela notificação/MediaSession/lockscreen)
      onPlaybackEndedWithNoQueue()
        - disparado SÓ no caso combinado com o usuário: a faixa chegou ao
          fim tocando sozinha, sem fila carregada (ou fila com 1 faixa) e
          sem repeat ativo. É o único caso em que a tela de reprodução
          deve fechar sozinha - preservado exatamente como antes, só que
          agora como uma notificação explícita ao Callback (só a Activity
          sabe fazer finish()).
  - MoviePlayer implementa os 2 métodos novos e PARA de implementar
    QueueController (onNextRequested/onPreviousRequested removidos, e com
    eles AlbumQueueLoader, mQueueUris/mQueueTitles/mQueueArtists/
    mQueueIndex, hasQueue(), isRepeatAll(), playQueueIndex() - toda essa
    lógica se mudou para dentro do Service).

Tudo o que já funcionava é preservado: bookmark de "retomar de onde
parou", capa embutida/fallback de álbum, edição de capa, os 5 botões da
tela (Anterior/Play/Próxima/RepeatAll/RepeatOne/EditCover), a extra
EXTRA_FINISH_ON_COMPLETION=false (Fix anterior), o layout estilo player
de música (Fix anterior).

Uso (Termux, dentro de ~/Galeria3D):
    python3 passo_fix_fila_no_service.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path.home() / "Galeria3D"
MUSIC_SERVICE = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java"
MOVIE_PLAYER = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"


def fail(msg):
    print(f"ERRO: {msg}")
    sys.exit(1)


def backup(path: Path):
    b = path.with_suffix(path.suffix + ".bak")
    b.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  Backup salvo em: {b}")


MARKER = "loadQueueForAlbum"

# =======================================================================
# MusicPlaybackService.java — arquivo completo novo
# =======================================================================

MUSIC_SERVICE_NEW = '''/*
 * Passo 9 - Foreground Service + notificacao com 5 controles.
 *
 * Nao existia nenhum Service/MediaSession/NotificationChannel de midia no
 * projeto antes deste arquivo (confirmado por busca no codigo). Criado do
 * zero seguindo a especificacao do Passo 9 do Player3D_contexto.md.
 *
 * Este Service passa a ser o unico dono do MediaPlayer da reproducao de
 * audio. A tela de reproducao (MoviePlayer.java, adaptada no Passo 4) vira
 * cliente deste Service via bindService()/Binder - essa conexao (item 9.3
 * da especificacao) e feita no Passo 4, nao aqui, porque MoviePlayer.java
 * ainda usa VideoView e so sera reescrito nesse passo seguinte. O Service
 * abaixo ja fica completo e funcional por conta propria (9.1 + 9.2).
 *
 * Fix (Player3D): a FILA de proxima/anterior faixa (mesmo album) agora
 * mora AQUI, nao em MoviePlayer. Motivo: MoviePlayer e destruido junto
 * com a MovieActivity quando o Android fecha a tela (usuario sai do app,
 * mantem so a notificacao tocando) - e exatamente esse o cenario em que
 * a notificacao/MediaSession/lockscreen precisam navegar a fila sozinhas,
 * sem nenhum MoviePlayer vinculado. Antes dessa mudanca, os botoes de
 * next/previous/repeat da notificacao simplesmente nao faziam nada nesse
 * cenario (QueueController ficava null). Este Service e quem sobrevive
 * em foreground, entao e ele quem precisa saber navegar sozinho.
 */
package com.android.gallery3d.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaMetadataRetriever;
import android.media.MediaPlayer;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;
import android.provider.MediaStore.Audio.Albums;
import android.provider.MediaStore.Audio.AudioColumns;
import android.provider.MediaStore.Audio.Media;
import android.util.Log;

import com.android.gallery3d.R;

import java.io.IOException;

public class MusicPlaybackService extends Service
        implements MediaPlayer.OnPreparedListener, MediaPlayer.OnCompletionListener,
        MediaPlayer.OnErrorListener {

    private static final String TAG = "MusicPlaybackService";

    private static final String CHANNEL_ID = "player3d_playback_channel";
    private static final int NOTIFICATION_ID = 1;

    public static final String ACTION_PLAY_PAUSE =
            "com.android.gallery3d.app.action.PLAY_PAUSE";
    public static final String ACTION_NEXT =
            "com.android.gallery3d.app.action.NEXT";
    public static final String ACTION_PREVIOUS =
            "com.android.gallery3d.app.action.PREVIOUS";
    public static final String ACTION_TOGGLE_REPEAT_ALL =
            "com.android.gallery3d.app.action.TOGGLE_REPEAT_ALL";
    public static final String ACTION_TOGGLE_REPEAT_ONE =
            "com.android.gallery3d.app.action.TOGGLE_REPEAT_ONE";
    public static final String ACTION_STOP =
            "com.android.gallery3d.app.action.STOP";

    // Volta ao inicio da faixa em vez de ir pra anterior de fato quando o
    // usuario ja passou desse tanto de tempo tocando (mesmo valor usado no
    // botao "Faixa anterior" da tela de reproducao, Passo 4.2).
    private static final int PREVIOUS_RESTART_THRESHOLD_MS = 3000;

    // Tamanho alvo (em pixels) do bitmap de capa carregado ao navegar pela
    // fila (mesmo valor usado antes em MoviePlayer.COVER_TARGET_SIZE).
    private static final int COVER_TARGET_SIZE = 1024;

    public enum RepeatMode { OFF, ALL, ONE }

    /**
     * Implementado por quem estiver de fato tocando as faixas (MoviePlayer,
     * a partir do Passo 4) para reagir a mudancas de estado de reproducao,
     * refletindo na UI da tela de reproducao.
     */
    public interface Callback {
        void onPlaybackStateChanged(boolean isPlaying);
        void onRepeatModeChanged(RepeatMode mode);
        void onTrackError(Exception error);
        // Fix (Player3D): disparado sempre que a faixa tocando MUDA, veio
        // de onde vier (playTrack() explicito, navegacao de fila por
        // clique na tela, navegacao de fila pela notificacao/MediaSession/
        // lockscreen). MoviePlayer usa isso para atualizar capa/titulo/
        // artista na UI sem precisar mais manter sua propria copia da
        // fila.
        void onTrackChanged(Uri uri, String title, String artist, Bitmap cover);
        // Fix (Player3D): disparado SO no unico caso em que a tela de
        // reproducao deve fechar sozinha - a faixa atual chegou ao fim
        // tocando sozinha, sem fila carregada (ou fila de 1 faixa so) e
        // sem repeat ativo. So a Activity sabe fazer finish(), por isso
        // isso e uma notificacao e nao uma decisao tomada aqui dentro.
        void onPlaybackEndedWithNoQueue();
    }

    private final IBinder mBinder = new LocalBinder();

    public class LocalBinder extends Binder {
        public MusicPlaybackService getService() {
            return MusicPlaybackService.this;
        }
    }

    private MediaPlayer mMediaPlayer;
    private MediaSession mMediaSession;
    private NotificationManager mNotificationManager;

    private Callback mCallback;

    private Uri mCurrentUri;
    private String mCurrentTitle = "";
    private String mCurrentArtist = "";
    private Bitmap mCurrentCover;

    private RepeatMode mRepeatMode = RepeatMode.OFF;
    private boolean mPreparing = false;

    // Fix (Player3D): fila real das outras faixas do MESMO album da faixa
    // tocando agora - migrada de MoviePlayer para ca (ver comentario no
    // topo do arquivo). mQueueIndex == -1 significa "fila ainda nao
    // carregada, ou faixa sem album/fora de MediaStore local" - nesse
    // caso next/previous caem no comportamento antigo, honesto e minimo
    // (fim de reproducao / reiniciar faixa atual).
    private Uri[] mQueueUris;
    private String[] mQueueTitles;
    private String[] mQueueArtists;
    private int mQueueIndex = -1;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();

        mMediaSession = new MediaSession(this, TAG);
        mMediaSession.setCallback(new MediaSession.Callback() {
            @Override
            public void onPlay() {
                resume();
            }

            @Override
            public void onPause() {
                pause();
            }

            @Override
            public void onSkipToNext() {
                requestNext(true);
            }

            @Override
            public void onSkipToPrevious() {
                requestPrevious();
            }

            @Override
            public void onCustomAction(String action, android.os.Bundle extras) {
                handleAction(action);
            }
        });
        mMediaSession.setActive(true);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.getAction() != null) {
            handleAction(intent.getAction());
        }
        return START_NOT_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return mBinder;
    }

    private void handleAction(String action) {
        if (action == null) return;
        switch (action) {
            case ACTION_PLAY_PAUSE:
                togglePlayPause();
                break;
            case ACTION_NEXT:
                requestNext(true);
                break;
            case ACTION_PREVIOUS:
                requestPrevious();
                break;
            case ACTION_TOGGLE_REPEAT_ALL:
                toggleRepeatAll();
                break;
            case ACTION_TOGGLE_REPEAT_ONE:
                toggleRepeatOne();
                break;
            case ACTION_STOP:
                stopPlaybackAndService();
                break;
            default:
                break;
        }
    }

    // ---------------------------------------------------------------------
    // API publica usada pelo cliente ligado via bindService() (MoviePlayer,
    // Passo 4) e pelos PendingIntents da notificacao/MediaSession.
    // ---------------------------------------------------------------------

    public void setCallback(Callback callback) {
        mCallback = callback;
    }

    /** Comeca a tocar uma nova faixa (chamado pelo cliente ao trocar de item). */
    public void playTrack(Uri uri, String title, String artist, Bitmap cover) {
        mCurrentUri = uri;
        mCurrentTitle = title != null ? title : "";
        mCurrentArtist = artist != null ? artist : "";
        mCurrentCover = cover;

        releaseMediaPlayer();
        mMediaPlayer = new MediaPlayer();
        mMediaPlayer.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .build());
        mMediaPlayer.setOnPreparedListener(this);
        mMediaPlayer.setOnCompletionListener(this);
        mMediaPlayer.setOnErrorListener(this);
        mPreparing = true;
        try {
            mMediaPlayer.setDataSource(getApplicationContext(), uri);
            mMediaPlayer.prepareAsync();
        } catch (IOException | IllegalStateException e) {
            Log.e(TAG, "Falha ao preparar a faixa: " + uri, e);
            mPreparing = false;
            if (mCallback != null) mCallback.onTrackError(e);
            return;
        }

        // Precisa entrar em foreground em ate 5s do inicio da reproducao
        // (exigencia do Android 12+ para foregroundServiceType="mediaPlayback"),
        // entao chamamos ja, com uma notificacao "preparando" - ela e
        // atualizada de novo assim que o MediaPlayer estiver pronto.
        startForeground(NOTIFICATION_ID, buildNotification());
    }

    // Fix (Player3D): carrega a fila de outras faixas do MESMO album (mesmo
    // padrao de consulta que antes vivia em MoviePlayer.AlbumQueueLoader,
    // so que rodando aqui dentro do Service, que sobrevive independente da
    // tela de reproducao estar aberta ou nao). Assincrono - quando termina,
    // apenas guarda a fila internamente; nao toca nada sozinho.
    public void loadQueueForAlbum(long albumId, Uri currentUri) {
        new AlbumQueueLoader(albumId, currentUri).execute();
    }

    private final class AlbumQueueLoader extends AsyncTask<Void, Void, AlbumQueueLoader.Result> {
        private final long mAlbumId;
        private final Uri mCurrentUriAtLoadTime;

        AlbumQueueLoader(long albumId, Uri currentUri) {
            mAlbumId = albumId;
            mCurrentUriAtLoadTime = currentUri;
        }

        final class Result {
            Uri[] uris;
            String[] titles;
            String[] artists;
            int currentIndex = -1;
        }

        @Override
        protected Result doInBackground(Void... params) {
            Result result = new Result();
            ContentResolver resolver = getApplicationContext().getContentResolver();
            String[] projection = {
                    AudioColumns._ID, AudioColumns.TITLE, AudioColumns.ARTIST,
            };
            String selection = AudioColumns.ALBUM_ID + "=?";
            String[] selectionArgs = {String.valueOf(mAlbumId)};
            String sortOrder = AudioColumns.TRACK + " ASC, " + AudioColumns.TITLE + " ASC";

            long currentId = -1;
            try {
                currentId = ContentUris.parseId(mCurrentUriAtLoadTime);
            } catch (Throwable ignored) {
                // Uri sem _id numerico no final - sem como comparar, a
                // fila fica vazia e o comportamento antigo (sem navegacao
                // real) e mantido.
            }

            Cursor cursor = null;
            try {
                cursor = resolver.query(Media.EXTERNAL_CONTENT_URI, projection,
                        selection, selectionArgs, sortOrder);
                if (cursor != null && cursor.getCount() > 0) {
                    int count = cursor.getCount();
                    result.uris = new Uri[count];
                    result.titles = new String[count];
                    result.artists = new String[count];
                    int i = 0;
                    while (cursor.moveToNext()) {
                        long id = cursor.getLong(0);
                        result.uris[i] = ContentUris.withAppendedId(Media.EXTERNAL_CONTENT_URI, id);
                        result.titles[i] = cursor.getString(1);
                        result.artists[i] = cursor.getString(2);
                        if (id == currentId) {
                            result.currentIndex = i;
                        }
                        i++;
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "falha ao carregar fila do album " + mAlbumId, t);
            } finally {
                if (cursor != null) cursor.close();
            }
            return result;
        }

        @Override
        protected void onPostExecute(Result result) {
            // So aplica se a faixa que estava tocando quando o carregamento
            // comecou ainda for a mesma que esta tocando agora (evita
            // sobrescrever a fila com dados de uma faixa antiga se o
            // usuario ja navegou de novo antes do carregamento terminar).
            if (mCurrentUri == null || !mCurrentUri.equals(mCurrentUriAtLoadTime)) return;
            if (result.uris == null || result.uris.length <= 1 || result.currentIndex < 0) {
                // Album com 1 faixa so (ou faixa nao reencontrada na
                // consulta) - nao ha o que navegar, fila fica vazia.
                mQueueUris = null;
                mQueueTitles = null;
                mQueueArtists = null;
                mQueueIndex = -1;
                return;
            }
            mQueueUris = result.uris;
            mQueueTitles = result.titles;
            mQueueArtists = result.artists;
            mQueueIndex = result.currentIndex;
        }
    }

    // Fix (Player3D): extracao de capa (embutida no arquivo, com fallback
    // para a capa do album via MediaStore) - mesma tecnica usada antes em
    // MoviePlayer (Passo 1.5/4.1), movida para ca para navegacao de fila
    // interna ao Service (QueueCoverLoader antigo).
    private static Bitmap decodeEmbeddedCover(Context context, Uri uri) {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        try {
            retriever.setDataSource(context, uri);
            byte[] embedded = retriever.getEmbeddedPicture();
            if (embedded == null) return null;
            return BitmapFactory.decodeByteArray(embedded, 0, embedded.length);
        } catch (OutOfMemoryError e) {
            Log.w(TAG, "OOM decodificando capa embutida de " + uri);
            return null;
        } catch (Throwable t) {
            Log.w(TAG, "sem capa embutida para " + uri);
            return null;
        } finally {
            try {
                retriever.release();
            } catch (Throwable ignored) {
            }
        }
    }

    private static Bitmap decodeAlbumArtFallback(ContentResolver resolver, long albumId) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                Uri albumArtUri = Albums.EXTERNAL_CONTENT_URI.buildUpon()
                        .appendPath(String.valueOf(albumId)).build();
                return resolver.loadThumbnail(albumArtUri,
                        new android.util.Size(COVER_TARGET_SIZE, COVER_TARGET_SIZE), null);
            }
            return decodeAlbumArtLegacy(resolver, albumId);
        } catch (OutOfMemoryError e) {
            Log.w(TAG, "OOM decodificando capa do album " + albumId);
            return null;
        } catch (Throwable t) {
            Log.w(TAG, "sem capa de album para " + albumId);
            return null;
        }
    }

    private static Bitmap decodeAlbumArtLegacy(ContentResolver resolver, long albumId) {
        String[] projection = {Albums.ALBUM_ART};
        Cursor cursor = resolver.query(Albums.EXTERNAL_CONTENT_URI, projection,
                Albums._ID + "=?", new String[]{String.valueOf(albumId)}, null);
        if (cursor == null) return null;
        try {
            if (cursor.moveToFirst()) {
                String path = cursor.getString(0);
                if (path != null) {
                    return BitmapFactory.decodeFile(path);
                }
            }
        } finally {
            cursor.close();
        }
        return null;
    }

    // Fix (Player3D): carrega a capa de uma faixa da fila em background e
    // aplica via playTrackFromQueue() quando terminar (mesmo papel do
    // antigo QueueCoverLoader de MoviePlayer).
    private final class QueueCoverLoader extends AsyncTask<Void, Void, Bitmap> {
        private final Uri mTargetUri;
        private final String mTitle;
        private final String mArtist;

        QueueCoverLoader(Uri targetUri, String title, String artist) {
            mTargetUri = targetUri;
            mTitle = title;
            mArtist = artist;
        }

        @Override
        protected Bitmap doInBackground(Void... params) {
            Bitmap cover = decodeEmbeddedCover(getApplicationContext(), mTargetUri);
            if (cover == null) {
                ContentResolver resolver = getApplicationContext().getContentResolver();
                long albumId = -1;
                Cursor cursor = null;
                try {
                    cursor = resolver.query(mTargetUri,
                            new String[]{AudioColumns.ALBUM_ID}, null, null, null);
                    if (cursor != null && cursor.moveToFirst()) {
                        albumId = cursor.getLong(0);
                    }
                } catch (Throwable ignored) {
                } finally {
                    if (cursor != null) cursor.close();
                }
                if (albumId >= 0) {
                    cover = decodeAlbumArtFallback(resolver, albumId);
                }
            }
            return cover;
        }

        @Override
        protected void onPostExecute(Bitmap cover) {
            // So aplica se ainda estivermos navegando para essa mesma
            // faixa (evita corrida se o usuario navegou de novo antes do
            // carregamento anterior terminar).
            if (!mTargetUri.equals(mCurrentUri)) return;
            mCurrentCover = cover;
            updateNotification();
            if (mCallback != null) {
                mCallback.onTrackChanged(mTargetUri, mTitle, mArtist, cover);
            }
        }
    }

    // Fix (Player3D): toca de verdade uma faixa da FILA (navegacao interna,
    // por next/previous) - troca a faixa tocando, avisa o Callback
    // imediatamente com a capa ainda nula (placeholder) e dispara o
    // carregamento assincrono da capa real, que atualiza tudo de novo
    // quando terminar. Distinto de playTrack() (chamado pelo cliente ao
    // ABRIR a tela pela primeira vez, ja com capa pronta em maos).
    private void playTrackFromQueue(int index) {
        mQueueIndex = index;
        Uri uri = mQueueUris[index];
        String title = mQueueTitles[index] != null ? mQueueTitles[index] : "";
        String artist = mQueueArtists[index] != null ? mQueueArtists[index] : "";

        playTrack(uri, title, artist, null);
        if (mCallback != null) {
            mCallback.onTrackChanged(uri, title, artist, null);
        }
        new QueueCoverLoader(uri, title, artist).execute();
    }

    @Override
    public void onPrepared(MediaPlayer mp) {
        mPreparing = false;
        mp.start();
        updatePlaybackState();
        notifyState(true);
        // Fix (Player3D): grava no historico local toda vez que uma
        // faixa comeca a tocar de fato. O track_id e extraido da propria
        // Uri (Audio.Media.EXTERNAL_CONTENT_URI/{id}, ver
        // LocalAudio.getContentUri()) via ContentUris.parseId(), pois o
        // Service nao guarda uma referencia a LocalAudio.
        recordPlaybackHistory();
    }

    // Fix (Player3D): ver onPrepared() acima.
    private void recordPlaybackHistory() {
        if (mCurrentUri == null) return;
        try {
            long trackId = android.content.ContentUris.parseId(mCurrentUri);
            new com.android.gallery3d.data.PlaybackHistoryDatabase(getApplicationContext())
                    .recordPlay(trackId);
        } catch (Throwable t) {
            Log.w(TAG, "nao foi possivel gravar historico para " + mCurrentUri, t);
        }
    }

    @Override
    public void onCompletion(MediaPlayer mp) {
        if (mRepeatMode == RepeatMode.ONE) {
            mp.seekTo(0);
            mp.start();
            updatePlaybackState();
            notifyState(true);
            return;
        }
        // Repetir todas ou tocar a proxima faixa da fila e decisao interna
        // (ver requestNext) - o Service so avisa que acabou.
        // Fix (Player3D): fromUserAction=false - fim natural da faixa,
        // nao pedido do usuario. So esse caminho pode fechar a tela
        // (via onPlaybackEndedWithNoQueue, decidido pelo Callback).
        requestNext(false);
    }

    @Override
    public boolean onError(MediaPlayer mp, int what, int extra) {
        mPreparing = false;
        Log.e(TAG, "MediaPlayer error: what=" + what + " extra=" + extra);
        if (mCallback != null) {
            mCallback.onTrackError(new IOException("MediaPlayer error " + what + "/" + extra));
        }
        return true;
    }

    public void togglePlayPause() {
        if (mMediaPlayer == null || mPreparing) return;
        if (mMediaPlayer.isPlaying()) {
            pause();
        } else {
            resume();
        }
    }

    public void pause() {
        if (mMediaPlayer != null && !mPreparing && mMediaPlayer.isPlaying()) {
            mMediaPlayer.pause();
            updatePlaybackState();
            notifyState(false);
        }
    }

    public void resume() {
        if (mMediaPlayer != null && !mPreparing && !mMediaPlayer.isPlaying()) {
            mMediaPlayer.start();
            updatePlaybackState();
            notifyState(true);
        }
    }

    public void seekTo(int milliseconds) {
        if (mMediaPlayer != null && !mPreparing) {
            mMediaPlayer.seekTo(milliseconds);
            updatePlaybackState();
        }
    }

    public int getCurrentPosition() {
        return (mMediaPlayer != null && !mPreparing) ? mMediaPlayer.getCurrentPosition() : 0;
    }

    public int getDuration() {
        return (mMediaPlayer != null && !mPreparing) ? mMediaPlayer.getDuration() : 0;
    }

    public boolean isPlaying() {
        return mMediaPlayer != null && !mPreparing && mMediaPlayer.isPlaying();
    }

    public RepeatMode getRepeatMode() {
        return mRepeatMode;
    }

    public void toggleRepeatAll() {
        mRepeatMode = (mRepeatMode == RepeatMode.ALL) ? RepeatMode.OFF : RepeatMode.ALL;
        if (mCallback != null) mCallback.onRepeatModeChanged(mRepeatMode);
        updateNotification();
    }

    public void toggleRepeatOne() {
        mRepeatMode = (mRepeatMode == RepeatMode.ONE) ? RepeatMode.OFF : RepeatMode.ONE;
        if (mCallback != null) mCallback.onRepeatModeChanged(mRepeatMode);
        updateNotification();
    }

    private boolean hasQueue() {
        return mQueueUris != null && mQueueIndex >= 0;
    }

    private boolean isRepeatAll() {
        return mRepeatMode == RepeatMode.ALL;
    }

    /**
     * Clique curto/duplo de "faixa anterior": se ja passou de 3s tocando a
     * faixa atual, volta pro inicio dela; senao, navega para a faixa
     * anterior de verdade na fila (Fix Player3D: decidido aqui dentro,
     * sem depender de nenhum cliente vinculado).
     */
    private void requestPrevious() {
        if (mMediaPlayer != null && !mPreparing && mMediaPlayer.getCurrentPosition() > PREVIOUS_RESTART_THRESHOLD_MS) {
            seekTo(0);
            return;
        }
        if (!hasQueue()) {
            seekTo(0);
            return;
        }
        int prev = mQueueIndex - 1;
        if (prev < 0) {
            if (isRepeatAll()) {
                prev = mQueueUris.length - 1;
            } else {
                seekTo(0);
                return;
            }
        }
        playTrackFromQueue(prev);
    }

    // Fix (Player3D): decisao de navegacao de "proxima faixa" agora e
    // 100% interna ao Service (nao depende mais de QueueController
    // externo) - funciona com ou sem MoviePlayer vinculado, resolvendo o
    // bug de botoes de notificacao "sem efeito" quando a tela de
    // reproducao ja foi fechada pelo Android. fromUserAction distingue
    // pedido do usuario (nunca fecha a tela sozinho, so pausa) de fim
    // natural da faixa (pode fechar, via onPlaybackEndedWithNoQueue, so
    // no caso sem fila e sem repeat).
    private void requestNext(boolean fromUserAction) {
        if (!hasQueue()) {
            if (fromUserAction) {
                pause();
            } else if (mCallback != null) {
                mCallback.onPlaybackEndedWithNoQueue();
            }
            return;
        }
        int next = mQueueIndex + 1;
        if (next >= mQueueUris.length) {
            if (isRepeatAll()) {
                next = 0;
            } else {
                pause();
                return;
            }
        }
        playTrackFromQueue(next);
    }

    private void stopPlaybackAndService() {
        releaseMediaPlayer();
        stopForeground(true);
        stopSelf();
    }

    @Override
    public void onDestroy() {
        releaseMediaPlayer();
        if (mMediaSession != null) {
            mMediaSession.setActive(false);
            mMediaSession.release();
        }
        super.onDestroy();
    }

    private void releaseMediaPlayer() {
        if (mMediaPlayer != null) {
            try {
                mMediaPlayer.reset();
                mMediaPlayer.release();
            } catch (IllegalStateException e) {
                Log.w(TAG, "Erro ao liberar MediaPlayer", e);
            }
            mMediaPlayer = null;
        }
        mPreparing = false;
    }

    private void notifyState(boolean isPlaying) {
        if (mCallback != null) mCallback.onPlaybackStateChanged(isPlaying);
        updateNotification();
    }

    private void updatePlaybackState() {
        long actions = PlaybackState.ACTION_PLAY_PAUSE
                | PlaybackState.ACTION_PLAY
                | PlaybackState.ACTION_PAUSE
                | PlaybackState.ACTION_SKIP_TO_NEXT
                | PlaybackState.ACTION_SKIP_TO_PREVIOUS
                | PlaybackState.ACTION_SEEK_TO;

        int state = isPlaying() ? PlaybackState.STATE_PLAYING : PlaybackState.STATE_PAUSED;

        PlaybackState.Builder builder = new PlaybackState.Builder()
                .setActions(actions)
                .setState(state, getCurrentPosition(), 1.0f);
        mMediaSession.setPlaybackState(builder.build());
    }

    private void createNotificationChannel() {
        mNotificationManager = getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, getString(R.string.app_name),
                    NotificationManager.IMPORTANCE_LOW);
            mNotificationManager.createNotificationChannel(channel);
        }
    }

    // Fix (Player3D): request code baseado em action.hashCode() e fragil -
    // hashCode nao tem garantia de unicidade nem de estabilidade entre
    // execucoes/versoes de String, o que podia fazer PendingIntents de
    // botoes diferentes colidirem no cache do sistema e alguns botoes da
    // notificacao pararem de responder. Cada botao agora tem um request
    // code fixo e unico, igual ao padrao recomendado pela documentacao do
    // Android pra PendingIntents de notificacao com multiplas acoes.
    private static final int REQUEST_CODE_REPEAT_ALL = 101;
    private static final int REQUEST_CODE_PREVIOUS = 102;
    private static final int REQUEST_CODE_PLAY_PAUSE = 103;
    private static final int REQUEST_CODE_NEXT = 104;
    private static final int REQUEST_CODE_REPEAT_ONE = 105;

    private PendingIntent actionPendingIntent(String action, int requestCode) {
        Intent intent = new Intent(this, MusicPlaybackService.class);
        intent.setAction(action);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return PendingIntent.getService(this, requestCode, intent, flags);
    }

    private Notification buildNotification() {
        boolean playing = isPlaying();
        // Nota: o estado visual "ativado" (ALL/1 destacado) dos botoes e
        // especificado no Passo 4.2 para a tela de reproducao; a notificacao
        // usa aqui o mesmo icone monocromatico nos dois estados.

        Notification.Action repeatAll = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_repeat_all,
                getString(R.string.player3d_repeat_all),
                actionPendingIntent(ACTION_TOGGLE_REPEAT_ALL, REQUEST_CODE_REPEAT_ALL)).build();

        Notification.Action previous = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_previous,
                getString(R.string.player3d_previous),
                actionPendingIntent(ACTION_PREVIOUS, REQUEST_CODE_PREVIOUS)).build();

        Notification.Action playPause = new Notification.Action.Builder(
                playing ? R.drawable.ic_vidcontrol_pause : R.drawable.ic_vidcontrol_play,
                getString(playing ? R.string.player3d_pause : R.string.player3d_play),
                actionPendingIntent(ACTION_PLAY_PAUSE, REQUEST_CODE_PLAY_PAUSE)).build();

        Notification.Action next = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_next,
                getString(R.string.player3d_next),
                actionPendingIntent(ACTION_NEXT, REQUEST_CODE_NEXT)).build();

        Notification.Action repeatOne = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_repeat_one,
                getString(R.string.player3d_repeat_one),
                actionPendingIntent(ACTION_TOGGLE_REPEAT_ONE, REQUEST_CODE_REPEAT_ONE)).build();

        Notification.MediaStyle style = new Notification.MediaStyle()
                .setMediaSession(mMediaSession.getSessionToken())
                .setShowActionsInCompactView(1, 2, 3);

        Notification.Builder builder = new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_vidcontrol_play)
                .setContentTitle(mCurrentTitle)
                .setContentText(mCurrentArtist)
                .setLargeIcon(mCurrentCover)
                .setOngoing(playing)
                .setOnlyAlertOnce(true)
                .setStyle(style)
                .addAction(repeatAll)
                .addAction(previous)
                .addAction(playPause)
                .addAction(next)
                .addAction(repeatOne);

        return builder.build();
    }

    private void updateNotification() {
        if (mNotificationManager == null) return;
        mNotificationManager.notify(NOTIFICATION_ID, buildNotification());
    }
}
'''


def step_music_service():
    if not MUSIC_SERVICE.exists():
        fail(f"Arquivo não encontrado: {MUSIC_SERVICE}")
    content = MUSIC_SERVICE.read_text(encoding="utf-8")
    if MARKER in content:
        print("[1/2 MusicPlaybackService.java] Já aplicado antes — nada a fazer (idempotente).")
        return
    backup(MUSIC_SERVICE)
    MUSIC_SERVICE.write_text(MUSIC_SERVICE_NEW, encoding="utf-8")
    print("[1/2 MusicPlaybackService.java] OK — fila migrada para dentro do Service.")


# =======================================================================
# MoviePlayer.java — patches cirúrgicos (arquivo grande, edição pontual)
# =======================================================================

def step_movie_player():
    if not MOVIE_PLAYER.exists():
        fail(f"Arquivo não encontrado: {MOVIE_PLAYER}")
    content = MOVIE_PLAYER.read_text(encoding="utf-8")
    if MARKER in content:
        print("[2/2 MoviePlayer.java] Já aplicado antes — nada a fazer (idempotente).")
        return

    backup(MOVIE_PLAYER)

    # --- 2.0: cabeçalho da classe (comentário) ---
    old_header = '''/*
 * Passo 4.1 (Player3D) - motor de renderizacao trocado de VideoView para
 * MediaPlayer puro. Desde o Passo 9, o MediaPlayer real nao mora mais aqui:
 * mora no MusicPlaybackService, que roda em foreground e sobrevive mesmo
 * com a tela de reproducao fechada. Esta classe virou um cliente do
 * Service via bindService()/Binder - implementa MusicPlaybackService.Callback
 * (estado de reproducao/erro) e MusicPlaybackService.QueueController
 * (proxima/anterior faixa), que e a mesma fonte de verdade usada pela
 * notificacao e pela tela de bloqueio (item 9.3 da especificacao).
 *
 * Fix (Player3D): o app agora tem uma fila real, carregada de forma
 * assincrona (AlbumQueueLoader) com as outras faixas do MESMO album da
 * faixa aberta. onNextRequested()/onPreviousRequested() navegam pra
 * faixa real seguinte/anterior quando essa fila existe; sem fila (album
 * com 1 faixa so, ou faixa fora do MediaStore local), cai no
 * comportamento antigo, honesto e minimo: "proxima" ao fim da faixa ==
 * fim da reproducao, "anterior" volta pro inicio da faixa atual.
 */'''
    new_header = '''/*
 * Passo 4.1 (Player3D) - motor de renderizacao trocado de VideoView para
 * MediaPlayer puro. Desde o Passo 9, o MediaPlayer real nao mora mais aqui:
 * mora no MusicPlaybackService, que roda em foreground e sobrevive mesmo
 * com a tela de reproducao fechada. Esta classe virou um cliente do
 * Service via bindService()/Binder - implementa MusicPlaybackService.Callback
 * (estado de reproducao/erro, mudanca de faixa, fim de reproducao sem
 * fila), que e a mesma fonte de verdade usada pela notificacao e pela
 * tela de bloqueio (item 9.3 da especificacao).
 *
 * Fix (Player3D): a fila real de outras faixas do MESMO album da faixa
 * aberta - e a decisao de para onde navegar em "proxima"/"anterior" -
 * agora vivem dentro de MusicPlaybackService, nao aqui (ver comentario no
 * topo de MusicPlaybackService.java). Motivo: MoviePlayer e destruido
 * junto com a MovieActivity quando o Android fecha a tela, mas a
 * notificacao/MediaSession/lockscreen (que tambem navegam a fila)
 * precisam continuar funcionando mesmo nesse caso - por isso quem manda
 * na fila e o Service, que sobrevive em foreground. Esta classe so reage
 * as mudancas via onTrackChanged()/onPlaybackEndedWithNoQueue().
 */'''
    if content.count(old_header) != 1:
        fail("Comentário de cabeçalho da classe não encontrado (ou "
             "ambíguo) — verifique manualmente.")
    content = content.replace(old_header, new_header, 1)

    # --- 2.1: implements MusicPlaybackService.QueueController removido ---
    old_impl = '''public class MoviePlayer implements
        MusicPlaybackService.Callback, MusicPlaybackService.QueueController,
        ControllerOverlay.Listener {'''
    new_impl = '''public class MoviePlayer implements
        MusicPlaybackService.Callback, ControllerOverlay.Listener {'''
    if content.count(old_impl) != 1:
        fail("Assinatura de 'class MoviePlayer implements' não encontrada "
             "(ou ambígua) — verifique manualmente.")
    content = content.replace(old_impl, new_impl, 1)

    # --- 2.1b: remove as 2 chamadas a mService.setQueueController(...) -
    # o metodo nao existe mais em MusicPlaybackService (QueueController foi
    # removido) - sem isso o projeto nao compila.
    old_connect = '''            mService.setCallback(MoviePlayer.this);
            mService.setQueueController(MoviePlayer.this);
            maybeStartPlayback();'''
    new_connect = '''            mService.setCallback(MoviePlayer.this);
            maybeStartPlayback();'''
    if content.count(old_connect) != 1:
        fail("Ponto de onServiceConnected (setCallback+setQueueController) "
             "não encontrado (ou ambíguo) — verifique manualmente.")
    content = content.replace(old_connect, new_connect, 1)

    old_disconnect = '''            if (mService != null) {
                mService.setCallback(null);
                mService.setQueueController(null);
            }'''
    new_disconnect = '''            if (mService != null) {
                mService.setCallback(null);
            }'''
    if content.count(old_disconnect) != 1:
        fail("Ponto de onDestroy (setCallback(null)+setQueueController(null)) "
             "não encontrado (ou ambíguo) — verifique manualmente.")
    content = content.replace(old_disconnect, new_disconnect, 1)

    # --- 2.2: remove os campos de fila local ---
    old_fields = '''    // Fix (Player3D): fila real das outras faixas do MESMO album da faixa
    // aberta. Antes disso existir, "proxima" so fechava a tela (era
    // tratado como fim de reproducao) e "anterior" so reiniciava a faixa
    // atual - nenhum dos dois navegava de verdade. Carregada de forma
    // assincrona por AlbumQueueLoader assim que sabemos o albumId (depois
    // que TrackMetadataLoader termina). mQueueIndex == -1 significa "fila
    // ainda nao carregada, ou faixa sem album/fora de MediaStore local" -
    // nesse caso next/previous caem no comportamento antigo, honesto e
    // minimo (fim de reproducao / reiniciar faixa atual).
    private Uri[] mQueueUris;
    private String[] mQueueTitles;
    private String[] mQueueArtists;
    private int mQueueIndex = -1;
    // Uri da faixa TOCANDO agora - pode mudar ao navegar pela fila. mUri
    // (acima) continua sendo a faixa com que a tela foi aberta, usada so
    // para o bookmark de "retomar de onde parou" do fluxo original.
    private Uri mCurrentPlayUri;'''
    new_fields = '''    // Fix (Player3D): a fila de proxima/anterior faixa (mesmo album) agora
    // mora em MusicPlaybackService, nao aqui - ver comentario no topo de
    // MusicPlaybackService.java. MoviePlayer so guarda a Uri tocando
    // AGORA (atualizada via callback onTrackChanged()), nao a fila em si.
    // Uri da faixa TOCANDO agora - pode mudar ao navegar pela fila. mUri
    // (acima) continua sendo a faixa com que a tela foi aberta, usada so
    // para o bookmark de "retomar de onde parou" do fluxo original.
    private Uri mCurrentPlayUri;'''
    if content.count(old_fields) != 1:
        fail("Bloco de campos de fila (mQueueUris etc) não encontrado (ou "
             "ambíguo) em MoviePlayer.java — verifique manualmente.")
    content = content.replace(old_fields, new_fields, 1)

    # --- 2.3: TrackMetadataLoader.onPostExecute - troca AlbumQueueLoader
    # local por mService.loadQueueForAlbum() ---
    old_post_execute = '''        @Override
        protected void onPostExecute(Result result) {
            mTrackTitle = result.title != null ? result.title : "";
            mTrackArtist = result.artist != null ? result.artist : "";
            mTrackCover = result.cover;
            if (result.cover != null) {
                mCoverView.setImageBitmap(result.cover);
            } else {
                mCoverView.setImageResource(R.drawable.ic_audio_cover_placeholder);
            }
            mMetadataLoaded = true;
            // Fix (Player3D): assim que sabemos o albumId, carrega a fila
            // real das outras faixas do mesmo album em segundo plano, pra
            // next/previous poderem navegar de verdade.
            if (result.albumId >= 0) {
                new AlbumQueueLoader(result.albumId).execute();
            }
            maybeStartPlayback();
        }
    }'''
    new_post_execute = '''        @Override
        protected void onPostExecute(Result result) {
            mTrackTitle = result.title != null ? result.title : "";
            mTrackArtist = result.artist != null ? result.artist : "";
            mTrackCover = result.cover;
            if (result.cover != null) {
                mCoverView.setImageBitmap(result.cover);
            } else {
                mCoverView.setImageResource(R.drawable.ic_audio_cover_placeholder);
            }
            mMetadataLoaded = true;
            maybeStartPlayback();
        }
    }

    // Fix (Player3D): chamado depois que o Service esta vinculado E a
    // faixa comecou a tocar de fato (mCurrentPlayUri ja e a Uri real
    // tocando) - pede ao Service para carregar a fila do album em segundo
    // plano. A fila passa a viver la, nao aqui (ver comentario no topo de
    // MusicPlaybackService.java).
    private void requestQueueLoad(long albumId) {
        if (mService != null && albumId >= 0) {
            mService.loadQueueForAlbum(albumId, mCurrentPlayUri);
        }
    }'''
    if content.count(old_post_execute) != 1:
        fail("TrackMetadataLoader.onPostExecute() não encontrado no formato "
             "esperado (ou ambíguo) em MoviePlayer.java — verifique manualmente.")
    content = content.replace(old_post_execute, new_post_execute, 1)

    # --- 2.4: guardar albumId para poder pedir a fila assim que o Service
    # conectar (caso a conexao termine DEPOIS dos metadados, ordem nao
    # garantida entre as duas tasks assincronas do construtor) ---
    old_result_class = '''        final class Result {
            String title;
            String artist;
            Bitmap cover;
            long albumId = -1;
        }'''
    # (mantido sem mudanca - so confirmando que existe, ancora abaixo)
    if content.count(old_result_class) != 1:
        fail("Classe Result de TrackMetadataLoader não encontrada (ou "
             "ambígua) — verifique manualmente.")

    old_on_post_execute_2 = '''            mMetadataLoaded = true;
            maybeStartPlayback();
        }
    }

    // Fix (Player3D): chamado depois'''
    new_on_post_execute_2 = '''            mMetadataLoaded = true;
            mPendingAlbumId = result.albumId;
            maybeStartPlayback();
        }
    }

    // Fix (Player3D): chamado depois'''
    if content.count(old_on_post_execute_2) != 1:
        fail("Ponto de ancoragem para mPendingAlbumId não encontrado (ou "
             "ambíguo) — verifique manualmente.")
    content = content.replace(old_on_post_execute_2, new_on_post_execute_2, 1)

    # --- 2.5: declarar mPendingAlbumId junto dos outros campos de estado ---
    old_state_fields = '''    private boolean mServiceBound;
    private boolean mMetadataLoaded;
    private boolean mStarted;'''
    new_state_fields = '''    private boolean mServiceBound;
    private boolean mMetadataLoaded;
    private boolean mStarted;
    // Fix (Player3D): albumId resolvido por TrackMetadataLoader, guardado
    // ate o Service estar vinculado para podermos pedir loadQueueForAlbum()
    // (as duas tasks assincronas do construtor - metadados e bind do
    // Service - nao tem ordem garantida entre si).
    private long mPendingAlbumId = -1;
    private boolean mQueueRequested;'''
    if content.count(old_state_fields) != 1:
        fail("Bloco de campos de estado (mServiceBound/mMetadataLoaded/"
             "mStarted) não encontrado (ou ambíguo) — verifique manualmente.")
    content = content.replace(old_state_fields, new_state_fields, 1)

    # --- 2.6: maybeStartPlayback() passa a tambem disparar o pedido de
    # fila quando tanto o Service quanto o albumId estiverem prontos ---
    old_maybe_start = '''    private void maybeStartPlayback() {
        if (mStarted || !mServiceBound || !mMetadataLoaded) return;
        mStarted = true;

        if (mVideoPosition > 0) {'''
    new_maybe_start = '''    private void maybeStartPlayback() {
        // Fix (Player3D): o pedido de fila so depende de Service vinculado
        // + albumId conhecido (nao do inicio da reproducao em si) - roda
        // assim que os dois estiverem prontos, uma unica vez.
        if (mServiceBound && mMetadataLoaded && !mQueueRequested) {
            mQueueRequested = true;
            requestQueueLoad(mPendingAlbumId);
        }

        if (mStarted || !mServiceBound || !mMetadataLoaded) return;
        mStarted = true;

        if (mVideoPosition > 0) {'''
    if content.count(old_maybe_start) != 1:
        fail("maybeStartPlayback() não encontrado no formato esperado (ou "
             "ambíguo) — verifique manualmente.")
    content = content.replace(old_maybe_start, new_maybe_start, 1)

    # --- 2.7: remove decodeEmbeddedCover/decodeAlbumArtFallback/Legacy
    # duplicados? NAO - mantidos aqui tambem, pois TrackMetadataLoader
    # (metadados da faixa ABERTA originalmente) continua usando-os. So
    # removemos o que era exclusivo de navegacao de fila (AlbumQueueLoader,
    # QueueCoverLoader), que migrou pro Service.

    old_album_queue_loader_and_queue_cover = '''    // Fix (Player3D): carrega as outras faixas do MESMO album (mesmo
    // ALBUM_ID da faixa aberta) pra next/previous poderem navegar de
    // verdade dentro do album, em vez de fechar a tela (next) ou so
    // reiniciar a faixa atual (previous). Ordenada por numero da faixa,
    // com titulo como desempate - mesmo criterio usado pra playlists de
    // album em qualquer tocador de musica.
    private final class AlbumQueueLoader extends AsyncTask<Void, Void, AlbumQueueLoader.Result> {
        private final long mAlbumId;

        AlbumQueueLoader(long albumId) {
            mAlbumId = albumId;
        }

        final class Result {
            Uri[] uris;
            String[] titles;
            String[] artists;
            int currentIndex = -1;
        }

        @Override
        protected Result doInBackground(Void... params) {
            Result result = new Result();
            ContentResolver resolver = mContext.getContentResolver();
            String[] projection = {
                    AudioColumns._ID, AudioColumns.TITLE, AudioColumns.ARTIST,
            };
            String selection = AudioColumns.ALBUM_ID + "=?";
            String[] selectionArgs = {String.valueOf(mAlbumId)};
            String sortOrder = AudioColumns.TRACK + " ASC, " + AudioColumns.TITLE + " ASC";

            long currentId = -1;
            try {
                currentId = ContentUris.parseId(mCurrentPlayUri);
            } catch (Throwable ignored) {
                // Uri sem _id numerico no final (ex.: content:// vindo de
                // outro provider) - sem como comparar, a fila fica vazia e
                // o comportamento antigo (sem navegacao real) e mantido.
            }

            Cursor cursor = null;
            try {
                cursor = resolver.query(Media.EXTERNAL_CONTENT_URI, projection,
                        selection, selectionArgs, sortOrder);
                if (cursor != null && cursor.getCount() > 0) {
                    int count = cursor.getCount();
                    result.uris = new Uri[count];
                    result.titles = new String[count];
                    result.artists = new String[count];
                    int i = 0;
                    while (cursor.moveToNext()) {
                        long id = cursor.getLong(0);
                        result.uris[i] = ContentUris.withAppendedId(Media.EXTERNAL_CONTENT_URI, id);
                        result.titles[i] = cursor.getString(1);
                        result.artists[i] = cursor.getString(2);
                        if (id == currentId) {
                            result.currentIndex = i;
                        }
                        i++;
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "falha ao carregar fila do album " + mAlbumId, t);
            } finally {
                if (cursor != null) cursor.close();
            }
            return result;
        }

        @Override
        protected void onPostExecute(Result result) {
            if (result.uris == null || result.uris.length <= 1 || result.currentIndex < 0) {
                // Album com 1 faixa so (ou faixa nao reencontrada na
                // consulta) - nao ha o que navegar, fila fica vazia e
                // hasQueue() continua reportando false.
                return;
            }
            mQueueUris = result.uris;
            mQueueTitles = result.titles;
            mQueueArtists = result.artists;
            mQueueIndex = result.currentIndex;
        }
    }

    // Fix (Player3D): carrega a capa da faixa ao navegar pela fila
    // (next/previous reais) - mesma tecnica de decodeEmbeddedCover/
    // decodeAlbumArtFallback, so que titulo/artista ja vieram prontos de
    // AlbumQueueLoader (nao precisa reconsultar).
    private final class QueueCoverLoader extends AsyncTask<Void, Void, Bitmap> {
        private final Uri mTargetUri;

        QueueCoverLoader(Uri targetUri) {
            mTargetUri = targetUri;
        }

        @Override
        protected Bitmap doInBackground(Void... params) {
            Bitmap cover = decodeEmbeddedCover(mContext, mTargetUri);
            if (cover == null) {
                ContentResolver resolver = mContext.getContentResolver();
                long albumId = -1;
                Cursor cursor = null;
                try {
                    cursor = resolver.query(mTargetUri,
                            new String[]{AudioColumns.ALBUM_ID}, null, null, null);
                    if (cursor != null && cursor.moveToFirst()) {
                        albumId = cursor.getLong(0);
                    }
                } catch (Throwable ignored) {
                } finally {
                    if (cursor != null) cursor.close();
                }
                if (albumId >= 0) {
                    cover = decodeAlbumArtFallback(resolver, albumId);
                }
            }
            return cover;
        }

        @Override
        protected void onPostExecute(Bitmap cover) {
            // So aplica se ainda estivermos tocando essa mesma faixa (evita
            // sobrescrever a capa se o usuario navegou de novo antes do
            // carregamento anterior terminar).
            if (!mTargetUri.equals(mCurrentPlayUri)) return;
            mTrackCover = cover;
            if (cover != null) {
                mCoverView.setImageBitmap(cover);
            } else {
                mCoverView.setImageResource(R.drawable.ic_audio_cover_placeholder);
            }
        }
    }

    private String mTrackTitle = "";'''
    new_after_removal = '''    private String mTrackTitle = "";'''
    if content.count(old_album_queue_loader_and_queue_cover) != 1:
        fail("Blocos AlbumQueueLoader/QueueCoverLoader não encontrados (ou "
             "ambíguos) em MoviePlayer.java — verifique manualmente.")
    content = content.replace(old_album_queue_loader_and_queue_cover, new_after_removal, 1)

    # --- 2.8: substitui onNextRequested/onPreviousRequested/hasQueue/
    # isRepeatAll/playQueueIndex por onTrackChanged/onPlaybackEndedWithNoQueue ---
    old_next_prev_block = '''    // Below are notifications from MusicPlaybackService.QueueController.
    // Fix (Player3D): antes, o app nao tinha fila/playlist real - "proxima"
    // so fechava a tela (tratada como fim de reproducao) e "anterior" so
    // reiniciava a faixa atual. Agora, quando ha uma fila carregada
    // (AlbumQueueLoader encontrou outras faixas do mesmo album), next/
    // previous navegam pra faixa real seguinte/anterior. Sem fila (album
    // com 1 faixa so, ou faixa fora do MediaStore local), cai no
    // comportamento antigo, honesto e minimo.
    // Fix (Player3D): onNextRequested(fromUserAction) agora distingue POR
    // QUE foi chamado (ver MusicPlaybackService.QueueController).
    // fromUserAction=true (usuario clicou "proxima"/notificacao/MediaSession)
    // NUNCA fecha a tela, mesmo sem fila carregada - so pausa, igual ao
    // fim de fila sem repeat. fromUserAction=false (a faixa atual chegou
    // ao fim tocando sozinha) preserva o unico caso em que fechar a tela
    // e o comportamento correto: sem fila E sem repeat, chega ao fim,
    // fecha.
    @Override
    public void onNextRequested(boolean fromUserAction) {
        if (!hasQueue()) {
            if (fromUserAction) {
                if (mService != null) mService.pause();
                mController.showPaused();
            } else {
                mController.showEnded();
                onCompletion();
            }
            return;
        }
        int next = mQueueIndex + 1;
        if (next >= mQueueUris.length) {
            if (isRepeatAll()) {
                next = 0;
            } else {
                // Fix (Player3D): fim da fila sem repeat NAO fecha mais a
                // tela - so pausa na ultima faixa, com o botao de play de
                // volta.
                if (mService != null) mService.pause();
                mController.showPaused();
                return;
            }
        }
        playQueueIndex(next);
    }

    @Override
    public void onPreviousRequested() {
        if (!hasQueue()) {
            if (mService != null) mService.seekTo(0);
            return;
        }
        int prev = mQueueIndex - 1;
        if (prev < 0) {
            if (isRepeatAll()) {
                prev = mQueueUris.length - 1;
            } else {
                if (mService != null) mService.seekTo(0);
                return;
            }
        }
        playQueueIndex(prev);
    }

    private boolean hasQueue() {
        return mQueueUris != null && mQueueIndex >= 0;
    }

    private boolean isRepeatAll() {
        return mService != null
                && mService.getRepeatMode() == MusicPlaybackService.RepeatMode.ALL;
    }

    // Fix (Player3D): toca de verdade a faixa em mQueueUris[index] - troca
    // Uri/titulo/artista (ja vieram prontos de AlbumQueueLoader) e dispara
    // o carregamento assincrono da capa dessa faixa (QueueCoverLoader).
    private void playQueueIndex(int index) {
        mQueueIndex = index;
        mCurrentPlayUri = mQueueUris[index];
        mTrackTitle = mQueueTitles[index] != null ? mQueueTitles[index] : "";
        mTrackArtist = mQueueArtists[index] != null ? mQueueArtists[index] : "";
        mTrackCover = null;
        mCoverView.setImageResource(R.drawable.ic_audio_cover_placeholder);
        new QueueCoverLoader(mCurrentPlayUri).execute();
        playCurrentTrack(0);
    }

    public void onCompletion() {
    }'''
    new_next_prev_block = '''    // Fix (Player3D): a decisao de navegacao de fila (proxima/anterior)
    // agora vive inteiramente dentro de MusicPlaybackService (ver
    // comentario no topo de MusicPlaybackService.java) - MoviePlayer so
    // reage as mudancas via estes 2 callbacks, nao decide mais nada
    // sozinho sobre a fila.
    @Override
    public void onTrackChanged(Uri uri, String title, String artist, Bitmap cover) {
        mCurrentPlayUri = uri;
        mTrackTitle = title != null ? title : "";
        mTrackArtist = artist != null ? artist : "";
        mTrackCover = cover;
        if (cover != null) {
            mCoverView.setImageBitmap(cover);
        } else {
            mCoverView.setImageResource(R.drawable.ic_audio_cover_placeholder);
        }
    }

    @Override
    public void onPlaybackEndedWithNoQueue() {
        mController.showEnded();
        onCompletion();
    }

    public void onCompletion() {
    }'''
    if content.count(old_next_prev_block) != 1:
        fail("Bloco onNextRequested/onPreviousRequested não encontrado (ou "
             "ambíguo) em MoviePlayer.java — verifique manualmente.")
    content = content.replace(old_next_prev_block, new_next_prev_block, 1)

    # --- 2.9: agora imports podem ter ficado sem uso (ContentResolver,
    # Cursor, AudioColumns, Media, ContentUris ainda sao usados em
    # TrackMetadataLoader/decodeAlbumArtFallback - NAO remover). Mantidos
    # de proposito: TrackMetadataLoader ainda usa ContentResolver/Cursor/
    # AudioColumns/Media para resolver metadados da faixa ABERTA
    # originalmente (nao a fila).

    # --- 2.7b: comentário de decodeEmbeddedCover ainda cita QueueCoverLoader
    # (que migrou pro Service) - ajusta o texto pra nao confundir leitura
    # futura (não afeta compilação, é só comentário).
    old_decode_comment = '''    // Extracao de capa (embutida no arquivo, com fallback para a capa do
    // album via MediaStore) - promovida pra fora de TrackMetadataLoader
    // (Fix Player3D) pra ser reutilizada tambem por QueueCoverLoader, que
    // carrega a capa ao navegar pela fila real de next/previous. Mesma
    // tecnica do Passo 1.5 (LocalAudio), so que parametrizada por
    // Context/Uri em vez de depender de campos de uma unica faixa.
    private static Bitmap decodeEmbeddedCover(Context context, Uri uri) {'''
    new_decode_comment = '''    // Extracao de capa (embutida no arquivo, com fallback para a capa do
    // album via MediaStore) - usada por TrackMetadataLoader para a capa
    // da faixa com que a tela foi ABERTA originalmente. A navegacao de
    // fila (next/previous) tem sua propria copia equivalente dentro de
    // MusicPlaybackService (QueueCoverLoader), que carrega a capa das
    // OUTRAS faixas do album sem depender desta classe.
    private static Bitmap decodeEmbeddedCover(Context context, Uri uri) {'''
    if content.count(old_decode_comment) != 1:
        fail("Comentário de decodeEmbeddedCover não encontrado (ou "
             "ambíguo) — verifique manualmente.")
    content = content.replace(old_decode_comment, new_decode_comment, 1)

    if MARKER not in content:
        fail("Substituição falhou — marcador ausente após patch. Abortando "
             "sem escrever.")

    MOVIE_PLAYER.write_text(content, encoding="utf-8")
    print("[2/2 MoviePlayer.java] OK — lógica de fila removida, agora reage "
          "aos callbacks do Service.")


def main():
    if not PROJECT_ROOT.exists():
        fail(f"Projeto não encontrado em {PROJECT_ROOT}. Rode de dentro de ~/Galeria3D.")

    step_music_service()
    print()
    step_movie_player()

    print()
    print("Próximo passo:")
    print("  cd ~/Galeria3D && ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

/*
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
import android.media.MediaMetadata;
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
        MediaPlayer.OnErrorListener, MediaPlayer.OnSeekCompleteListener {

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
    // Correcao (Player3D): CHEGUEI a migrar isto para MediaSessionCompat/
    // PlaybackStateCompat (androidx.media), teorizando que o template de
    // notificacao redesenhado do Android 13+ so reconheceria um botao de
    // repetir via ACTION_SET_REPEAT_MODE/setRepeatMode() da lib de
    // compatibilidade. NA PRATICA, no aparelho de teste (Samsung One UI
    // 6.1, Android 14), essa migracao teve o efeito CONTRARIO: os 5
    // botoes (que apareciam certinho com a MediaSession framework pura)
    // sumiram da notificacao expandida depois dela. Revertido de volta
    // para MediaSession/PlaybackState framework (este arquivo), que e o
    // que comprovadamente funciona aqui. NAO reintroduzir
    // MediaSessionCompat sem antes confirmar em teste real que o
    // problema era mesmo isso - o comportamento de MediaStyle varia
    // bastante entre fabricante/versao e nao da pra deduzir so pela
    // documentacao.
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
        mMediaPlayer.setOnSeekCompleteListener(this);
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
        updatePlaybackState();
        startForeground(NOTIFICATION_ID, buildNotification());
    }

    // Fix (Player3D - fila por pasta): carrega a fila de outras faixas,
    // tentando primeiro pelo MESMO album e, se isso nao render pelo menos
    // 2 faixas, cai para a MESMA pasta (BUCKET_ID). Assincrono - quando
    // termina, apenas guarda a fila internamente; nao toca nada sozinho.
    //
    // Motivo do fallback por pasta: ALBUM_ID de audio local sem tag de
    // album fica NULO no MediaStore. O codigo antigo lia essa coluna nula
    // com cursor.getLong(), que devolve 0 (nao -1) para coluna nula, e
    // tratava isso como "album de id 0 valido" - a consulta seguinte
    // (ALBUM_ID=0) nunca batia com nada, porque no SQL nenhuma linha com
    // ALBUM_ID realmente NULO satisfaz "=0". Resultado: fila sempre vazia
    // pra qualquer faixa sem tag de album (comum em bibliotecas locais,
    // fora de servicos de streaming) - dai next/previous nunca funcionar,
    // nem na notificacao nem na tela, e a faixa nunca avancar sozinha ao
    // terminar. BUCKET_ID (pasta que contem o arquivo) e uma coluna do
    // MediaStore que NUNCA e nula para arquivo de midia local, entao serve
    // de fallback confiavel quando o album falha ou tem so 1 faixa.
    public void loadQueueForTrack(long albumId, long bucketId, Uri currentUri) {
        new QueueLoader(albumId, bucketId, currentUri).execute();
    }

    private final class QueueLoader extends AsyncTask<Void, Void, QueueLoader.Result> {
        private final long mAlbumId;
        private final long mBucketId;
        private final Uri mCurrentUriAtLoadTime;

        QueueLoader(long albumId, long bucketId, Uri currentUri) {
            mAlbumId = albumId;
            mBucketId = bucketId;
            mCurrentUriAtLoadTime = currentUri;
        }

        final class Result {
            Uri[] uris;
            String[] titles;
            String[] artists;
            int currentIndex = -1;
            String source = "nenhum";
        }

        private Result queryBy(String column, long value, String sortOrder,
                long currentId, String sourceLabel) {
            Result result = new Result();
            result.source = sourceLabel;
            ContentResolver resolver = getApplicationContext().getContentResolver();
            String[] projection = {
                    AudioColumns._ID, AudioColumns.TITLE, AudioColumns.ARTIST,
            };
            String selection = column + "=?";
            String[] selectionArgs = {String.valueOf(value)};

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
                Log.w(TAG, "falha ao carregar fila (" + sourceLabel + "=" + value + ")", t);
            } finally {
                if (cursor != null) cursor.close();
            }
            return result;
        }

        private boolean isUsable(Result result) {
            return result.uris != null && result.uris.length > 1 && result.currentIndex >= 0;
        }

        @Override
        protected Result doInBackground(Void... params) {
            long currentId = -1;
            try {
                currentId = ContentUris.parseId(mCurrentUriAtLoadTime);
            } catch (Throwable ignored) {
                // Uri sem _id numerico no final - sem como comparar, a
                // fila fica vazia e o comportamento antigo (sem navegacao
                // real) e mantido.
            }

            // Fix (Player3D - pasta como padrao): a forma moderna de um
            // player de musica local agrupar faixas e pela PASTA onde os
            // arquivos estao - e assim que a maioria dos players simples
            // funciona por padrao, e BUCKET_ID nunca e nulo pra midia
            // local. ALBUM_ID so e usado como criterio quando a pasta
            // nao rende fila usavel (pasta com 1 arquivo so, ou sem
            // BUCKET_ID por algum motivo raro) - nesse caso, album ainda
            // pode agrupar faixas que o usuario colocou em pastas
            // diferentes mas com a mesma tag de album (import de app de
            // musica, por exemplo).
            Result byBucket = null;
            if (mBucketId >= 0) {
                String sortOrder = AudioColumns.TITLE + " ASC";
                byBucket = queryBy(AudioColumns.BUCKET_ID, mBucketId, sortOrder,
                        currentId, "pasta");
                if (isUsable(byBucket)) {
                    Log.i(TAG, "fila carregada por pasta=" + mBucketId
                            + " (" + byBucket.uris.length + " faixas)");
                    return byBucket;
                }
            }

            if (mAlbumId >= 0) {
                String sortOrder = AudioColumns.TRACK + " ASC, " + AudioColumns.TITLE + " ASC";
                Result byAlbum = queryBy(AudioColumns.ALBUM_ID, mAlbumId, sortOrder,
                        currentId, "album");
                if (isUsable(byAlbum)) {
                    Log.i(TAG, "pasta sem faixas suficientes (bucketId=" + mBucketId
                            + "), fila carregada por album=" + mAlbumId
                            + " (" + byAlbum.uris.length + " faixas)");
                    return byAlbum;
                }
            }

            Log.i(TAG, "fila vazia para bucketId=" + mBucketId + " albumId=" + mAlbumId
                    + " currentId=" + currentId + " - nenhum criterio encontrou mais de 1 faixa");
            return byBucket != null ? byBucket : new Result();
        }

        @Override
        protected void onPostExecute(Result result) {
            // So aplica se a faixa que estava tocando quando o carregamento
            // comecou ainda for a mesma que esta tocando agora (evita
            // sobrescrever a fila com dados de uma faixa antiga se o
            // usuario ja navegou de novo antes do carregamento terminar).
            if (mCurrentUri == null || !mCurrentUri.equals(mCurrentUriAtLoadTime)) {
                Log.i(TAG, "fila (" + result.source + ") descartada: faixa mudou antes do "
                        + "carregamento terminar (esperado=" + mCurrentUriAtLoadTime
                        + " atual=" + mCurrentUri + ")");
                return;
            }
            if (!isUsable(result)) {
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

    // Fix (Player3D): seekTo() sozinho e assincrono no MediaPlayer -
    // getCurrentPosition() logo em seguida pode ainda devolver a posicao
    // ANTIGA por um instante, ate o decoder de fato pular pro novo ponto.
    // O log abaixo ajuda a confirmar, num proximo logcat, se algum
    // arquivo especifico esta demorando muito ou falhando o seek (nesse
    // caso onSeekComplete() abaixo nunca dispara pra essa chamada, ou
    // dispara com getCurrentPosition() bem longe do milliseconds pedido).
    public void seekTo(int milliseconds) {
        if (mMediaPlayer != null && !mPreparing) {
            Log.i(TAG, "seekTo(" + milliseconds + ") pedido, posicao atual antes = "
                    + mMediaPlayer.getCurrentPosition());
            mMediaPlayer.seekTo(milliseconds);
        } else {
            Log.w(TAG, "seekTo(" + milliseconds + ") ignorado - mMediaPlayer="
                    + mMediaPlayer + " mPreparing=" + mPreparing);
        }
    }

    // Fix (Player3D): so publica o novo PlaybackState (posicao) DEPOIS
    // que o MediaPlayer confirma que o seek de fato terminou - antes
    // disso, updatePlaybackState() era chamado no proprio seekTo(),
    // publicando uma posicao que o decoder ainda nao tinha alcancado de
    // verdade. Isso fazia a UI (slider/lockscreen) mostrar a posicao NOVA
    // (pedida) enquanto o audio real ainda tocava da posicao ANTIGA, ate
    // o decoder alcancar sozinho - sensacao de audio "atrasado" ou preso.
    @Override
    public void onSeekComplete(MediaPlayer mp) {
        Log.i(TAG, "onSeekComplete: posicao real agora = " + mp.getCurrentPosition());
        updatePlaybackState();
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
        updatePlaybackState();
        updateNotification();
    }

    public void toggleRepeatOne() {
        mRepeatMode = (mRepeatMode == RepeatMode.ONE) ? RepeatMode.OFF : RepeatMode.ONE;
        if (mCallback != null) mCallback.onRepeatModeChanged(mRepeatMode);
        updatePlaybackState();
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
            Log.i(TAG, "requestNext: sem fila carregada (mQueueUris="
                    + (mQueueUris == null ? "null" : mQueueUris.length)
                    + ", mQueueIndex=" + mQueueIndex + ") - " +
                    (fromUserAction ? "pausando" : "avisando fim sem fila"));
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

    // Fix (Player3D): publica titulo/artista/capa/duracao na MediaSession.
    // Sem isso, o sistema Android nao consegue desenhar o slider de
    // progresso na notificacao (MediaStyle) porque nao sabe a duracao
    // total da faixa - o slider simplesmente some. Chamado sempre junto
    // de updatePlaybackState(), nunca sozinho, para manter metadata e
    // estado sempre consistentes antes de toda atualizacao da notificacao.
    private void publishMediaMetadata() {
        if (mMediaSession == null) return;
        MediaMetadata.Builder builder = new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, mCurrentTitle)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, mCurrentArtist)
                .putLong(MediaMetadata.METADATA_KEY_DURATION, getDuration());
        if (mCurrentCover != null) {
            builder.putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART, mCurrentCover);
        }
        mMediaSession.setMetadata(builder.build());
    }

    private void updatePlaybackState() {
        publishMediaMetadata();
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

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
 */
package com.android.gallery3d.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.net.Uri;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;
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
    }

    /**
     * Implementado por quem tem a lista/album atual (MoviePlayer, a partir
     * do Passo 4) para o Service saber qual e a proxima/anterior faixa
     * quando o pedido vem da notificacao, da tela de bloqueio, ou dos
     * botoes da propria tela de reproducao - e a mesma fonte de verdade
     * descrita no item 9.3 da especificacao.
     */
    public interface QueueController {
        void onNextRequested();
        void onPreviousRequested();
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
    private QueueController mQueueController;

    private Uri mCurrentUri;
    private String mCurrentTitle = "";
    private String mCurrentArtist = "";
    private Bitmap mCurrentCover;

    private RepeatMode mRepeatMode = RepeatMode.OFF;
    private boolean mPreparing = false;

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
                requestNext();
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
                requestNext();
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

    public void setQueueController(QueueController controller) {
        mQueueController = controller;
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

    @Override
    public void onPrepared(MediaPlayer mp) {
        mPreparing = false;
        mp.start();
        updatePlaybackState();
        notifyState(true);
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
        // Repetir todas ou tocar a proxima faixa da fila e decisao de quem
        // controla a fila (MoviePlayer) - o Service so avisa que acabou.
        requestNext();
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

    /**
     * Clique curto/duplo de "faixa anterior": se ja passou de 3s tocando a
     * faixa atual, volta pro inicio dela; senao, pede a faixa anterior de
     * verdade pra quem controla a fila.
     */
    private void requestPrevious() {
        if (mMediaPlayer != null && !mPreparing && mMediaPlayer.getCurrentPosition() > PREVIOUS_RESTART_THRESHOLD_MS) {
            seekTo(0);
            return;
        }
        if (mQueueController != null) {
            mQueueController.onPreviousRequested();
        }
    }

    private void requestNext() {
        if (mQueueController != null) {
            mQueueController.onNextRequested();
        }
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
                .setState(state, getCurrentPosition(), 1.0f)
                .addCustomAction(ACTION_TOGGLE_REPEAT_ALL,
                        getString(R.string.player3d_repeat_all),
                        R.drawable.ic_vidcontrol_repeat_all)
                .addCustomAction(ACTION_TOGGLE_REPEAT_ONE,
                        getString(R.string.player3d_repeat_one),
                        R.drawable.ic_vidcontrol_repeat_one);

        mMediaSession.setPlaybackState(builder.build());

        android.media.MediaMetadata.Builder metadata = new android.media.MediaMetadata.Builder()
                .putString(android.media.MediaMetadata.METADATA_KEY_TITLE, mCurrentTitle)
                .putString(android.media.MediaMetadata.METADATA_KEY_ARTIST, mCurrentArtist)
                .putLong(android.media.MediaMetadata.METADATA_KEY_DURATION, getDuration());
        if (mCurrentCover != null) {
            metadata.putBitmap(android.media.MediaMetadata.METADATA_KEY_ALBUM_ART, mCurrentCover);
        }
        mMediaSession.setMetadata(metadata.build());
    }

    // ---------------------------------------------------------------------
    // Notificacao (5 botoes: Repetir todas - Anterior - Play/Pause -
    // Proxima - Repetir uma), na mesma ordem da tela de reproducao (Passo
    // 4.2): ALL e Anterior a direita do play/pause, Proxima e Repetir Uma a
    // esquerda.
    // ---------------------------------------------------------------------

    private void createNotificationChannel() {
        mNotificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    getString(R.string.player3d_notification_channel_name),
                    NotificationManager.IMPORTANCE_LOW);
            channel.setDescription(getString(R.string.player3d_notification_channel_description));
            mNotificationManager.createNotificationChannel(channel);
        }
    }

    private PendingIntent actionPendingIntent(String action) {
        Intent intent = new Intent(this, MusicPlaybackService.class);
        intent.setAction(action);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return PendingIntent.getService(this, action.hashCode(), intent, flags);
    }

    private Notification buildNotification() {
        boolean playing = isPlaying();
        // Nota: o estado visual "ativado" (ALL/1 destacado) dos botoes e
        // especificado no Passo 4.2 para a tela de reproducao; a notificacao
        // usa aqui o mesmo icone monocromatico nos dois estados.

        Notification.Action repeatAll = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_repeat_all,
                getString(R.string.player3d_repeat_all),
                actionPendingIntent(ACTION_TOGGLE_REPEAT_ALL)).build();

        Notification.Action previous = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_previous,
                getString(R.string.player3d_previous),
                actionPendingIntent(ACTION_PREVIOUS)).build();

        Notification.Action playPause = new Notification.Action.Builder(
                playing ? R.drawable.ic_vidcontrol_pause : R.drawable.ic_vidcontrol_play,
                getString(playing ? R.string.player3d_pause : R.string.player3d_play),
                actionPendingIntent(ACTION_PLAY_PAUSE)).build();

        Notification.Action next = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_next,
                getString(R.string.player3d_next),
                actionPendingIntent(ACTION_NEXT)).build();

        Notification.Action repeatOne = new Notification.Action.Builder(
                R.drawable.ic_vidcontrol_repeat_one,
                getString(R.string.player3d_repeat_one),
                actionPendingIntent(ACTION_TOGGLE_REPEAT_ONE)).build();

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

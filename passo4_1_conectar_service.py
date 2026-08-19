#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passo 4.1 - Conectar MoviePlayer.java ao MusicPlaybackService (Player3D)

O que este script faz (item 9.3 da especificacao, feito aqui no Passo 4
como o proprio Passo 9 ja previa):
1. Reescreve app/src/main/java/com/android/gallery3d/app/MoviePlayer.java:
   - Troca o motor de VideoView para MediaPlayer puro hospedado no
     MusicPlaybackService (Passo 9) - MoviePlayer vira cliente do Service
     via bindService()/Binder, implementando MusicPlaybackService.Callback
     e MusicPlaybackService.QueueController.
   - mCoverView (ImageView) mostra a capa da faixa atual, extraida do
     proprio Uri (mesma tecnica do Passo 1.5: capa embutida via
     MediaMetadataRetriever, com fallback pra capa do album).
   - Remove o bloco de "esconder o VideoView por um instante" (nao se
     aplica mais a audio).
   - Mantem a assinatura publica da classe (construtor, onPause/onResume/
     onDestroy/onSaveInstanceState/onKeyDown/onKeyUp/onCompletion) intacta,
     entao MovieActivity.java e PhotoPage.java NAO precisam mudar.
2. Reescreve app/src/main/res/layout/movie_view.xml: troca a tag
   <VideoView android:id="@+id/surface_view" .../> por um <ImageView>
   com o mesmo id (o findViewById em MoviePlayer.java continua igual).

O que este script NAO faz (fica pro Passo 4.2, proximo):
- Os 4 botoes novos (Repetir todas / Anterior / Proxima / Repetir uma) em
  CommonControllerOverlay.java/MovieControllerOverlay.java.
- Fila/playlist real (onNextRequested/onPreviousRequested tem, por ora,
  um comportamento minimo e documentado no proprio codigo).
- O botao do editor de fotos na tela de reproducao (item 4.3).

trim_view.xml e TrimVideo.java NAO sao tocados por este script: usam a
mesma id "surface_view" mas sao uma tela separada (recorte de video), fora
do escopo do Passo 4 - a especificacao so lista MoviePlayer.java e os
ControllerOverlay para este passo.

Rode este script na RAIZ do projeto (~/Galeria3D no Termux):
    python3 passo4_1_conectar_service.py

Regras seguidas (workflow combinado):
- Falha cedo se pre-requisitos (Passo 9) nao estiverem no estado esperado,
  sem tocar em nada.
- Faz backup de cada arquivo existente que for editado, FORA da arvore
  res/ (pasta passo4_backups/ na raiz do projeto, espelhando o caminho) -
  ver a licao aprendida no handoff do Passo 9.
- E idempotente: rodar de novo depois de aplicado nao duplica nem corrompe
  nada, so avisa que ja foi aplicado.
- Termina com verificacao (grep) confirmando que nao sobrou VideoView em
  nenhum dos dois arquivos e que os pontos de conexao com o Service estao
  presentes.
"""

import os
import sys

MOVIE_PLAYER_PATH = "app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"
MOVIE_VIEW_LAYOUT_PATH = "app/src/main/res/layout/movie_view.xml"
SERVICE_JAVA_PATH = "app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java"
COVER_PLACEHOLDER_PATH = "app/src/main/res/drawable-nodpi/ic_audio_cover_placeholder.png"
BACKUP_DIR = "passo4_backups"

REQUIRED_FILES = [MOVIE_PLAYER_PATH, MOVIE_VIEW_LAYOUT_PATH, SERVICE_JAVA_PATH,
                   COVER_PLACEHOLDER_PATH]


def fail(msg):
    print("ERRO: " + msg)
    sys.exit(1)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def backup(path):
    # Backups vivem FORA da arvore res/ (passo4_backups/ na raiz do
    # projeto, espelhando o caminho original) - ver a licao do Passo 9
    # sobre nao deixar nada que nao termine em .xml dentro de res/values/.
    bak = os.path.join(BACKUP_DIR, path + ".bak_passo4_1")
    if not os.path.isfile(bak):
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        write(bak, read(path))
        print("Backup criado: %s" % bak)
    else:
        print("Backup ja existia, mantido: %s" % bak)


def check_prereqs():
    for f in REQUIRED_FILES:
        if not os.path.isfile(f):
            fail(
                "arquivo esperado nao encontrado: %s\n"
                "Rode este script na raiz do projeto (~/Galeria3D), depois "
                "do Passo 9 (passo9_service_notificacao.py)." % f
            )
    service = read(SERVICE_JAVA_PATH)
    for marker in ("public class LocalBinder", "public void playTrack(",
                   "interface Callback", "interface QueueController"):
        if marker not in service:
            fail(
                "MusicPlaybackService.java nao parece ter a API esperada "
                "do Passo 9 (%r nao encontrado). Rode o Passo 9 antes "
                "deste script." % marker
            )


def already_applied():
    if not os.path.isfile(MOVIE_PLAYER_PATH):
        return False
    content = read(MOVIE_PLAYER_PATH)
    return "MusicPlaybackService.Callback" in content


def apply_movie_player():
    backup(MOVIE_PLAYER_PATH)
    write(MOVIE_PLAYER_PATH, MOVIE_PLAYER_JAVA)
    print("Reescrito: %s (%d bytes)" % (MOVIE_PLAYER_PATH, len(MOVIE_PLAYER_JAVA)))


def apply_movie_view_layout():
    current = read(MOVIE_VIEW_LAYOUT_PATH)
    if "<ImageView" in current and "surface_view" in current:
        print("Aviso: %s ja usa ImageView, mantido." % MOVIE_VIEW_LAYOUT_PATH)
        return
    backup(MOVIE_VIEW_LAYOUT_PATH)
    write(MOVIE_VIEW_LAYOUT_PATH, MOVIE_VIEW_XML)
    print("Reescrito: %s (%d bytes)" % (MOVIE_VIEW_LAYOUT_PATH, len(MOVIE_VIEW_XML)))


def verify():
    print("\n--- Verificacao final ---")
    problems = []

    mp = read(MOVIE_PLAYER_PATH)
    if "import android.widget.VideoView" in mp or "VideoView mVideoView" in mp \
            or "(VideoView)" in mp:
        problems.append("MoviePlayer.java ainda usa a classe VideoView")
    if "MusicPlaybackService.Callback" not in mp:
        problems.append("MoviePlayer.java nao implementa MusicPlaybackService.Callback")
    if "MusicPlaybackService.QueueController" not in mp:
        problems.append("MoviePlayer.java nao implementa MusicPlaybackService.QueueController")
    if "bindService(" not in mp:
        problems.append("MoviePlayer.java nao chama bindService()")
    if "unbindService(" not in mp:
        problems.append("MoviePlayer.java nao chama unbindService() (vazamento de bind)")

    layout = read(MOVIE_VIEW_LAYOUT_PATH)
    if "<VideoView" in layout:
        problems.append("movie_view.xml ainda usa a tag <VideoView>")
    if 'android:id="@+id/surface_view"' not in layout:
        problems.append("movie_view.xml perdeu o id surface_view")

    if problems:
        print("Encontrados problemas na verificacao final:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)

    print("Tudo certo: VideoView removido, MoviePlayer conectado ao Service.")


def main():
    check_prereqs()
    if already_applied():
        print(
            "Aviso: %s ja foi conectado ao MusicPlaybackService (Passo 4.1 "
            "ja aplicado). Nada a fazer." % MOVIE_PLAYER_PATH
        )
        # Ainda assim confere/aplica o layout, caso so um dos dois tenha
        # sido aplicado numa execucao anterior interrompida.
        apply_movie_view_layout()
        verify()
        return
    apply_movie_player()
    apply_movie_view_layout()
    verify()
    print("\nPasso 4.1 aplicado. Agora rode: ./gradlew assembleDebug")
    print(
        "Proximo (Passo 4.2): os 4 botoes novos (ALL/Anterior/Proxima/1) em "
        "CommonControllerOverlay.java/MovieControllerOverlay.java."
    )


MOVIE_PLAYER_JAVA = """/*
 * Copyright (C) 2009 The Android Open Source Project
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

package com.android.gallery3d.app;

import android.annotation.TargetApi;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.ContentResolver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.DialogInterface.OnCancelListener;
import android.content.DialogInterface.OnClickListener;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ServiceConnection;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.AudioManager;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.provider.MediaStore.Audio.Albums;
import android.provider.MediaStore.Audio.AudioColumns;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;

import com.android.gallery3d.R;
import com.android.gallery3d.common.ApiHelper;
import com.android.gallery3d.common.BlobCache;
import com.android.gallery3d.util.CacheManager;
import com.android.gallery3d.util.GalleryUtils;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;

/*
 * Passo 4.1 (Player3D) - motor de renderizacao trocado de VideoView para
 * MediaPlayer puro. Desde o Passo 9, o MediaPlayer real nao mora mais aqui:
 * mora no MusicPlaybackService, que roda em foreground e sobrevive mesmo
 * com a tela de reproducao fechada. Esta classe virou um cliente do
 * Service via bindService()/Binder - implementa MusicPlaybackService.Callback
 * (estado de reproducao/erro) e MusicPlaybackService.QueueController
 * (proxima/anterior faixa), que e a mesma fonte de verdade usada pela
 * notificacao e pela tela de bloqueio (item 9.3 da especificacao).
 *
 * O app ainda nao tem uma fila/playlist real (isso e trabalho do Passo 4.2
 * em diante, quando os botoes de Proxima/Anterior existirem de verdade).
 * Ate la, onNextRequested()/onPreviousRequested() tem um comportamento
 * honesto e minimo: "proxima" ao fim da faixa == fim da reproducao (mesmo
 * comportamento que o antigo onCompletion() de video tinha), e "anterior"
 * volta para o inicio da faixa atual.
 */
public class MoviePlayer implements
        MusicPlaybackService.Callback, MusicPlaybackService.QueueController,
        ControllerOverlay.Listener {
    @SuppressWarnings("unused")
    private static final String TAG = "MoviePlayer";

    private static final String KEY_VIDEO_POSITION = "video-position";
    private static final String KEY_RESUMEABLE_TIME = "resumeable-timeout";

    // These are constants in KeyEvent, appearing on API level 11.
    private static final int KEYCODE_MEDIA_PLAY = 126;
    private static final int KEYCODE_MEDIA_PAUSE = 127;

    // Copied from MediaPlaybackService in the Music Player app.
    private static final String SERVICECMD = "com.android.music.musicservicecommand";
    private static final String CMDNAME = "command";
    private static final String CMDPAUSE = "pause";

    // Tamanho alvo (em pixels) do bitmap de capa carregado para a tela de
    // reproducao. Mesma logica de extracao do Passo 1.5 (LocalAudio), mas
    // duplicada aqui de forma enxuta porque este arquivo so tem o Uri da
    // faixa (nao uma instancia de LocalAudio) - ver classe TrackMetadataLoader.
    private static final int COVER_TARGET_SIZE = 1024;

    // If we resume the acitivty with in RESUMEABLE_TIMEOUT, we will keep playing.
    // Otherwise, we pause the player.
    private static final long RESUMEABLE_TIMEOUT = 3 * 60 * 1000; // 3 mins

    private Context mContext;
    // AlertDialog.Builder precisa de um Context de Activity de verdade (nao
    // o ApplicationContext usado no resto da classe) - guardado a parte so
    // para o dialogo de "retomar de onde parou" em showResumeDialog().
    private final Context mActivityContext;
    private final ImageView mCoverView;
    private final View mRootView;
    private final Bookmarker mBookmarker;
    private final Uri mUri;
    private final Handler mHandler = new Handler();
    private final AudioBecomingNoisyReceiver mAudioBecomingNoisyReceiver;
    private final MovieControllerOverlay mController;

    private MusicPlaybackService mService;
    private boolean mServiceBound;
    private boolean mMetadataLoaded;
    private boolean mStarted;
    // Posicao (ms) para onde pular assim que a faixa comecar a tocar de
    // verdade (retomar de um bookmark, ou retomar apos recriacao da
    // Activity). 0 = comecar do inicio, sem seek pendente.
    private int mPendingSeekPositionMs;

    private long mResumeableTime = Long.MAX_VALUE;
    private int mVideoPosition = 0;
    private boolean mHasPaused = false;
    private int mLastSystemUiVis = 0;

    // If the time bar is being dragged.
    private boolean mDragging;

    // If the time bar is visible.
    private boolean mShowing;

    private final Runnable mPlayingChecker = new Runnable() {
        @Override
        public void run() {
            if (mService != null && mService.isPlaying()) {
                mController.showPlaying();
            } else {
                mHandler.postDelayed(mPlayingChecker, 250);
            }
        }
    };

    private final Runnable mProgressChecker = new Runnable() {
        @Override
        public void run() {
            int pos = setProgress();
            mHandler.postDelayed(mProgressChecker, 1000 - (pos % 1000));
        }
    };

    private final ServiceConnection mServiceConnection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder binder) {
            mService = ((MusicPlaybackService.LocalBinder) binder).getService();
            mServiceBound = true;
            mService.setCallback(MoviePlayer.this);
            mService.setQueueController(MoviePlayer.this);
            maybeStartPlayback();
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            mService = null;
            mServiceBound = false;
        }
    };

    public MoviePlayer(View rootView, final MovieActivity movieActivity,
            Uri videoUri, Bundle savedInstance, boolean canReplay) {
        mContext = movieActivity.getApplicationContext();
        mActivityContext = movieActivity;
        mRootView = rootView;
        mCoverView = (ImageView) rootView.findViewById(R.id.surface_view);
        mCoverView.setScaleType(ImageView.ScaleType.CENTER_CROP);
        mBookmarker = new Bookmarker(movieActivity);
        mUri = videoUri;

        mController = new MovieControllerOverlay(mContext);
        ((ViewGroup)rootView).addView(mController.getView());
        mController.setListener(this);
        mController.setCanReplay(canReplay);

        mCoverView.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                mController.show();
                return true;
            }
        });

        setOnSystemUiVisibilityChangeListener();
        // Hide system UI by default
        showSystemUi(false);

        mAudioBecomingNoisyReceiver = new AudioBecomingNoisyReceiver();
        mAudioBecomingNoisyReceiver.register();

        Intent i = new Intent(SERVICECMD);
        i.putExtra(CMDNAME, CMDPAUSE);
        movieActivity.sendBroadcast(i);

        if (savedInstance != null) { // this is a resumed activity
            mVideoPosition = savedInstance.getInt(KEY_VIDEO_POSITION, 0);
            mResumeableTime = savedInstance.getLong(KEY_RESUMEABLE_TIME, Long.MAX_VALUE);
            mHasPaused = true;
        }

        // Faixa/capa (Passo 1.5) e conexao ao Service (Passo 9) sao
        // assincronas e independentes uma da outra - a reproducao so
        // comeca de fato (maybeStartPlayback) quando as duas terminarem.
        new TrackMetadataLoader().execute();
        bindPlaybackService();
    }

    private void bindPlaybackService() {
        Intent serviceIntent = new Intent(mContext, MusicPlaybackService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            mContext.startForegroundService(serviceIntent);
        } else {
            mContext.startService(serviceIntent);
        }
        mContext.bindService(serviceIntent, mServiceConnection, Context.BIND_AUTO_CREATE);
    }

    // Metadados (titulo/artista) + capa de uma faixa de audio a partir do
    // Uri puro (MoviePlayer nao recebe uma instancia de LocalAudio, so o
    // Uri via PhotoPage.playVideo() -> item.getPlayUri()). Mesma tecnica de
    // extracao de capa do Passo 1.5 (embutida no arquivo via
    // MediaMetadataRetriever, com fallback para a capa do album via
    // MediaStore.Audio.Albums), reimplementada aqui de forma enxuta e sem
    // cache (o cache de capa por album ja existe em LocalAudio/ImageCacheService
    // para a grade principal; aqui e uma unica leitura pontual).
    private final class TrackMetadataLoader extends AsyncTask<Void, Void, TrackMetadataLoader.Result> {
        final class Result {
            String title;
            String artist;
            Bitmap cover;
        }

        @Override
        protected Result doInBackground(Void... params) {
            Result result = new Result();
            long albumId = -1;
            ContentResolver resolver = mContext.getContentResolver();
            String[] projection = {
                    AudioColumns.TITLE, AudioColumns.ARTIST, AudioColumns.ALBUM_ID,
            };
            Cursor cursor = null;
            try {
                cursor = resolver.query(mUri, projection, null, null, null);
                if (cursor != null && cursor.moveToFirst()) {
                    result.title = cursor.getString(0);
                    result.artist = cursor.getString(1);
                    albumId = cursor.getLong(2);
                }
            } catch (Throwable t) {
                Log.w(TAG, "falha ao ler metadados de " + mUri, t);
            } finally {
                if (cursor != null) cursor.close();
            }

            result.cover = decodeEmbeddedCover();
            if (result.cover == null && albumId >= 0) {
                result.cover = decodeAlbumArtFallback(resolver, albumId);
            }
            return result;
        }

        private Bitmap decodeEmbeddedCover() {
            MediaMetadataRetriever retriever = new MediaMetadataRetriever();
            try {
                retriever.setDataSource(mContext, mUri);
                byte[] embedded = retriever.getEmbeddedPicture();
                if (embedded == null) return null;
                return BitmapFactory.decodeByteArray(embedded, 0, embedded.length);
            } catch (OutOfMemoryError e) {
                Log.w(TAG, "OOM decodificando capa embutida de " + mUri);
                return null;
            } catch (Throwable t) {
                Log.w(TAG, "sem capa embutida para " + mUri);
                return null;
            } finally {
                try {
                    retriever.release();
                } catch (Throwable ignored) {
                }
            }
        }

        @TargetApi(Build.VERSION_CODES.Q)
        private Bitmap decodeAlbumArtFallback(ContentResolver resolver, long albumId) {
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

        // Pre-Android 10: MediaStore.Audio.Albums.ALBUM_ART e uma coluna de
        // caminho de arquivo apontando direto pra capa em cache no disco.
        private Bitmap decodeAlbumArtLegacy(ContentResolver resolver, long albumId) {
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

        @Override
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

    private String mTrackTitle = "";
    private String mTrackArtist = "";
    private Bitmap mTrackCover;

    // So chama service.playTrack(...) quando o bind ao Service E o carregamento
    // de metadados/capa (ambos assincronos, ver construtor) tiverem terminado.
    private void maybeStartPlayback() {
        if (mStarted || !mServiceBound || !mMetadataLoaded) return;
        mStarted = true;

        if (mVideoPosition > 0) {
            // Reproducao retomada apos a Activity ser recriada (ex.: giro de
            // tela) no meio de uma faixa.
            playCurrentTrack(mVideoPosition);
            return;
        }

        final Integer bookmark = mBookmarker.getBookmark(mUri);
        if (bookmark != null) {
            showResumeDialog(mActivityContext, bookmark);
        } else {
            startVideo();
        }
    }

    @TargetApi(Build.VERSION_CODES.JELLY_BEAN)
    private void setOnSystemUiVisibilityChangeListener() {
        if (!ApiHelper.HAS_VIEW_SYSTEM_UI_FLAG_HIDE_NAVIGATION) return;

        // When the user touches the screen or uses some hard key, the framework
        // will change system ui visibility from invisible to visible. We show
        // the media control and enable system UI (e.g. ActionBar) to be visible at this point
        mCoverView.setOnSystemUiVisibilityChangeListener(
                new View.OnSystemUiVisibilityChangeListener() {
            @Override
            public void onSystemUiVisibilityChange(int visibility) {
                int diff = mLastSystemUiVis ^ visibility;
                mLastSystemUiVis = visibility;
                if ((diff & View.SYSTEM_UI_FLAG_HIDE_NAVIGATION) != 0
                        && (visibility & View.SYSTEM_UI_FLAG_HIDE_NAVIGATION) == 0) {
                    mController.show();
                }
            }
        });
    }

    @SuppressWarnings("deprecation")
    @TargetApi(Build.VERSION_CODES.JELLY_BEAN)
    private void showSystemUi(boolean visible) {
        if (!ApiHelper.HAS_VIEW_SYSTEM_UI_FLAG_LAYOUT_STABLE) return;

        int flag = View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE;
        if (!visible) {
            // We used the deprecated "STATUS_BAR_HIDDEN" for unbundling
            flag |= View.STATUS_BAR_HIDDEN | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION;
        }
        mCoverView.setSystemUiVisibility(flag);
    }

    public void onSaveInstanceState(Bundle outState) {
        outState.putInt(KEY_VIDEO_POSITION, mService != null ? mService.getCurrentPosition() : mVideoPosition);
        outState.putLong(KEY_RESUMEABLE_TIME, mResumeableTime);
    }

    private void showResumeDialog(Context context, final int bookmark) {
        AlertDialog.Builder builder = new AlertDialog.Builder(context);
        builder.setTitle(R.string.resume_playing_title);
        builder.setMessage(String.format(
                context.getString(R.string.resume_playing_message),
                GalleryUtils.formatDuration(context, bookmark / 1000)));
        builder.setOnCancelListener(new OnCancelListener() {
            @Override
            public void onCancel(DialogInterface dialog) {
                onCompletion();
            }
        });
        builder.setPositiveButton(
                R.string.resume_playing_resume, new OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                playCurrentTrack(bookmark);
            }
        });
        builder.setNegativeButton(
                R.string.resume_playing_restart, new OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                startVideo();
            }
        });
        builder.show();
    }

    public void onPause() {
        mHasPaused = true;
        mHandler.removeCallbacksAndMessages(null);
        if (mService != null) {
            mVideoPosition = mService.getCurrentPosition();
            mBookmarker.setBookmark(mUri, mVideoPosition, mService.getDuration());
        }
        mResumeableTime = System.currentTimeMillis() + RESUMEABLE_TIMEOUT;
    }

    public void onResume() {
        if (mHasPaused) {
            // Se dormimos por tempo demais, pausa a reproducao.
            if (System.currentTimeMillis() > mResumeableTime && mService != null) {
                pauseVideo();
            }
        }
        mHandler.post(mProgressChecker);
    }

    public void onDestroy() {
        mAudioBecomingNoisyReceiver.unregister();
        // Ao contrario do VideoView antigo, NAO paramos a reproducao aqui:
        // o MediaPlayer mora no MusicPlaybackService (Passo 9), que continua
        // tocando em foreground mesmo com a tela de reproducao fechada -
        // esse e o motivo de ele existir. So desfazemos o bind.
        if (mServiceBound) {
            if (mService != null) {
                mService.setCallback(null);
                mService.setQueueController(null);
            }
            mContext.unbindService(mServiceConnection);
            mServiceBound = false;
        }
    }

    // This updates the time bar display (if necessary). It is called every
    // second by mProgressChecker and also from places where the time bar needs
    // to be updated immediately.
    private int setProgress() {
        if (mDragging || !mShowing || mService == null) {
            return 0;
        }
        int position = mService.getCurrentPosition();
        int duration = mService.getDuration();
        mController.setTimes(position, duration, 0, 0);
        return position;
    }

    private void startVideo() {
        playCurrentTrack(0);
    }

    // Pede ao Service pra tocar a faixa atual (sempre do inicio - o
    // MediaPlayer nao suporta abrir ja numa posicao). Se seekPositionMs > 0,
    // o pulo acontece assim que a faixa comecar a tocar de verdade (ver
    // onPlaybackStateChanged).
    private void playCurrentTrack(int seekPositionMs) {
        mPendingSeekPositionMs = seekPositionMs;
        mController.showLoading();
        mHandler.removeCallbacks(mPlayingChecker);
        mHandler.postDelayed(mPlayingChecker, 250);
        if (mService != null) {
            mService.playTrack(mUri, mTrackTitle, mTrackArtist, mTrackCover);
        }
    }

    private void playVideo() {
        if (mService != null) {
            mService.resume();
        }
        mController.showPlaying();
        setProgress();
    }

    private void pauseVideo() {
        if (mService != null) {
            mService.pause();
        }
        mController.showPaused();
    }

    // Below are notifications from MusicPlaybackService (Passo 9,
    // MusicPlaybackService.Callback) - mesma fonte de verdade usada pela
    // notificacao e pela tela de bloqueio.
    @Override
    public void onPlaybackStateChanged(boolean isPlaying) {
        if (mPendingSeekPositionMs > 0 && mService != null) {
            mService.seekTo(mPendingSeekPositionMs);
            mPendingSeekPositionMs = 0;
        }
        if (isPlaying) {
            mController.showPlaying();
        } else {
            mController.showPaused();
        }
        setProgress();
    }

    @Override
    public void onRepeatModeChanged(MusicPlaybackService.RepeatMode mode) {
        // Estado visual dos botoes de repeat (ALL/1) e trabalho do Passo 4.2,
        // quando os botoes existirem de verdade nesta tela.
    }

    @Override
    public void onTrackError(Exception error) {
        mHandler.removeCallbacksAndMessages(null);
        mController.showErrorMessage("");
    }

    // Below are notifications from MusicPlaybackService.QueueController -
    // ainda nao existe fila/playlist real no app (isso chega a partir do
    // Passo 4.2/5). Ate la, comportamento minimo e honesto: fim da faixa
    // unica = fim da reproducao; "anterior" volta ao inicio da faixa atual.
    @Override
    public void onNextRequested() {
        mController.showEnded();
        onCompletion();
    }

    @Override
    public void onPreviousRequested() {
        if (mService != null) {
            mService.seekTo(0);
        }
    }

    public void onCompletion() {
    }

    // Below are notifications from ControllerOverlay
    @Override
    public void onPlayPause() {
        if (mService != null && mService.isPlaying()) {
            pauseVideo();
        } else {
            playVideo();
        }
    }

    @Override
    public void onSeekStart() {
        mDragging = true;
    }

    @Override
    public void onSeekMove(int time) {
        if (mService != null) {
            mService.seekTo(time);
        }
    }

    @Override
    public void onSeekEnd(int time, int start, int end) {
        mDragging = false;
        if (mService != null) {
            mService.seekTo(time);
        }
        setProgress();
    }

    @Override
    public void onShown() {
        mShowing = true;
        setProgress();
        showSystemUi(true);
    }

    @Override
    public void onHidden() {
        mShowing = false;
        showSystemUi(false);
    }

    @Override
    public void onReplay() {
        startVideo();
    }

    // Below are key events passed from MovieActivity.
    public boolean onKeyDown(int keyCode, KeyEvent event) {

        // Some headsets will fire off 7-10 events on a single click
        if (event.getRepeatCount() > 0) {
            return isMediaKey(keyCode);
        }

        boolean isPlaying = mService != null && mService.isPlaying();
        switch (keyCode) {
            case KeyEvent.KEYCODE_HEADSETHOOK:
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                if (isPlaying) {
                    pauseVideo();
                } else {
                    playVideo();
                }
                return true;
            case KEYCODE_MEDIA_PAUSE:
                if (isPlaying) {
                    pauseVideo();
                }
                return true;
            case KEYCODE_MEDIA_PLAY:
                if (!isPlaying) {
                    playVideo();
                }
                return true;
            case KeyEvent.KEYCODE_MEDIA_PREVIOUS:
            case KeyEvent.KEYCODE_MEDIA_NEXT:
                // TODO: Handle next / previous accordingly, for now we're
                // just consuming the events.
                return true;
        }
        return false;
    }

    public boolean onKeyUp(int keyCode, KeyEvent event) {
        return isMediaKey(keyCode);
    }

    private static boolean isMediaKey(int keyCode) {
        return keyCode == KeyEvent.KEYCODE_HEADSETHOOK
                || keyCode == KeyEvent.KEYCODE_MEDIA_PREVIOUS
                || keyCode == KeyEvent.KEYCODE_MEDIA_NEXT
                || keyCode == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE
                || keyCode == KeyEvent.KEYCODE_MEDIA_PLAY
                || keyCode == KeyEvent.KEYCODE_MEDIA_PAUSE;
    }

    // We want to pause when the headset is unplugged.
    private class AudioBecomingNoisyReceiver extends BroadcastReceiver {

        public void register() {
            mContext.registerReceiver(this,
                    new IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY));
        }

        public void unregister() {
            mContext.unregisterReceiver(this);
        }

        @Override
        public void onReceive(Context context, Intent intent) {
            if (mService != null && mService.isPlaying()) pauseVideo();
        }
    }
}

class Bookmarker {
    private static final String TAG = "Bookmarker";

    private static final String BOOKMARK_CACHE_FILE = "bookmark";
    private static final int BOOKMARK_CACHE_MAX_ENTRIES = 100;
    private static final int BOOKMARK_CACHE_MAX_BYTES = 10 * 1024;
    private static final int BOOKMARK_CACHE_VERSION = 1;

    private static final int HALF_MINUTE = 30 * 1000;
    private static final int TWO_MINUTES = 4 * HALF_MINUTE;

    private final Context mContext;

    public Bookmarker(Context context) {
        mContext = context;
    }

    public void setBookmark(Uri uri, int bookmark, int duration) {
        try {
            BlobCache cache = CacheManager.getCache(mContext,
                    BOOKMARK_CACHE_FILE, BOOKMARK_CACHE_MAX_ENTRIES,
                    BOOKMARK_CACHE_MAX_BYTES, BOOKMARK_CACHE_VERSION);

            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            DataOutputStream dos = new DataOutputStream(bos);
            dos.writeUTF(uri.toString());
            dos.writeInt(bookmark);
            dos.writeInt(duration);
            dos.flush();
            cache.insert(uri.hashCode(), bos.toByteArray());
        } catch (Throwable t) {
            Log.w(TAG, "setBookmark failed", t);
        }
    }

    public Integer getBookmark(Uri uri) {
        try {
            BlobCache cache = CacheManager.getCache(mContext,
                    BOOKMARK_CACHE_FILE, BOOKMARK_CACHE_MAX_ENTRIES,
                    BOOKMARK_CACHE_MAX_BYTES, BOOKMARK_CACHE_VERSION);

            byte[] data = cache.lookup(uri.hashCode());
            if (data == null) return null;

            DataInputStream dis = new DataInputStream(
                    new ByteArrayInputStream(data));

            String uriString = DataInputStream.readUTF(dis);
            int bookmark = dis.readInt();
            int duration = dis.readInt();

            if (!uriString.equals(uri.toString())) {
                return null;
            }

            if ((bookmark < HALF_MINUTE) || (duration < TWO_MINUTES)
                    || (bookmark > (duration - HALF_MINUTE))) {
                return null;
            }
            return Integer.valueOf(bookmark);
        } catch (Throwable t) {
            Log.w(TAG, "getBookmark failed", t);
        }
        return null;
    }
}
"""

MOVIE_VIEW_XML = """<?xml version="1.0" encoding="utf-8"?>
<!-- Copyright (C) 2007 The Android Open Source Project

     Licensed under the Apache License, Version 2.0 (the "License");
     you may not use this file except in compliance with the License.
     You may obtain a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

     Unless required by applicable law or agreed to in writing, software
     distributed under the License is distributed on an "AS IS" BASIS,
     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
     See the License for the specific language governing permissions and
     limitations under the License.
-->

<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
        android:id="@+id/movie_view_root"
        android:background="@android:color/black"
        android:layout_width="match_parent"
        android:layout_height="match_parent">
    <!-- Passo 4.1: capa da faixa atual no lugar do VideoView (motor trocado
         para MediaPlayer puro, hospedado no MusicPlaybackService). -->
    <ImageView android:id="@+id/surface_view"
            android:layout_width="match_parent"
            android:layout_height="match_parent"
            android:layout_centerInParent="true"
            android:scaleType="centerCrop" />
</RelativeLayout>
"""

if __name__ == "__main__":
    main()

/*
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
import android.content.ContentUris;
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
import android.provider.MediaStore.Audio.Media;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.Toast;

import com.android.gallery3d.R;
import com.android.gallery3d.common.ApiHelper;
import com.android.gallery3d.common.BlobCache;
import com.android.gallery3d.util.CacheManager;
import com.android.gallery3d.util.GalleryUtils;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

/*
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
 */
public class MoviePlayer implements
        MusicPlaybackService.Callback, ControllerOverlay.Listener {
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
    // Fix (Player3D): albumId resolvido por TrackMetadataLoader, guardado
    // ate o Service estar vinculado para podermos pedir loadQueueForAlbum()
    // (as duas tasks assincronas do construtor - metadados e bind do
    // Service - nao tem ordem garantida entre si).
    private long mPendingAlbumId = -1;
    private boolean mQueueRequested;
    // Posicao (ms) para onde pular assim que a faixa comecar a tocar de
    // verdade (retomar de um bookmark, ou retomar apos recriacao da
    // Activity). 0 = comecar do inicio, sem seek pendente.
    private int mPendingSeekPositionMs;

    // Fix (Player3D): a fila de proxima/anterior faixa (mesmo album) agora
    // mora em MusicPlaybackService, nao aqui - ver comentario no topo de
    // MusicPlaybackService.java. MoviePlayer so guarda a Uri tocando
    // AGORA (atualizada via callback onTrackChanged()), nao a fila em si.
    // Uri da faixa TOCANDO agora - pode mudar ao navegar pela fila. mUri
    // (acima) continua sendo a faixa com que a tela foi aberta, usada so
    // para o bookmark de "retomar de onde parou" do fluxo original.
    private Uri mCurrentPlayUri;

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
        mCurrentPlayUri = videoUri;

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
            long albumId = -1;
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

            result.albumId = albumId;
            result.cover = decodeEmbeddedCover(mContext, mUri);
            if (result.cover == null && albumId >= 0) {
                result.cover = decodeAlbumArtFallback(resolver, albumId);
            }
            return result;
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
            mPendingAlbumId = result.albumId;
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
    }

    // Extracao de capa (embutida no arquivo, com fallback para a capa do
    // album via MediaStore) - usada por TrackMetadataLoader para a capa
    // da faixa com que a tela foi ABERTA originalmente. A navegacao de
    // fila (next/previous) tem sua propria copia equivalente dentro de
    // MusicPlaybackService (QueueCoverLoader), que carrega a capa das
    // OUTRAS faixas do album sem depender desta classe.
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

    @TargetApi(Build.VERSION_CODES.Q)
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

    // Pre-Android 10: MediaStore.Audio.Albums.ALBUM_ART e uma coluna de
    // caminho de arquivo apontando direto pra capa em cache no disco.
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

    private String mTrackTitle = "";
    private String mTrackArtist = "";
    private Bitmap mTrackCover;

    // So chama service.playTrack(...) quando o bind ao Service E o carregamento
    // de metadados/capa (ambos assincronos, ver construtor) tiverem terminado.
    private void maybeStartPlayback() {
        // Fix (Player3D): o pedido de fila so depende de Service vinculado
        // + albumId conhecido (nao do inicio da reproducao em si) - roda
        // assim que os dois estiverem prontos, uma unica vez.
        if (mServiceBound && mMetadataLoaded && !mQueueRequested) {
            mQueueRequested = true;
            requestQueueLoad(mPendingAlbumId);
        }

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
            // Fix (Player3D): salva o bookmark contra a faixa que esta
            // TOCANDO de verdade agora (mCurrentPlayUri pode ter mudado se
            // o usuario navegou pela fila), nao a faixa original com que a
            // tela foi aberta.
            mBookmarker.setBookmark(mCurrentPlayUri, mVideoPosition, mService.getDuration());
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
            mService.playTrack(mCurrentPlayUri, mTrackTitle, mTrackArtist, mTrackCover);
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
        mController.setRepeatModeVisual(mode);
    }

    @Override
    public void onTrackError(Exception error) {
        mHandler.removeCallbacksAndMessages(null);
        mController.showErrorMessage("");
    }

    // Fix (Player3D): a decisao de navegacao de fila (proxima/anterior)
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
    }

    // Passo 4.3 (Player3D): editar a capa da faixa atual. Reusa a capa JA
    // decodificada em memoria (mTrackCover, vinda de TrackMetadataLoader ou
    // QueueCoverLoader) - nao depende de LocalAudio/DataManager (que exigem
    // um caminho de arquivo local resolvido, infraestrutura que MovieActivity
    // nao tem). Salva a capa num arquivo temporario de cache, expoe via o
    // FileProvider ja configurado no projeto, e abre o mesmo editor de
    // fotos (FilterShowActivity) que PhotoPage.launchPhotoEditor() usa.
    @Override
    public void onEditCover() {
        if (mTrackCover == null) {
            Toast.makeText(mActivityContext, R.string.player3d_no_cover_to_edit,
                    Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            File cacheDir = new File(mContext.getCacheDir(), "audio_covers");
            if (!cacheDir.exists() && !cacheDir.mkdirs()) {
                Log.w(TAG, "nao foi possivel criar cache dir para capa: " + cacheDir);
                Toast.makeText(mActivityContext, R.string.player3d_no_cover_to_edit,
                        Toast.LENGTH_SHORT).show();
                return;
            }
            File coverFile = new File(cacheDir,
                    "cover_" + Math.abs(mCurrentPlayUri.hashCode()) + ".jpg");
            FileOutputStream out = new FileOutputStream(coverFile);
            try {
                mTrackCover.compress(Bitmap.CompressFormat.JPEG, 92, out);
            } finally {
                out.close();
            }
            Uri coverUri = androidx.core.content.FileProvider.getUriForFile(
                    mContext, mContext.getPackageName() + ".provider", coverFile);

            Intent intent = new Intent(PhotoPage.ACTION_NEXTGEN_EDIT);
            intent.setDataAndType(coverUri, "image/jpeg");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            if (mActivityContext.getPackageManager()
                    .queryIntentActivities(intent,
                            android.content.pm.PackageManager.MATCH_DEFAULT_ONLY).isEmpty()) {
                intent.setAction(Intent.ACTION_EDIT);
            }
            mActivityContext.startActivity(Intent.createChooser(intent, null));
        } catch (IOException e) {
            Log.w(TAG, "falha ao salvar capa temporaria para edicao", e);
            Toast.makeText(mActivityContext, R.string.player3d_no_cover_to_edit,
                    Toast.LENGTH_SHORT).show();
        }
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

    // Botoes novos da tela de reproducao (Passo 4.2). Previous/Next mandam
    // o MESMO Intent ACTION_PREVIOUS/ACTION_NEXT que a notificacao ja manda
    // (Passo 9) - o Service decide sozinho, com a MESMA logica de limiar de
    // 3s ja testada em requestPrevious(), se e reinicio da faixa atual ou
    // pedido de fila (onPreviousRequested/onNextRequested, ver acima).
    // Evita duplicar essa logica de limiar em dois lugares.
    @Override
    public void onPrevious() {
        sendPlaybackAction(MusicPlaybackService.ACTION_PREVIOUS);
    }

    @Override
    public void onNext() {
        sendPlaybackAction(MusicPlaybackService.ACTION_NEXT);
    }

    private void sendPlaybackAction(String action) {
        Intent intent = new Intent(mContext, MusicPlaybackService.class);
        intent.setAction(action);
        mContext.startService(intent);
    }

    @Override
    public void onToggleRepeatAll() {
        if (mService != null) {
            mService.toggleRepeatAll();
        }
    }

    @Override
    public void onToggleRepeatOne() {
        if (mService != null) {
            mService.toggleRepeatOne();
        }
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

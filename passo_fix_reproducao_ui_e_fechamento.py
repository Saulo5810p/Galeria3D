#!/usr/bin/env python3
"""
CORREÇÕES na tela de reprodução (Player3D) — pedidas após o Passo 5.

(A) BUG CRÍTICO: pause/next/previous fechando a tela de reprodução.

    Causa raiz confirmada: MovieActivity.onCreate() lê
    MediaStore.EXTRA_FINISH_ON_COMPLETION do Intent, com DEFAULT true
    quando a extra não está presente:
        intent.getBooleanExtra(MediaStore.EXTRA_FINISH_ON_COMPLETION, true)
    PhotoPage.playVideo() (o Intent que abre a tela de reprodução de
    áudio) nunca seta essa extra — então mFinishOnCompletion fica sempre
    true. Toda vez que MoviePlayer.onCompletion() roda (chamado pelo
    fallback "sem fila" de onNextRequested(), e também no caminho de fim
    de faixa natural), MovieActivity.finish() é chamado e a tela fecha
    inteira. Isso também explica pause/previous "fechando": se a fila
    (AlbumQueueLoader, assíncrona) ainda não carregou quando o usuário
    interage, hasQueue() retorna false e cai nesse mesmo fallback.

    Correção (conforme decisão do usuário: só fecha quando a faixa
    termina sozinha tocando, sem fila e sem repeat — nunca por causa de
    pause/next/previous):
    - PhotoPage.playVideo() passa a setar EXTRA_FINISH_ON_COMPLETION
      explicitamente como false — a tela NUNCA fecha sozinha por conta
      do MovieActivity, o controle de fechar (ou não) fica 100% com
      MoviePlayer, que já sabe distinguir os casos.
    - MoviePlayer.onNextRequested(): quando não há fila (hasQueue() ==
      false), passa a apenas pausar a faixa atual (mesmo comportamento
      já usado quando a fila acaba sem repeat), em vez de chamar
      onCompletion() (que fechava a tela). onCompletion() (que efetiva o
      finish(), via override em MovieActivity) só é chamado agora no
      ÚNICO caso pedido: a faixa chegou ao fim tocando sozinha
      (MediaPlayer.OnCompletionListener natural, sem fila carregada e
      sem repeat ativo) — ver MusicPlaybackService.onCompletion() /
      MoviePlayer, que já cai em onNextRequested() nesse caso; a
      diferença fica então isolada em por que onNextRequested() foi
      chamado (usuário vs fim natural), tratada no item (B) abaixo.

    (B) Para preservar o único caso em que fechar É o comportamento
    correto (fim natural da faixa, sem fila, sem repeat), adicionamos um
    parâmetro fromUserAction a onNextRequested() nos dois pontos que já
    chamam ele hoje: o clique do botão "próxima" (usuário) e o callback
    de fim de faixa do MediaPlayer (natural). Isso separa os dois casos
    que antes caíam no mesmo código.

(C) LAYOUT dos botões da tela de reprodução (estilo "player de música
    convencional", conforme pedido):
    - [Anterior] [Play/Pause] [Próxima]: continuam juntos e centralizados
      horizontalmente, mas MOVIDOS pra mais perto da parte de baixo da
      tela (não mais no centro vertical exato), como qualquer player de
      música.
    - Canto inferior ESQUERDO: botão de Repetir Todas sozinho (do lado
      de onde fica o botão de filtro da ActionBar).
    - Canto inferior DIREITO: Editar Capa e Repetir Uma, um do lado do
      outro (Repetir Uma mais pra fora, Editar Capa mais pra dentro).
    - Todos sempre visíveis em qualquer orientação (retrato/paisagem),
      sem sair da tela e sem se sobrepor — cálculo de gap já corrigido
      anteriormente é preservado.

(D) Resquícios visuais de vídeo/galeria removidos:
    - Ícone de "play" preto sobreposto na capa, na tela de visualização
      单 item ANTES de abrir o player de fato (PhotoView.java,
      drawVideoPlayIcon) — nunca mais desenhado, pois o app não tem
      vídeo de verdade (toda faixa é MEDIA_TYPE_VIDEO internamente por
      decisão de arquitetura do Passo 1.4, então esse ícone aparecia
      para TODAS as faixas).
    - Texto "Loading video…" na tela de reprodução trocado para
      "Carregando Faixa 3D…".

Arquivos tocados:
    1. app/src/main/res/values/strings.xml (loading_video)
    2. app/src/main/java/com/android/gallery3d/app/PhotoPage.java
       (EXTRA_FINISH_ON_COMPLETION=false em playVideo())
    3. app/src/main/java/com/android/gallery3d/app/MoviePlayer.java
       (fallback sem fila não fecha mais por engano)
    4. app/src/main/java/com/android/gallery3d/app/MovieControllerOverlay.java
       (reposicionamento completo dos botões)
    5. app/src/main/java/com/android/gallery3d/ui/PhotoView.java
       (remove ícone de play preto)

Uso (Termux, dentro de ~/Galeria3D):
    python3 passo_fix_reproducao_ui_e_fechamento.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path.home() / "Galeria3D"
STRINGS = PROJECT_ROOT / "app/src/main/res/values/strings.xml"
PHOTO_PAGE = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/PhotoPage.java"
MOVIE_PLAYER = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"
MUSIC_SERVICE = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/MusicPlaybackService.java"
CONTROLLER = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/MovieControllerOverlay.java"
PHOTO_VIEW = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/ui/PhotoView.java"


def fail(msg):
    print(f"ERRO: {msg}")
    sys.exit(1)


def backup(path: Path):
    b = path.with_suffix(path.suffix + ".bak")
    b.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  Backup salvo em: {b}")


def replace_once(path: Path, old: str, new: str, label: str, idempotent_marker: str = None):
    if not path.exists():
        fail(f"[{label}] Arquivo não encontrado: {path}")
    content = path.read_text(encoding="utf-8")
    marker = idempotent_marker if idempotent_marker is not None else new
    if marker in content:
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
    if marker not in patched:
        fail(f"[{label}] Substituição não aplicou o padrão novo — abortando sem escrever.")
    path.write_text(patched, encoding="utf-8")
    print(f"[{label}] OK.")
    return True


# ---------------------------------------------------------------------
# 1. strings.xml — "Loading video..." -> "Carregando Faixa 3D..."
# ---------------------------------------------------------------------

def step_strings():
    old = '<string name="loading_video">Loading video\\u2026</string>'
    new = '<string name="loading_video">Carregando Faixa 3D\\u2026</string>'
    replace_once(STRINGS, old, new, "1/5 strings.xml",
                 idempotent_marker='Carregando Faixa 3D')


# ---------------------------------------------------------------------
# 2. PhotoPage.java — playVideo() nunca deixa a Activity fechar sozinha
# ---------------------------------------------------------------------

def step_photo_page():
    old = '''    public void playVideo(Activity activity, Uri uri, String title) {'''
    marker = "EXTRA_FINISH_ON_COMPLETION, false"
    if not PHOTO_PAGE.exists():
        fail(f"[2/5] Arquivo não encontrado: {PHOTO_PAGE}")
    content = PHOTO_PAGE.read_text(encoding="utf-8")
    if marker in content:
        print("[2/5 PhotoPage.java] Já aplicado antes — nada a fazer (idempotente).")
        return
    count = content.count(old)
    if count == 0:
        fail("[2/5] Assinatura de playVideo() não encontrada em PhotoPage.java — "
             "verifique manualmente.")
    if count > 1:
        fail("[2/5] Assinatura de playVideo() encontrada mais de 1 vez — ambíguo.")

    # Precisamos achar o Intent dentro do método e adicionar a extra.
    # Âncora: a linha startActivityForResult dentro de playVideo (única
    # ocorrência com REQUEST_PLAY_VIDEO, confirmado no Passo 3).
    anchor = "activity.startActivityForResult(intent, REQUEST_PLAY_VIDEO);"
    if content.count(anchor) != 1:
        fail("[2/5] Âncora startActivityForResult(intent, REQUEST_PLAY_VIDEO) "
             "não encontrada (ou ambígua) — verifique manualmente o método playVideo().")

    backup(PHOTO_PAGE)
    new_anchor = (
        "        // Fix (Player3D): a tela de reproducao NUNCA deve fechar\n"
        "        // sozinha por causa do mecanismo generico de\n"
        "        // EXTRA_FINISH_ON_COMPLETION do MovieActivity (que por\n"
        "        // padrao e true quando ausente) - pause/next/previous nao\n"
        "        // podem fechar a tela. Quem decide fechar (ou nao) e o\n"
        "        // MoviePlayer, de forma explicita, no unico caso correto\n"
        "        // (fim natural da faixa, sem fila, sem repeat).\n"
        "        intent.putExtra(android.provider.MediaStore.EXTRA_FINISH_ON_COMPLETION, false);\n"
        "        " + anchor
    )
    patched = content.replace(anchor, new_anchor, 1)
    if marker not in patched:
        fail("[2/5] Substituição falhou — abortando sem escrever.")
    PHOTO_PAGE.write_text(patched, encoding="utf-8")
    print("[2/5 PhotoPage.java] OK.")


# ---------------------------------------------------------------------
# 3. MoviePlayer.java — onNextRequested() só fecha no fim natural real
# ---------------------------------------------------------------------

def step_movie_player():
    if not MOVIE_PLAYER.exists():
        fail(f"[3/5] Arquivo não encontrado: {MOVIE_PLAYER}")
    if not MUSIC_SERVICE.exists():
        fail(f"[3/5] Arquivo não encontrado: {MUSIC_SERVICE}")

    player_content = MOVIE_PLAYER.read_text(encoding="utf-8")
    service_content = MUSIC_SERVICE.read_text(encoding="utf-8")

    marker = "fromUserAction"
    if marker in player_content and marker in service_content:
        print("[3/5] Já aplicado antes — nada a fazer (idempotente).")
        return

    # --- 3.1: MusicPlaybackService.java - interface QueueController ---
    old_iface = '''    public interface QueueController {
        void onNextRequested();
        void onPreviousRequested();
    }'''
    new_iface = '''    // Fix (Player3D): onNextRequested() agora informa QUEM pediu a
    // proxima faixa - true = usuario (clique/notificacao/MediaSession),
    // false = fim natural da faixa atual (MediaPlayer.OnCompletionListener).
    // So o caso "false, sem fila, sem repeat" deve fechar a tela.
    public interface QueueController {
        void onNextRequested(boolean fromUserAction);
        void onPreviousRequested();
    }'''
    if service_content.count(old_iface) != 1:
        fail("[3/5] Interface QueueController não encontrada (ou ambígua) em "
             "MusicPlaybackService.java — verifique manualmente.")
    service_content = service_content.replace(old_iface, new_iface, 1)

    # --- 3.2: requestNext() vira requestNext(boolean fromUserAction) ---
    old_request_next = '''    private void requestNext() {
        if (mQueueController != null) {
            mQueueController.onNextRequested();
        }
    }'''
    new_request_next = '''    private void requestNext(boolean fromUserAction) {
        if (mQueueController != null) {
            mQueueController.onNextRequested(fromUserAction);
        }
    }'''
    if service_content.count(old_request_next) != 1:
        fail("[3/5] requestNext() não encontrado no formato esperado em "
             "MusicPlaybackService.java — verifique manualmente.")
    service_content = service_content.replace(old_request_next, new_request_next, 1)

    # --- 3.3: os 4 call-sites de requestNext() em MusicPlaybackService ---
    # 3 sao acao do usuario (ACTION_NEXT, onSkipToNext da MediaSession);
    # 1 e o fim natural da faixa (dentro de onCompletion(MediaPlayer mp)).
    # Distinguimos pelo contexto ja confirmado por leitura manual do
    # arquivo: a unica ocorrencia dentro do bloco onCompletion(MediaPlayer
    # mp) é fromUserAction=false: todas as outras (ACTION_NEXT tratado em
    # handleAction, e onSkipToNext da MediaSession) sao fromUserAction=true.
    user_call_count = service_content.count("requestNext();")
    if user_call_count == 0:
        fail("[3/5] Nenhuma chamada requestNext() sobrou em "
             "MusicPlaybackService.java para ajustar — verifique manualmente.")

    # Ancora especifica do caminho natural: dentro de onCompletion(MediaPlayer mp),
    # comentario ja existente logo acima da chamada confirma o contexto.
    natural_anchor = (
        "        // Repetir todas ou tocar a proxima faixa da fila e decisao de quem\n"
        "        // controla a fila (MoviePlayer) - o Service so avisa que acabou.\n"
        "        requestNext();"
    )
    if service_content.count(natural_anchor) != 1:
        fail("[3/5] Não encontrei (ou é ambíguo) o ponto de chamada natural "
             "de requestNext() dentro de onCompletion(MediaPlayer) em "
             "MusicPlaybackService.java — verifique manualmente e ajuste "
             "essa chamada para requestNext(false); as demais para "
             "requestNext(true).")
    natural_replacement = (
        "        // Repetir todas ou tocar a proxima faixa da fila e decisao de quem\n"
        "        // controla a fila (MoviePlayer) - o Service so avisa que acabou.\n"
        "        // Fix (Player3D): fromUserAction=false - fim natural da faixa,\n"
        "        // nao pedido do usuario. So esse caminho pode fechar a tela\n"
        "        // (MoviePlayer.onNextRequested decide).\n"
        "        requestNext(false);"
    )
    service_content = service_content.replace(natural_anchor, natural_replacement, 1)

    # As chamadas remanescentes (ACTION_NEXT, onSkipToNext) sao todas
    # fromUserAction=true.
    remaining = service_content.count("requestNext();")
    if remaining == 0:
        fail("[3/5] Não sobrou nenhuma chamada requestNext() de usuário em "
             "MusicPlaybackService.java (esperado pelo menos 1: ACTION_NEXT "
             "ou onSkipToNext) — verifique manualmente.")
    service_content = service_content.replace("requestNext();", "requestNext(true);")

    if marker not in service_content:
        fail("[3/5] Marcador 'fromUserAction' ausente após patch de "
             "MusicPlaybackService.java — abortando sem escrever.")

    # --- 3.4: MoviePlayer.java - onNextRequested(boolean) ---
    old_next = '''    @Override
    public void onNextRequested() {
        if (!hasQueue()) {
            mController.showEnded();
            onCompletion();
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
    }'''

    new_next = '''    // Fix (Player3D): onNextRequested(fromUserAction) agora distingue POR
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
    }'''

    if player_content.count(old_next) != 1:
        fail("[3/5] onNextRequested() não encontrado no formato esperado em "
             "MoviePlayer.java — verifique manualmente.")
    player_content = player_content.replace(old_next, new_next, 1)

    if marker not in player_content:
        fail("[3/5] Marcador 'fromUserAction' ausente após patch de "
             "MoviePlayer.java — abortando sem escrever.")

    backup(MUSIC_SERVICE)
    MUSIC_SERVICE.write_text(service_content, encoding="utf-8")
    backup(MOVIE_PLAYER)
    MOVIE_PLAYER.write_text(player_content, encoding="utf-8")
    print("[3/5 MoviePlayer.java + MusicPlaybackService.java] OK.")


# ---------------------------------------------------------------------
# 4. MovieControllerOverlay.java — reposicionar botões
# ---------------------------------------------------------------------

CONTROLLER_NEW = '''/*
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

package com.android.gallery3d.app;

import android.content.Context;
import android.os.Handler;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.animation.Animation;
import android.view.animation.Animation.AnimationListener;
import android.view.animation.AnimationUtils;
import android.widget.ImageView;
import android.widget.ImageView.ScaleType;
import com.android.gallery3d.R;

/**
 * The playback controller for the Movie Player.
 *
 * Fix (Player3D), layout estilo player de musica convencional:
 * - [Anterior] [Play/Pause] [Proxima]: juntos, centralizados
 *   horizontalmente, mas posicionados mais PERTO DA BASE da tela (nao
 *   mais no centro vertical exato), como qualquer tocador de musica.
 * - Canto inferior ESQUERDO: [Repetir todas] sozinho (do lado de onde
 *   fica o botao de filtro da ActionBar).
 * - Canto inferior DIREITO: [Editar capa] [Repetir uma], lado a lado
 *   (editar capa mais para dentro, repetir uma mais para fora, na
 *   quina).
 * Todos os 5 botoes SEMPRE visiveis, em qualquer orientacao, sem sair da
 * tela e sem se sobrepor.
 */
public class MovieControllerOverlay extends CommonControllerOverlay implements
        AnimationListener {

    private boolean hidden;

    private final Handler handler;
    private final Runnable startHidingRunnable;
    private final Animation hideAnimation;

    private final ImageView mRepeatAllView;
    private final ImageView mPreviousView;
    private final ImageView mNextView;
    private final ImageView mRepeatOneView;
    private final ImageView mEditCoverView;

    public MovieControllerOverlay(Context context) {
        super(context);

        LayoutParams wrapContent =
                new LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);

        mRepeatAllView = createExtraButton(context,
                R.drawable.ic_vidcontrol_repeat_all, R.string.player3d_repeat_all);
        addView(mRepeatAllView, wrapContent);

        mPreviousView = createExtraButton(context,
                R.drawable.ic_vidcontrol_previous, R.string.player3d_previous);
        addView(mPreviousView, wrapContent);

        mNextView = createExtraButton(context,
                R.drawable.ic_vidcontrol_next, R.string.player3d_next);
        addView(mNextView, wrapContent);

        mRepeatOneView = createExtraButton(context,
                R.drawable.ic_vidcontrol_repeat_one, R.string.player3d_repeat_one);
        addView(mRepeatOneView, wrapContent);

        mEditCoverView = createExtraButton(context,
                R.drawable.ic_menu_edit_holo_dark, R.string.player3d_edit_cover);
        addView(mEditCoverView, wrapContent);

        mRepeatAllView.setVisibility(View.INVISIBLE);
        mPreviousView.setVisibility(View.INVISIBLE);
        mNextView.setVisibility(View.INVISIBLE);
        mRepeatOneView.setVisibility(View.INVISIBLE);
        mEditCoverView.setVisibility(View.INVISIBLE);

        handler = new Handler();
        startHidingRunnable = new Runnable() {
                @Override
            public void run() {
                startHiding();
            }
        };

        hideAnimation = AnimationUtils.loadAnimation(context, R.anim.player_out);
        hideAnimation.setAnimationListener(this);

        hide();
    }

    private ImageView createExtraButton(Context context, int iconRes, int contentDescriptionRes) {
        ImageView view = new ImageView(context);
        view.setImageResource(iconRes);
        view.setContentDescription(context.getResources().getString(contentDescriptionRes));
        view.setBackgroundResource(R.drawable.bg_vidcontrol);
        view.setScaleType(ScaleType.CENTER);
        view.setFocusable(true);
        view.setClickable(true);
        view.setOnClickListener(this);
        return view;
    }

    @Override
    protected void createTimeBar(Context context) {
        mTimeBar = new TimeBar(context, this);
    }

    @Override
    public void hide() {
        boolean wasHidden = hidden;
        hidden = true;
        super.hide();
        if (mListener != null && wasHidden != hidden) {
            mListener.onHidden();
        }
    }


    @Override
    public void show() {
        boolean wasHidden = hidden;
        hidden = false;
        super.show();
        if (mListener != null && wasHidden != hidden) {
            mListener.onShown();
        }
        maybeStartHiding();
    }

    private void maybeStartHiding() {
        cancelHiding();
        if (mState == State.PLAYING) {
            handler.postDelayed(startHidingRunnable, 2500);
        }
    }

    private void startHiding() {
        startHideAnimation(mBackground);
        startHideAnimation(mTimeBar);
        startHideAnimation(mPlayPauseReplayView);
        startHideAnimation(mRepeatAllView);
        startHideAnimation(mPreviousView);
        startHideAnimation(mNextView);
        startHideAnimation(mRepeatOneView);
        startHideAnimation(mEditCoverView);
    }

    private void startHideAnimation(View view) {
        if (view.getVisibility() == View.VISIBLE) {
            view.startAnimation(hideAnimation);
        }
    }

    private void cancelHiding() {
        handler.removeCallbacks(startHidingRunnable);
        mBackground.setAnimation(null);
        mTimeBar.setAnimation(null);
        mPlayPauseReplayView.setAnimation(null);
        mRepeatAllView.setAnimation(null);
        mPreviousView.setAnimation(null);
        mNextView.setAnimation(null);
        mRepeatOneView.setAnimation(null);
        mEditCoverView.setAnimation(null);
    }

    @Override
    public void onAnimationStart(Animation animation) {
        // Do nothing.
    }

    @Override
    public void onAnimationRepeat(Animation animation) {
        // Do nothing.
    }

    @Override
    public void onAnimationEnd(Animation animation) {
        hide();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (hidden) {
            show();
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (super.onTouchEvent(event)) {
            return true;
        }

        if (hidden) {
            show();
            return true;
        }
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                cancelHiding();
                if (mState == State.PLAYING || mState == State.PAUSED) {
                    mListener.onPlayPause();
                }
                break;
            case MotionEvent.ACTION_UP:
                maybeStartHiding();
                break;
        }
        return true;
    }

    @Override
    public void onClick(View view) {
        if (view == mPreviousView) {
            cancelHiding();
            if (mListener != null) mListener.onPrevious();
            maybeStartHiding();
            return;
        }
        if (view == mNextView) {
            cancelHiding();
            if (mListener != null) mListener.onNext();
            maybeStartHiding();
            return;
        }
        if (view == mRepeatAllView) {
            if (mListener != null) mListener.onToggleRepeatAll();
            return;
        }
        if (view == mRepeatOneView) {
            if (mListener != null) mListener.onToggleRepeatOne();
            return;
        }
        if (view == mEditCoverView) {
            if (mListener != null) mListener.onEditCover();
            return;
        }
        super.onClick(view);
    }

    // Fix (Player3D), layout estilo player de musica convencional:
    // - [Previous] [PlayPause] [Next]: juntos, centralizados
    //   horizontalmente, MOVIDOS pra perto da base da tela (nao mais no
    //   centro vertical - CommonControllerOverlay.onLayout centraliza
    //   mPlayPauseReplayView em w/2,h/2 por padrao; aqui recalculamos a
    //   posicao vertical dos 3 botoes principais para perto do rodape,
    //   acima da TimeBar).
    // - Canto inferior esquerdo: [RepeatAll] sozinho.
    // - Canto inferior direito: [EditCover] [RepeatOne], lado a lado
    //   (EditCover mais para dentro, RepeatOne na quina).
    @Override
    protected void onLayout(boolean changed, int left, int top, int right, int bottom) {
        super.onLayout(changed, left, top, right, bottom);

        int w = right - left;
        int h = bottom - top;

        int buttonWidth = mPlayPauseReplayView.getMeasuredWidth();
        int buttonHeight = mPlayPauseReplayView.getMeasuredHeight();

        // Linha principal (Anterior/Play/Proxima): perto da base da tela,
        // acima da TimeBar, em vez do centro vertical exato.
        int mainRowMargin = buttonHeight; // distancia acima da TimeBar
        int mainRowCenterY = h - mTimeBar.getPreferredHeight() - mainRowMargin
                - buttonHeight / 2;
        int centerX = w / 2;

        // Botao de play/pause principal (da classe base) precisa ser
        // reposicionado aqui tambem - a base o centraliza em h/2, temos
        // que sobrescrever manualmente.
        layoutCenteredAt(mPlayPauseReplayView, centerX, mainRowCenterY);

        // Gap dos botoes Anterior/Proxima em relacao ao Play, limitado ao
        // espaco real disponivel (fix anterior preservado).
        int usableHalfWidth = Math.min(centerX - left, right - centerX);
        int maxGap = usableHalfWidth - buttonWidth / 2;
        int preferredGap = buttonWidth + buttonWidth / 3;
        int gap = Math.max(buttonWidth / 2, Math.min(preferredGap, maxGap));

        layoutCenteredAt(mPreviousView, centerX - gap, mainRowCenterY);
        layoutCenteredAt(mNextView, centerX + gap, mainRowCenterY);

        updateExtraButtonsVisibility();

        // Cantos inferiores: mesma altura da linha principal, nao
        // competem por espaco vertical com ela (ficam mais abaixo, perto
        // da TimeBar).
        int margin = buttonWidth / 2;
        int cornerY = h - mTimeBar.getPreferredHeight() - margin
                - mRepeatAllView.getMeasuredHeight() / 2;
        int spacing = buttonWidth / 4;

        // Canto inferior esquerdo: Repetir Todas, sozinho.
        int repeatAllCenterX = margin + mRepeatAllView.getMeasuredWidth() / 2;
        layoutCenteredAt(mRepeatAllView, repeatAllCenterX, cornerY);

        // Canto inferior direito: Repetir Uma na quina, Editar Capa do
        // lado, mais para dentro.
        int repeatOneCenterX = w - margin - mRepeatOneView.getMeasuredWidth() / 2;
        layoutCenteredAt(mRepeatOneView, repeatOneCenterX, cornerY);

        int editCoverCenterX = repeatOneCenterX - mRepeatOneView.getMeasuredWidth() / 2
                - spacing - mEditCoverView.getMeasuredWidth() / 2;
        layoutCenteredAt(mEditCoverView, editCoverCenterX, cornerY);
    }

    private void layoutCenteredAt(View view, int centerX, int centerY) {
        int cw = view.getMeasuredWidth();
        int ch = view.getMeasuredHeight();
        view.layout(centerX - cw / 2, centerY - ch / 2, centerX + cw / 2, centerY + ch / 2);
    }

    @Override
    protected void updateViews() {
        if (hidden) {
            return;
        }
        super.updateViews();
        int visibility = mPlayPauseReplayView.getVisibility();
        mPreviousView.setVisibility(visibility);
        mNextView.setVisibility(visibility);
        mEditCoverView.setVisibility(visibility);
        updateExtraButtonsVisibility();
    }

    private void updateExtraButtonsVisibility() {
        int visibility = mPlayPauseReplayView.getVisibility();
        mRepeatAllView.setVisibility(visibility);
        mRepeatOneView.setVisibility(visibility);
    }

    /**
     * Atualiza o icone dos botoes de repeat pra refletir o modo atual
     * (chamado por MoviePlayer.onRepeatModeChanged, Passo 9/4.2). Troca pra
     * uma variante com cor de destaque quando o respectivo modo esta ativo.
     */
    public void setRepeatModeVisual(MusicPlaybackService.RepeatMode mode) {
        mRepeatAllView.setImageResource(mode == MusicPlaybackService.RepeatMode.ALL
                ? R.drawable.ic_vidcontrol_repeat_all_active
                : R.drawable.ic_vidcontrol_repeat_all);
        mRepeatOneView.setImageResource(mode == MusicPlaybackService.RepeatMode.ONE
                ? R.drawable.ic_vidcontrol_repeat_one_active
                : R.drawable.ic_vidcontrol_repeat_one);
    }

    // TimeBar listener

    @Override
    public void onScrubbingStart() {
        cancelHiding();
        super.onScrubbingStart();
    }

    @Override
    public void onScrubbingMove(int time) {
        cancelHiding();
        super.onScrubbingMove(time);
    }

    @Override
    public void onScrubbingEnd(int time, int trimStartTime, int trimEndTime) {
        maybeStartHiding();
        super.onScrubbingEnd(time, trimStartTime, trimEndTime);
    }
}
'''


def step_controller():
    if not CONTROLLER.exists():
        fail(f"[4/5] Arquivo não encontrado: {CONTROLLER}")
    content = CONTROLLER.read_text(encoding="utf-8")
    marker = "mainRowCenterY"
    if marker in content:
        print("[4/5 MovieControllerOverlay.java] Já aplicado antes — nada a fazer (idempotente).")
        return
    backup(CONTROLLER)
    CONTROLLER.write_text(CONTROLLER_NEW, encoding="utf-8")
    print("[4/5 MovieControllerOverlay.java] OK — layout reposicionado "
          "(estilo player de música).")


# ---------------------------------------------------------------------
# 5. PhotoView.java — remover ícone de play preto (resquício de vídeo)
# ---------------------------------------------------------------------

def step_photo_view():
    old = '''    // Draw the video play icon (in the place where the spinner was)
    private void drawVideoPlayIcon(GLCanvas canvas, int side) {
        int s = side / ICON_RATIO;
        // Draw the video play icon at the center
        mVideoPlayIcon.draw(canvas, -s / 2, -s / 2, s, s);
    }'''
    if not PHOTO_VIEW.exists():
        fail(f"[5/5] Arquivo não encontrado: {PHOTO_VIEW}")
    content = PHOTO_VIEW.read_text(encoding="utf-8")
    marker = "Fix (Player3D): app nao tem mais video de verdade"
    if marker in content:
        print("[5/5 PhotoView.java] Já aplicado antes — nada a fazer (idempotente).")
        return

    count = content.count(old)
    if count == 0:
        fail("[5/5] drawVideoPlayIcon() não encontrado no formato esperado em "
             "PhotoView.java — verifique manualmente.")
    if count > 1:
        fail("[5/5] drawVideoPlayIcon() encontrado mais de 1 vez — ambíguo.")

    new = (
        "    // " + marker + " (toda faixa de audio e\n"
        "    // MEDIA_TYPE_VIDEO internamente, decisao do Passo 1.4) - o icone\n"
        "    // preto de play sobreposto na capa nunca deve ser desenhado. Corpo\n"
        "    // esvaziado de proposito (chamadas existentes em outros pontos\n"
        "    // deste arquivo continuam compilando, sem efeito visual algum).\n"
        "    private void drawVideoPlayIcon(GLCanvas canvas, int side) {\n"
        "    }"
    )
    backup(PHOTO_VIEW)
    patched = content.replace(old, new, 1)
    if marker not in patched:
        fail("[5/5] Substituição falhou — abortando sem escrever.")
    PHOTO_VIEW.write_text(patched, encoding="utf-8")
    print("[5/5 PhotoView.java] OK — ícone de play preto desativado.")


def main():
    if not PROJECT_ROOT.exists():
        fail(f"Projeto não encontrado em {PROJECT_ROOT}. Rode de dentro de ~/Galeria3D.")

    step_strings()
    print()
    step_photo_page()
    print()
    step_movie_player()
    print()
    step_controller()
    print()
    step_photo_view()

    print()
    print("Próximo passo:")
    print("  cd ~/Galeria3D && ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

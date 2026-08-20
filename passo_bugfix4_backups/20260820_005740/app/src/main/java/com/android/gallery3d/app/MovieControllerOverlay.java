/*
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
 * Passo 4.2 (Player3D) - 4 botoes novos (Repetir todas, Faixa anterior,
 * Proxima faixa, Repetir uma), construidos com o MESMO padrao programatico
 * do botao de play/pause ja existente (CommonControllerOverlay.
 * mPlayPauseReplayView): ImageView com bg_vidcontrol como fundo, ScaleType
 * CENTER, clicavel. Ficam SO aqui (nao em CommonControllerOverlay, que
 * tambem e a base de TrimControllerOverlay/TrimVideo, a tela de corte de
 * video) - nao faz sentido repeat/anterior/proxima na tela de corte, que
 * alias e uma funcionalidade de video ja fora do escopo de qualquer passo
 * deste app de audio.
 *
 * Ordem da esquerda para a direita: [Repetir todas] [Anterior] [Play/Pause]
 * [Proxima] [Repetir uma] - identica a ordem ja usada e testada na
 * notificacao (MusicPlaybackService.buildNotification(), Passo 9), mesma
 * fonte de verdade.
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

        mRepeatAllView.setVisibility(View.INVISIBLE);
        mPreviousView.setVisibility(View.INVISIBLE);
        mNextView.setVisibility(View.INVISIBLE);
        mRepeatOneView.setVisibility(View.INVISIBLE);

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

    // Mesmo padrao de construcao do mPlayPauseReplayView (CommonControllerOverlay),
    // so trocando o drawable do icone e a descricao de acessibilidade.
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

    // Cliques dos 4 botoes novos. mPlayPauseReplayView continua tratado
    // pelo onClick(View) de CommonControllerOverlay (super.onClick).
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
        super.onClick(view);
    }

    // Posiciona os 4 botoes novos em linha horizontal ao redor do
    // mPlayPauseReplayView (ja posicionado por super.onLayout()), na ordem
    // [RepeatAll] [Previous] [PlayPause] [Next] [RepeatOne] - identica a
    // ordem da notificacao (Passo 9).
    @Override
    protected void onLayout(boolean changed, int left, int top, int right, int bottom) {
        super.onLayout(changed, left, top, right, bottom);

        int centerX = mPlayPauseReplayView.getLeft() + mPlayPauseReplayView.getMeasuredWidth() / 2;
        int centerY = mPlayPauseReplayView.getTop() + mPlayPauseReplayView.getMeasuredHeight() / 2;

        int buttonWidth = mPlayPauseReplayView.getMeasuredWidth();

        // Fix (Player3D): o gap antigo (buttonWidth + buttonWidth/3) era um
        // multiplo fixo que, multiplicado por 2 para os botoes extremos
        // (RepeatAll/RepeatOne), estourava a largura da tela em celulares
        // comuns - os 2 botoes extremos ficavam fora da area visivel.
        // Agora o gap eh limitado pelo espaco real disponivel entre o
        // centro e a borda do controller, garantindo que os 5 botoes
        // sempre cabem, com espacamento simetrico.
        int usableHalfWidth = Math.min(centerX - left, right - centerX);
        int maxGapForTwoSlots = (usableHalfWidth - buttonWidth / 2) / 2;

        int preferredGap = buttonWidth + buttonWidth / 3;
        int gap = Math.max(buttonWidth / 2, Math.min(preferredGap, maxGapForTwoSlots));

        layoutCenteredAt(mPreviousView, centerX - gap, centerY);
        layoutCenteredAt(mNextView, centerX + gap, centerY);
        layoutCenteredAt(mRepeatAllView, centerX - gap * 2, centerY);
        layoutCenteredAt(mRepeatOneView, centerX + gap * 2, centerY);
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
        // Os 4 botoes novos seguem a mesma visibilidade do play/pause
        // (escondidos durante LOADING/ERROR, visiveis em PLAYING/PAUSED).
        int visibility = mPlayPauseReplayView.getVisibility();
        mRepeatAllView.setVisibility(visibility);
        mPreviousView.setVisibility(visibility);
        mNextView.setVisibility(visibility);
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

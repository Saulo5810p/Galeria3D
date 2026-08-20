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

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
import android.content.res.Resources;
import android.os.Handler;
import android.util.TypedValue;
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
 * - Canto superior DIREITO: [Editar capa], sozinho, espaco proprio, longe
 *   dos outros botoes.
 * - Linha propria, BEM mais proxima da TimeBar (quase colada acima
 *   dela): [Repetir todas] no canto esquerdo, [Repetir uma] no canto
 *   direito.
 * - Barra cinza translucida (so decorativa) cobrindo do topo da linha
 *   Anterior/Play/Proxima ate o fim inferior da tela.
 * Todos os botoes SEMPRE visiveis, em qualquer orientacao, sem sair da
 * tela e sem se sobrepor.
 */
public class MovieControllerOverlay extends CommonControllerOverlay implements
        AnimationListener {

    // Correcao (Player3D, toque sobreposto entre botoes): TODOS os botoes
    // (o Play/Pause da classe base incluido) usavam android:background=
    // R.drawable.bg_vidcontrol com wrapContent - esse drawable mede
    // ~230dp de LARGURA (345x140px em hdpi, um fundo retangular largo,
    // nao um icone quadrado), entao cada botao "inflava" para esse
    // tamanho gigante e as areas de toque de Anterior/Play/Proxima (e de
    // Repetir Todas/Repetir Uma) ficavam se sobrepondo por dezenas de dp -
    // por isso o toque as vezes ia parar no botao errado (vizinho ganhava
    // a prioridade por ter sido adicionado depois na arvore de views).
    // Agora todo botao tem tamanho FIXO e igual (BUTTON_SIZE_DP), fundo
    // trocado para um ripple sem tamanho proprio (selectableItemBackgroundBorderless),
    // e ScaleType.CENTER_INSIDE (em vez de CENTER) pra nenhum icone maior
    // que o novo tamanho fixo ficar cortado.
    private static final int BUTTON_SIZE_DP = 48;

    private static int dpToPx(Context context, int dp) {
        Resources r = context.getResources();
        return Math.round(dp * r.getDisplayMetrics().density);
    }

    private static int resolveBorderlessRippleRes(Context context) {
        TypedValue outValue = new TypedValue();
        context.getTheme().resolveAttribute(
                android.R.attr.selectableItemBackgroundBorderless, outValue, true);
        return outValue.resourceId;
    }

    private boolean hidden;

    private final Handler handler;
    private final Runnable startHidingRunnable;
    private final Animation hideAnimation;

    // Correcao (Player3D): barra decorativa cinza bem translucida atras
    // dos botoes inferiores, so pra dar mais cara de player de musica -
    // nao reage a toque, nao tem nenhuma logica alem de aparecer/sumir
    // junto com os botoes.
    private final View mControlsBackdrop;

    private final ImageView mRepeatAllView;
    private final ImageView mPreviousView;
    private final ImageView mNextView;
    private final ImageView mRepeatOneView;
    private final ImageView mEditCoverView;

    public MovieControllerOverlay(Context context) {
        super(context);

        int buttonSizePx = dpToPx(context, BUTTON_SIZE_DP);
        LayoutParams fixedButtonSize = new LayoutParams(buttonSizePx, buttonSizePx);
        LayoutParams matchParent =
                new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT);

        // Corrige tambem o botao de Play/Pause criado na classe base
        // (CommonControllerOverlay), que tinha o mesmo problema de fundo
        // gigante (ver comentario acima em BUTTON_SIZE_DP).
        mPlayPauseReplayView.setBackgroundResource(resolveBorderlessRippleRes(context));
        mPlayPauseReplayView.setScaleType(ScaleType.CENTER_INSIDE);
        mPlayPauseReplayView.setLayoutParams(fixedButtonSize);

        // Adicionada antes dos botoes para ficar atras deles no z-order
        // (primeira view adicionada = desenhada primeiro = fica por baixo).
        mControlsBackdrop = new View(context);
        mControlsBackdrop.setBackgroundColor(
                context.getResources().getColor(R.color.player3d_controls_backdrop));
        mControlsBackdrop.setClickable(false);
        mControlsBackdrop.setFocusable(false);
        addView(mControlsBackdrop, matchParent);

        mRepeatAllView = createExtraButton(context,
                R.drawable.ic_vidcontrol_repeat_all, R.string.player3d_repeat_all);
        addView(mRepeatAllView, fixedButtonSize);

        mPreviousView = createExtraButton(context,
                R.drawable.ic_vidcontrol_previous, R.string.player3d_previous);
        addView(mPreviousView, fixedButtonSize);

        mNextView = createExtraButton(context,
                R.drawable.ic_vidcontrol_next, R.string.player3d_next);
        addView(mNextView, fixedButtonSize);

        mRepeatOneView = createExtraButton(context,
                R.drawable.ic_vidcontrol_repeat_one, R.string.player3d_repeat_one);
        addView(mRepeatOneView, fixedButtonSize);

        mEditCoverView = createExtraButton(context,
                R.drawable.ic_menu_edit_holo_dark, R.string.player3d_edit_cover);
        addView(mEditCoverView, fixedButtonSize);

        mControlsBackdrop.setVisibility(View.INVISIBLE);
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
        // Correcao (toque sobreposto): ripple sem tamanho proprio, em vez
        // do fundo largo bg_vidcontrol - ver comentario acima de
        // BUTTON_SIZE_DP. CENTER_INSIDE em vez de CENTER pra icones
        // maiores que o botao (ex.: os 48x48 originais vs o novo tamanho
        // fixo) encolherem pra caber, em vez de ficarem cortados.
        view.setBackgroundResource(resolveBorderlessRippleRes(context));
        view.setScaleType(ScaleType.CENTER_INSIDE);
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
        startHideAnimation(mControlsBackdrop);
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
        mControlsBackdrop.setAnimation(null);
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
    // - [EditCover]: movido para o canto superior direito da tela,
    //   espaco proprio, sem disputar espaco com os outros botoes.
    // - Correcao (mover repeat mais pra baixo): [RepeatAll] (canto
    //   inferior esquerdo) e [RepeatOne] (canto inferior direito) agora
    //   ficam na sua PROPRIA linha, mais abaixo que EditCover - bem perto
    //   da TimeBar, praticamente colados acima dela, sem cobrir/sair da
    //   tela. Como EditCover agora fica no topo, nao ha risco de
    //   sobreposicao entre os dois.
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
        // Correcao: piso do gap era buttonWidth/2 - com o buttonWidth
        // antigo (inflado pelo fundo bg_vidcontrol) isso ja garantia
        // sobreposicao entre os botoes; agora que buttonWidth reflete o
        // tamanho real (BUTTON_SIZE_DP), o piso vira buttonWidth (bordas
        // encostando, zero sobreposicao possivel) por seguranca.
        int gap = Math.max(buttonWidth, Math.min(preferredGap, maxGap));

        layoutCenteredAt(mPreviousView, centerX - gap, mainRowCenterY);
        layoutCenteredAt(mNextView, centerX + gap, mainRowCenterY);

        updateExtraButtonsVisibility();

        int margin = buttonWidth / 2;

        // Correcao: EditCover (lapis) ficava perto/em cima do Play no
        // canto inferior direito em telas menores/paisagem. Movido para o
        // canto SUPERIOR direito da tela, espaco proprio, longe de
        // qualquer outro botao, sem sair das dimensoes da tela.
        // Correcao: "mais pra cima e mais pra direita" - inset bem menor
        // que o dos outros cantos (so o suficiente pra nao cortar/tocar a
        // borda da tela), grudado quase na quina superior direita.
        int editCoverMargin = Math.max(buttonWidth / 6, 1);
        int editCoverCenterY = top + editCoverMargin + mEditCoverView.getMeasuredHeight() / 2;
        int editCoverCenterX = w - editCoverMargin - mEditCoverView.getMeasuredWidth() / 2;
        layoutCenteredAt(mEditCoverView, editCoverCenterX, editCoverCenterY);

        // RepeatAll / RepeatOne: linha propria, bem mais proxima da
        // TimeBar (bem menos folga que a linha do EditCover acima),
        // grudados nos cantos esquerdo/direito, sem tocar a TimeBar nem
        // sair da tela.
        int repeatMargin = Math.max(buttonHeight / 6, 1);
        int repeatCornerY = h - mTimeBar.getPreferredHeight() - repeatMargin
                - mRepeatAllView.getMeasuredHeight() / 2;

        int repeatAllCenterX = margin + mRepeatAllView.getMeasuredWidth() / 2;
        layoutCenteredAt(mRepeatAllView, repeatAllCenterX, repeatCornerY);

        int repeatOneCenterX = w - margin - mRepeatOneView.getMeasuredWidth() / 2;
        layoutCenteredAt(mRepeatOneView, repeatOneCenterX, repeatCornerY);

        // Barra decorativa: do topo da linha principal de botoes (Anterior/
        // Play/Proxima, a mais alta de todas) ate o fim inferior da tela -
        // so enfeite, nao interfere em nenhum toque nem posicionamento.
        int backdropTop = mainRowCenterY - buttonHeight / 2;
        mControlsBackdrop.layout(0, backdropTop, w, h);
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
        mControlsBackdrop.setVisibility(visibility);
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

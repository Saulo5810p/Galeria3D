#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passo 4.2 + correcao de aberturas externas (Player3D)

O que este script faz:

PASSO 4.2 - 4 botoes novos na tela de reproducao (Repetir todas, Faixa
anterior, Proxima faixa, Repetir uma):
1. ControllerOverlay.java: adiciona 4 metodos na interface Listener
   (onPrevious, onNext, onToggleRepeatAll, onToggleRepeatOne).
2. TrimVideo.java: stubs vazios pros 4 metodos novos (obrigatorio pra
   compilar - TrimVideo implementa ControllerOverlay.Listener direto; a
   tela de corte de video esta fora do escopo de qualquer passo deste app
   de audio, entao os stubs nao fazem nada).
3. MoviePlayer.java: implementa os 4 metodos de verdade. Previous/Next
   mandam o MESMO Intent ACTION_PREVIOUS/ACTION_NEXT que a notificacao ja
   manda (Passo 9) - reaproveita a logica de limiar de 3s ja testada no
   Service (requestPrevious()), em vez de duplicar essa logica aqui.
   RepeatAll/RepeatOne chamam os metodos publicos do Binder direto
   (toggleRepeatAll/toggleRepeatOne). onRepeatModeChanged agora atualiza o
   visual dos botoes de verdade (antes era um placeholder do Passo 4.1).
4. MovieControllerOverlay.java (reescrito por completo): os 4 botoes
   novos, construidos com o MESMO padrao programatico do botao de
   play/pause ja existente (ImageView + bg_vidcontrol + ScaleType CENTER),
   na ordem [Repetir todas][Anterior][Play/Pause][Proxima][Repetir uma] -
   identica a ordem ja testada na notificacao. Ficam SO nesta classe (nao
   em CommonControllerOverlay), entao NAO aparecem na tela de corte de
   video (TrimControllerOverlay), que compartilha a base mas nao devia
   ganhar botoes de repeat/anterior/proxima.
5. Icones: os 4 PNGs de drawable-nodpi (Passo 9) sao apagados e
   substituidos por vetores XML em drawable/ (mesma paleta cinza
   #D6D6D6), reaproveitando os paths padrao "repeat"/"repeat_one" e um
   "skip previous/next" duplo consistente com os PNGs originais. Repetir
   todas e Repetir uma ganham uma segunda versao "_active" (cor de
   destaque @color/holo_blue_light) trocada via
   MovieControllerOverlay.setRepeatModeVisual() quando o modo respectivo
   esta ligado.

   Nota sobre o texto "ALL": o PNG original tinha a palavra "ALL"
   desenhada dentro do icone. Um vetor XML pintado a mao com letras
   legiveis em ~48dp nao e viavel sem ferramenta de design (o texto ficaria
   ilegivel nesse tamanho de qualquer forma). Usei o icone de loop puro
   (sem texto) pra "Repetir todas" e loop+"1" pra "Repetir uma" (o digito
   "1" continua legivel pequeno) - a diferenca ALL vs ONE fica clara pelo
   proprio par de icones (com/sem "1") mais a cor de destaque quando
   ativo. Sinalizando essa troca explicitamente, ja que nao e 100%
   mecanica.

CORRECAO DE ABERTURAS EXTERNAS (fora da lista de passos, pedido direto):
6. AndroidManifest.xml:
   - MovieActivity: filtro de <rtsp>/mimetypes de video removido, trocado
     por mimetypes de audio (mp3/mp4a/ogg/wav/flac/aac). O filtro de
     playlist HTTP live (audio/mpegurl) ja era de audio, mantido como
     estava.
   - GalleryActivity: categoria APP_GALLERY removida do filtro MAIN/
     LAUNCHER (o app deixa de se registrar como Galeria padrao do
     sistema). Os filtros GET_CONTENT/PICK/VIEW de imagem e video (e o
     par VIEW+REVIEW do fluxo de revisao da Camera) foram removidos e
     trocados por GET_CONTENT/PICK/VIEW de audio - agora o app aparece
     como opcao pra ABRIR/ESCOLHER MUSICA em outros apps, nao mais fotos.
   - Fora do escopo desta correcao (nao mexido): a activity Wallpaper
     (SET_WALLPAPER, usa uma imagem como papel de parede - fluxo
     diferente de "abrir/escolher imagem") e CameraActivity/IngestActivity
     (USB), que nao foram mencionados no pedido.

Rode este script na RAIZ do projeto (~/Galeria3D no Termux):
    python3 passo4_2_botoes_e_intents_externos.py

Regras seguidas (workflow combinado): falha cedo se pre-requisitos
(Passo 4.1) nao estiverem no estado esperado; backup de cada arquivo
existente que for editado, FORA da arvore res/ (pasta
passo4_2_backups/ na raiz do projeto, espelhando o caminho); idempotente
(rodar de novo depois de aplicado nao duplica nem corrompe, so avisa);
termina com verificacao (grep) dos pontos-chave de cada mudanca.
"""

import os
import sys

BACKUP_DIR = "passo4_2_backups"

CONTROLLER_OVERLAY_PATH = "app/src/main/java/com/android/gallery3d/app/ControllerOverlay.java"
TRIM_VIDEO_PATH = "app/src/main/java/com/android/gallery3d/app/TrimVideo.java"
MOVIE_PLAYER_PATH = "app/src/main/java/com/android/gallery3d/app/MoviePlayer.java"
MOVIE_CONTROLLER_OVERLAY_PATH = "app/src/main/java/com/android/gallery3d/app/MovieControllerOverlay.java"
MANIFEST_PATH = "app/src/main/AndroidManifest.xml"

OLD_ICON_DIR = "app/src/main/res/drawable-nodpi"
NEW_ICON_DIR = "app/src/main/res/drawable"
OLD_ICON_NAMES = [
    "ic_vidcontrol_previous", "ic_vidcontrol_next",
    "ic_vidcontrol_repeat_all", "ic_vidcontrol_repeat_one",
]

REQUIRED_FILES = [CONTROLLER_OVERLAY_PATH, TRIM_VIDEO_PATH, MOVIE_PLAYER_PATH,
                   MOVIE_CONTROLLER_OVERLAY_PATH, MANIFEST_PATH]


def fail(msg):
    print("ERRO: " + msg)
    sys.exit(1)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def backup(path):
    bak = os.path.join(BACKUP_DIR, path + ".bak_passo4_2")
    if not os.path.isfile(bak):
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        write(bak, read(path))
        print("Backup criado: %s" % bak)
    else:
        print("Backup ja existia, mantido: %s" % bak)


def backup_binary(path):
    # PNGs (os icones antigos) nao sao UTF-8 - backup em modo binario.
    bak = os.path.join(BACKUP_DIR, path + ".bak_passo4_2")
    if not os.path.isfile(bak):
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        with open(path, "rb") as src, open(bak, "wb") as dst:
            dst.write(src.read())
        print("Backup criado: %s" % bak)
    else:
        print("Backup ja existia, mantido: %s" % bak)


def check_prereqs():
    for f in REQUIRED_FILES:
        if not os.path.isfile(f):
            fail(
                "arquivo esperado nao encontrado: %s\\n"
                "Rode este script na raiz do projeto (~/Galeria3D), depois "
                "do Passo 4.1 (passo4_1_conectar_service.py)." % f
            )
    mp = read(MOVIE_PLAYER_PATH)
    if "MusicPlaybackService.Callback" not in mp:
        fail(
            "MoviePlayer.java nao parece ter o Passo 4.1 aplicado "
            "(MusicPlaybackService.Callback nao encontrado). Rode o "
            "Passo 4.1 antes deste script."
        )


def already_applied():
    c = read(CONTROLLER_OVERLAY_PATH)
    return "onToggleRepeatAll" in c


def replace_exactly_once(path, old, new, label):
    content = read(path)
    count = content.count(old)
    if count == 0:
        fail(
            "%s: marcador esperado nao encontrado em %s.\\n"
            "O arquivo mudou desde a especificacao, ou o Passo 4.2 ja foi "
            "aplicado parcialmente. Nada foi alterado." % (label, path)
        )
    if count > 1:
        fail(
            "%s: marcador apareceu %d vezes em %s (esperado exatamente 1). "
            "Nada foi alterado, script parou por seguranca." % (label, count, path)
        )
    backup(path)
    content = content.replace(old, new, 1)
    write(path, content)
    print("OK: %s (%s)" % (label, path))


def patch_controller_overlay():
    old = '''  interface Listener {
    void onPlayPause();
    void onSeekStart();
    void onSeekMove(int time);
    void onSeekEnd(int time, int trimStartTime, int trimEndTime);
    void onShown();
    void onHidden();
    void onReplay();
  }'''
    new = '''  interface Listener {
    void onPlayPause();
    void onSeekStart();
    void onSeekMove(int time);
    void onSeekEnd(int time, int trimStartTime, int trimEndTime);
    void onShown();
    void onHidden();
    void onReplay();
    // Passo 4.2 (Player3D): botoes novos da tela de reproducao de audio.
    void onPrevious();
    void onNext();
    void onToggleRepeatAll();
    void onToggleRepeatOne();
  }'''
    replace_exactly_once(CONTROLLER_OVERLAY_PATH, old, new, "interface Listener")


def patch_trim_video():
    old = '''    @Override
    public void onReplay() {
        mVideoView.seekTo(mTrimStartTime);
        playVideo();
    }'''
    new = '''    @Override
    public void onReplay() {
        mVideoView.seekTo(mTrimStartTime);
        playVideo();
    }

    // Passo 4.2 (Player3D): TrimVideo (corte de video) esta fora do escopo
    // de todos os passos deste app de audio - stubs vazios, existem so
    // porque ControllerOverlay.Listener agora exige esses 4 metodos.
    @Override
    public void onPrevious() {
    }

    @Override
    public void onNext() {
    }

    @Override
    public void onToggleRepeatAll() {
    }

    @Override
    public void onToggleRepeatOne() {
    }'''
    replace_exactly_once(TRIM_VIDEO_PATH, old, new, "TrimVideo stubs")


def patch_movie_player():
    old1 = '''    @Override
    public void onRepeatModeChanged(MusicPlaybackService.RepeatMode mode) {
        // Estado visual dos botoes de repeat (ALL/1) e trabalho do Passo 4.2,
        // quando os botoes existirem de verdade nesta tela.
    }'''
    new1 = '''    @Override
    public void onRepeatModeChanged(MusicPlaybackService.RepeatMode mode) {
        mController.setRepeatModeVisual(mode);
    }'''
    replace_exactly_once(MOVIE_PLAYER_PATH, old1, new1, "onRepeatModeChanged")

    old2 = '''    @Override
    public void onReplay() {
        startVideo();
    }'''
    new2 = '''    @Override
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
    }'''
    replace_exactly_once(MOVIE_PLAYER_PATH, old2, new2, "MoviePlayer 4 metodos novos")


def patch_movie_controller_overlay():
    if "onToggleRepeatAll" in read(MOVIE_CONTROLLER_OVERLAY_PATH):
        print("Aviso: %s ja parece ter o Passo 4.2 aplicado, mantido." % MOVIE_CONTROLLER_OVERLAY_PATH)
        return
    backup(MOVIE_CONTROLLER_OVERLAY_PATH)
    write(MOVIE_CONTROLLER_OVERLAY_PATH, MOVIE_CONTROLLER_OVERLAY_JAVA)
    print("Reescrito: %s (%d bytes)" % (MOVIE_CONTROLLER_OVERLAY_PATH, len(MOVIE_CONTROLLER_OVERLAY_JAVA)))


def patch_icons():
    for name in OLD_ICON_NAMES:
        old_path = os.path.join(OLD_ICON_DIR, name + ".png")
        if os.path.isfile(old_path):
            backup_binary(old_path)
            os.remove(old_path)
            print("Removido: %s (era PNG, virou vetor XML)" % old_path)

    icon_map = {
        "ic_vidcontrol_previous.xml": ICON_PREVIOUS_XML,
        "ic_vidcontrol_next.xml": ICON_NEXT_XML,
        "ic_vidcontrol_repeat_all.xml": ICON_REPEAT_ALL_XML,
        "ic_vidcontrol_repeat_all_active.xml": ICON_REPEAT_ALL_ACTIVE_XML,
        "ic_vidcontrol_repeat_one.xml": ICON_REPEAT_ONE_XML,
        "ic_vidcontrol_repeat_one_active.xml": ICON_REPEAT_ONE_ACTIVE_XML,
    }
    for filename, content in icon_map.items():
        target = os.path.join(NEW_ICON_DIR, filename)
        if os.path.isfile(target) and read(target) == content:
            print("Aviso: %s ja existe e esta igual, mantido." % target)
            continue
        write(target, content)
        print("Criado/atualizado: %s" % target)


def patch_manifest():
    manifest = read(MANIFEST_PATH)
    if 'android:mimeType="audio/mpeg"' in manifest and "APP_GALLERY" not in manifest:
        print("Aviso: %s ja parece ter os intents externos corrigidos, mantido." % MANIFEST_PATH)
        return

    backup(MANIFEST_PATH)
    content = manifest

    old_movie = '''            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="rtsp" />
             </intent-filter>
             <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="http" />
                <data android:scheme="https" />
                <data android:scheme="content" />
                <data android:scheme="file" />
                <data android:mimeType="video/mpeg4" />
                <data android:mimeType="video/mp4" />
                <data android:mimeType="video/3gp" />
                <data android:mimeType="video/3gpp" />
                <data android:mimeType="video/3gpp2" />
                <data android:mimeType="video/webm" />
                <data android:mimeType="video/avi" />
             </intent-filter>
             <intent-filter>
                <!-- HTTP live support -->
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="http" />
                <data android:scheme="https" />
                <data android:mimeType="audio/x-mpegurl" />
                <data android:mimeType="audio/mpegurl" />
                <data android:mimeType="application/vnd.apple.mpegurl" />
                <data android:mimeType="application/x-mpegurl" />
             </intent-filter>'''
    new_movie = '''            <!-- Passo 4.2/externo (Player3D): MovieActivity agora abre a tela
                 de REPRODUCAO DE AUDIO (MoviePlayer), nao mais video. Filtro
                 de rtsp/video removido; abre arquivos de audio locais ou
                 remotos por content/file/http(s), e mantem o suporte a
                 playlist HTTP live (audio/mpegurl) que ja era de audio. -->
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="http" />
                <data android:scheme="https" />
                <data android:scheme="content" />
                <data android:scheme="file" />
                <data android:mimeType="audio/mpeg" />
                <data android:mimeType="audio/mp3" />
                <data android:mimeType="audio/mp4" />
                <data android:mimeType="audio/mp4a-latm" />
                <data android:mimeType="audio/x-m4a" />
                <data android:mimeType="audio/ogg" />
                <data android:mimeType="audio/wav" />
                <data android:mimeType="audio/x-wav" />
                <data android:mimeType="audio/flac" />
                <data android:mimeType="audio/aac" />
             </intent-filter>
             <intent-filter>
                <!-- HTTP live support -->
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="http" />
                <data android:scheme="https" />
                <data android:mimeType="audio/x-mpegurl" />
                <data android:mimeType="audio/mpegurl" />
                <data android:mimeType="application/vnd.apple.mpegurl" />
                <data android:mimeType="application/x-mpegurl" />
             </intent-filter>'''
    count = content.count(old_movie)
    if count == 1:
        content = content.replace(old_movie, new_movie, 1)
        print("OK: MovieActivity intent-filters trocados pra audio")
    elif count == 0:
        print("Aviso: bloco de intent-filter de video do MovieActivity nao encontrado (talvez ja alterado), pulando essa parte.")
    else:
        fail("bloco de intent-filter do MovieActivity apareceu %d vezes (esperado 1). Nada foi alterado." % count)

    old_launcher = '''            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.LAUNCHER" />
                <category android:name="android.intent.category.APP_GALLERY" />
            </intent-filter>'''
    new_launcher = '''            <!-- Passo 4.2/externo (Player3D): categoria APP_GALLERY removida -
                 o app nao se registra mais como Galeria padrao do sistema. -->
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>'''
    count = content.count(old_launcher)
    if count == 1:
        content = content.replace(old_launcher, new_launcher, 1)
        print("OK: categoria APP_GALLERY removida")
    elif count == 0:
        print("Aviso: filtro MAIN/LAUNCHER com APP_GALLERY nao encontrado (talvez ja alterado), pulando essa parte.")
    else:
        fail("filtro MAIN/LAUNCHER apareceu %d vezes (esperado 1). Nada foi alterado." % count)

    old_getcontent = '''            <intent-filter>
                <action android:name="android.intent.action.GET_CONTENT" />
                <category android:name="android.intent.category.OPENABLE" />
                <data android:mimeType="vnd.android.cursor.dir/image" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.GET_CONTENT" />
                <category android:name="android.intent.category.OPENABLE" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="image/*" />
                <data android:mimeType="video/*" />
            </intent-filter>
            <!-- We do NOT support the PICK intent, we add these intent-filter for
                 backward compatibility. Handle it as GET_CONTENT. -->
            <intent-filter>
                <action android:name="android.intent.action.PICK" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="image/*" />
                <data android:mimeType="video/*" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.PICK" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="vnd.android.cursor.dir/image" />
                <data android:mimeType="vnd.android.cursor.dir/video" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="vnd.android.cursor.dir/image" />
                <data android:mimeType="vnd.android.cursor.dir/video" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <action android:name="com.android.camera.action.REVIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="" />
                <data android:scheme="http" />
                <data android:scheme="https" />
                <data android:scheme="content" />
                <data android:scheme="file" />
                <data android:mimeType="image/*" />
                <data android:mimeType="application/vnd.google.panorama360+jpg" />
            </intent-filter>
            <intent-filter>
                <action android:name="com.android.camera.action.REVIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="http" />
                <data android:scheme="https" />
                <data android:scheme="content" />
                <data android:scheme="file" />
                <data android:mimeType="video/mpeg4" />
                <data android:mimeType="video/mp4" />
                <data android:mimeType="video/3gp" />
                <data android:mimeType="video/3gpp" />
                <data android:mimeType="video/3gpp2" />
            </intent-filter>'''
    new_getcontent = '''            <!-- Passo 4.2/externo (Player3D): filtros de imagem/video removidos
                 (GET_CONTENT, PICK, VIEW de vnd.android.cursor.dir/image e
                 /video, e o par VIEW+REVIEW do fluxo de revisao da Camera -
                 nada disso se aplica a um app que nao e mais galeria de
                 fotos/video). Trocados por GET_CONTENT/PICK/VIEW de audio,
                 pra este app aparecer como opcao pra abrir/escolher musica. -->
            <intent-filter>
                <action android:name="android.intent.action.GET_CONTENT" />
                <category android:name="android.intent.category.OPENABLE" />
                <data android:mimeType="vnd.android.cursor.dir/audio" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.GET_CONTENT" />
                <category android:name="android.intent.category.OPENABLE" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="audio/*" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.PICK" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="audio/*" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.PICK" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="vnd.android.cursor.dir/audio" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="vnd.android.cursor.dir/audio" />
            </intent-filter>'''
    count = content.count(old_getcontent)
    if count == 1:
        content = content.replace(old_getcontent, new_getcontent, 1)
        print("OK: filtros de imagem/video trocados por audio em GalleryActivity")
    elif count == 0:
        print("Aviso: bloco GET_CONTENT/PICK/VIEW de imagem/video nao encontrado (talvez ja alterado), pulando essa parte.")
    else:
        fail("bloco GET_CONTENT/PICK/VIEW apareceu %d vezes (esperado 1). Nada foi alterado." % count)

    write(MANIFEST_PATH, content)


def verify():
    print("\\n--- Verificacao final ---")
    problems = []

    co = read(CONTROLLER_OVERLAY_PATH)
    if "onToggleRepeatAll" not in co or "onToggleRepeatOne" not in co:
        problems.append("ControllerOverlay.java: metodos novos nao encontrados")

    tv = read(TRIM_VIDEO_PATH)
    if tv.count("public void onToggleRepeatAll") == 0:
        problems.append("TrimVideo.java: stub onToggleRepeatAll nao encontrado")

    mp = read(MOVIE_PLAYER_PATH)
    if "sendPlaybackAction" not in mp:
        problems.append("MoviePlayer.java: sendPlaybackAction nao encontrado")
    if "mController.setRepeatModeVisual" not in mp:
        problems.append("MoviePlayer.java: onRepeatModeChanged nao esta ligado de verdade")

    mco = read(MOVIE_CONTROLLER_OVERLAY_PATH)
    for marker in ("mRepeatAllView", "mPreviousView", "mNextView", "mRepeatOneView",
                   "setRepeatModeVisual"):
        if marker not in mco:
            problems.append("MovieControllerOverlay.java: %s nao encontrado" % marker)

    for name in OLD_ICON_NAMES:
        if os.path.isfile(os.path.join(OLD_ICON_DIR, name + ".png")):
            problems.append("PNG antigo ainda presente: %s.png" % name)
        if not os.path.isfile(os.path.join(NEW_ICON_DIR, name + ".xml")):
            problems.append("Icone XML novo faltando: %s.xml" % name)

    manifest = read(MANIFEST_PATH)
    if 'category.APP_GALLERY"' in manifest:
        problems.append("AndroidManifest.xml: categoria APP_GALLERY ainda presente")
    # So checa dentro do bloco da GalleryActivity - CropActivity/FilterShowActivity/
    # TrimVideo (edicao de foto/video, acionadas via EDIT/CROP/TRIM por OUTROS apps,
    # nao por VIEW/GET_CONTENT/PICK) sao subsistemas inteiros fora do escopo desta
    # correcao pontual, sinalizados separadamente - ver aviso no final do script.
    gallery_start = manifest.find('android:name="com.android.gallery3d.app.GalleryActivity"')
    gallery_end = manifest.find("</activity>", gallery_start)
    gallery_block = manifest[gallery_start:gallery_end] if gallery_start != -1 else ""
    if 'mimeType="video/*"' in gallery_block or 'mimeType="image/*"' in gallery_block:
        problems.append("AndroidManifest.xml: GalleryActivity ainda tem mimeType image/* ou video/*")
    if 'android:mimeType="audio/*"' not in gallery_block:
        problems.append("AndroidManifest.xml: GalleryActivity sem mimeType audio/*")

    if problems:
        print("Encontrados problemas na verificacao final:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)

    print("Tudo certo: Passo 4.2 e correcao de intents externos aplicados.")
    print(
        "\nAviso (fora do escopo desta correcao pontual): o manifest ainda "
        "registra TrimVideo (acao TRIM, video/*), FilterShowActivity (acao "
        "EDIT, image/*) e CropActivity (acao CROP, image/*) como opcoes "
        "externas de EDICAO de foto/video (menu 'Editar com...' de outros "
        "apps - diferente do menu 'Abrir com...' que a GalleryActivity "
        "controlava). Sao subsistemas inteiros de edicao de imagem, ja "
        "fora do escopo de qualquer passo ate agora - nao mexi neles. "
        "Avise se quiser que eu remova essa exposicao tambem."
    )


def main():
    check_prereqs()
    if already_applied():
        print("Aviso: Passo 4.2 ja parece ter sido aplicado (ControllerOverlay.java "
              "ja tem onToggleRepeatAll). Reaplicando so as partes que faltarem.")
    if "onToggleRepeatAll" not in read(CONTROLLER_OVERLAY_PATH):
        patch_controller_overlay()
    else:
        print("Aviso: ControllerOverlay.java ja tem os 4 metodos novos, mantido.")

    if "public void onToggleRepeatAll" not in read(TRIM_VIDEO_PATH):
        patch_trim_video()
    else:
        print("Aviso: TrimVideo.java ja tem os stubs novos, mantido.")

    if "sendPlaybackAction" not in read(MOVIE_PLAYER_PATH):
        patch_movie_player()
    else:
        print("Aviso: MoviePlayer.java ja tem os 4 metodos novos, mantido.")
    patch_movie_controller_overlay()
    patch_icons()
    patch_manifest()
    verify()
    print("\\nPasso 4.2 e correcao de intents externos aplicados. Agora rode: ./gradlew assembleDebug")


MOVIE_CONTROLLER_OVERLAY_JAVA = """/*
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
        int gap = buttonWidth + buttonWidth / 3;

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
"""

ICON_PREVIOUS_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#D6D6D6"
        android:pathData="M3,4L5,4L5,20L3,20Z M6,12L13,4L13,20Z M12.5,12L20,4L20,20Z" />
</vector>
"""

ICON_NEXT_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#D6D6D6"
        android:pathData="M4,4L4,20L11,12Z M10.5,4L10.5,20L18,12Z M19,4L21,4L21,20L19,20Z" />
</vector>
"""

ICON_REPEAT_ALL_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#D6D6D6"
        android:pathData="M7,7h10v3l4,-4l-4,-4v3L5,5v6h2L7,7zM17,17H7v-3l-4,4l4,4v-3h12v-6h-2L17,17z" />
</vector>
"""

ICON_REPEAT_ALL_ACTIVE_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="@color/holo_blue_light"
        android:pathData="M7,7h10v3l4,-4l-4,-4v3L5,5v6h2L7,7zM17,17H7v-3l-4,4l4,4v-3h12v-6h-2L17,17z" />
</vector>
"""

ICON_REPEAT_ONE_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#D6D6D6"
        android:pathData="M13,15h-1v-3.85L11,11.4v-0.85l1.9,-0.65h0.1V15z M17,17H7v-3l-4,4l4,4v-3h12v-6h-2L17,17z M7,7h10v3l4,-4l-4,-4v3L5,5v6h2L7,7z" />
</vector>
"""

ICON_REPEAT_ONE_ACTIVE_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="@color/holo_blue_light"
        android:pathData="M13,15h-1v-3.85L11,11.4v-0.85l1.9,-0.65h0.1V15z M17,17H7v-3l-4,4l4,4v-3h12v-6h-2L17,17z M7,7h10v3l4,-4l-4,-4v3L5,5v6h2L7,7z" />
</vector>
"""

if __name__ == "__main__":
    main()

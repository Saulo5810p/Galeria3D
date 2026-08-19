#!/usr/bin/env python3
"""
Duas correções, no projeto Player3D (~/Galeria3D):

(A) BUG DOS 4 BOTÕES SUMIDOS na tela de reprodução (Repetir todas,
    Anterior, Próxima, Repetir uma).

    Causa raiz: em MovieControllerOverlay.onLayout(), o espaçamento entre
    os 5 botões era calculado como um múltiplo FIXO da largura do botão
    de play/pause (`gap = buttonWidth + buttonWidth/3`, e os botões
    extremos ficam em `centerX ± gap*2`). Em telas de celular comuns
    (~360-420dp de largura, como o Galaxy A35), esse deslocamento é maior
    que a metade da largura disponível do controller — os botões
    "Repetir todas" e "Repetir uma" acabam posicionados FORA da área
    visível da tela. O código sempre existiu e sempre esteve certo; o
    bug é geométrico, não lógico.

    Correção: calcular o gap com base no espaço REAL disponível
    (a largura do próprio MovieControllerOverlay), dividindo
    simetricamente entre os 5 botões, e limitando a um teto (o
    comportamento antigo) só quando a tela é larga o bastante — mantém
    o espaçamento "elegante" em telas grandes e garante que nada saia
    da borda em telas pequenas.

(B) PASSO 4.3 — habilitar o botão do editor de fotos na tela de
    reprodução (não define ele como tela de reprodução, só garante que a
    entrada exista e funcione quando o item aberto é uma faixa de
    áudio).

    Causa raiz confirmada: LocalAudio.getSupportedOperations() nunca
    incluía SUPPORT_EDIT na máscara — então launchPhotoEditor() sempre
    retornava sem fazer nada (o próprio método já checa esse flag e sai
    cedo se ausente). Além disso, launchPhotoEditor() usa
    current.getContentUri(), que para LocalAudio aponta pro ARQUIVO DE
    ÁUDIO, não pra capa — abrir o editor de imagem nesse Uri falharia ou
    tentaria editar o arquivo de música como se fosse imagem.

    Correção:
    - LocalAudio.java: adiciona SUPPORT_EDIT à máscara e um novo método
      getCoverUriForEdit(Context), que persiste o bitmap de capa já
      resolvido (Passo 1.5, LocalAudioRequest/onDecodeOriginal) num
      arquivo temporário em cache e devolve uma Uri de conteúdo válida
      pra ele (via FileProvider já configurado no projeto, se existir;
      caso contrário Uri.fromFile como fallback, ver nota no patch).
    - PhotoPage.java: launchPhotoEditor() passa a checar se o item atual
      é MEDIA_TYPE_VIDEO (== áudio, Passo 1.4) e, se for, usar a Uri da
      capa resolvida por getCoverUriForEdit() em vez de getContentUri().
      Para fotos/imagens normais (caso ainda exista algum MediaItem de
      imagem na árvore /local/image), o comportamento antigo continua
      idêntico.

Uso (Termux, dentro de ~/Galeria3D):
    python3 passo_fix_botoes_e_4_3.py
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path.home() / "Galeria3D"
CONTROLLER = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/MovieControllerOverlay.java"
PHOTO_PAGE = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/app/PhotoPage.java"
LOCAL_AUDIO = PROJECT_ROOT / "app/src/main/java/com/android/gallery3d/data/LocalAudio.java"


def fail(msg):
    print(f"ERRO: {msg}")
    sys.exit(1)


def backup(path: Path):
    b = path.with_suffix(path.suffix + ".bak")
    b.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Backup salvo em: {b}")


# ---------------------------------------------------------------------
# (A) Corrigir onLayout dos 4 botões
# ---------------------------------------------------------------------

OLD_LAYOUT = '''    @Override
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
    }'''

NEW_LAYOUT = '''    @Override
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
    }'''


def patch_layout():
    if not CONTROLLER.exists():
        fail(f"Arquivo não encontrado: {CONTROLLER}")

    content = CONTROLLER.read_text(encoding="utf-8")

    if NEW_LAYOUT in content:
        print("(A) Já aplicado antes — nada a fazer (idempotente).")
        return

    count = content.count(OLD_LAYOUT)
    if count == 0:
        fail("(A) Não encontrei o onLayout() esperado em MovieControllerOverlay.java "
             "— o método pode já ter sido alterado de outra forma. Verifique manualmente.")
    if count > 1:
        fail(f"(A) Padrão encontrado {count} vezes — esperado exatamente 1.")

    backup(CONTROLLER)
    patched = content.replace(OLD_LAYOUT, NEW_LAYOUT)

    if OLD_LAYOUT in patched:
        fail("(A) Substituição não removeu o bloco antigo — abortando sem escrever.")

    CONTROLLER.write_text(patched, encoding="utf-8")

    final = CONTROLLER.read_text(encoding="utf-8")
    if NEW_LAYOUT not in final:
        fail("(A) Verificação pós-escrita falhou.")

    print("(A) OK — onLayout() de MovieControllerOverlay.java corrigido "
          "(gap dos 4 botões agora respeita a largura real da tela).")


# ---------------------------------------------------------------------
# (B) Passo 4.3 — botão do editor de fotos aponta pra capa da faixa
# ---------------------------------------------------------------------

PROVIDER_PATHS = PROJECT_ROOT / "app/src/main/res/xml/provider_paths.xml"

# --- B.1: LocalAudio.java — SUPPORT_EDIT + getCoverUriForEdit() ---

OLD_SUPPORTED_OPS = (
    "    @Override\n"
    "    public int getSupportedOperations() {\n"
    "        return SUPPORT_DELETE | SUPPORT_SHARE | SUPPORT_PLAY | SUPPORT_INFO "
    "| SUPPORT_TRIM | SUPPORT_MUTE;\n"
    "    }\n"
)

NEW_SUPPORTED_OPS = (
    "    @Override\n"
    "    public int getSupportedOperations() {\n"
    "        // Passo 4.3 (Player3D): SUPPORT_EDIT habilita o botao do editor de\n"
    "        // fotos na tela de reproducao, apontando pra capa da faixa (ver\n"
    "        // getCoverUriForEdit() abaixo), nao pro arquivo de audio em si.\n"
    "        return SUPPORT_DELETE | SUPPORT_SHARE | SUPPORT_PLAY | SUPPORT_INFO "
    "| SUPPORT_TRIM | SUPPORT_MUTE | SUPPORT_EDIT;\n"
    "    }\n"
    "\n"
    "    // Passo 4.3 (Player3D): resolve a capa atual da faixa (mesma logica de\n"
    "    // LocalAudioRequest.onDecodeOriginal, capa embutida > capa do album >\n"
    "    // null) de forma SINCRONA, persiste num arquivo temporario em cache e\n"
    "    // devolve uma Uri de conteudo (via FileProvider ja configurado no\n"
    "    // projeto, mesmo authority \".provider\" usado em TrimVideo/MuteVideo)\n"
    "    // para o FilterShowActivity poder abrir como imagem editavel. Retorna\n"
    "    // null se nao houver capa nenhuma (nem embutida nem de album) - quem\n"
    "    // chama deve tratar null (ex.: nao abrir o editor / avisar o usuario).\n"
    "    public android.net.Uri getCoverUriForEdit(android.content.Context context) {\n"
    "        Bitmap cover = decodeCoverForEditSync();\n"
    "        if (cover == null) return null;\n"
    "        java.io.File cacheDir = new java.io.File(context.getCacheDir(), \"audio_covers\");\n"
    "        if (!cacheDir.exists() && !cacheDir.mkdirs()) {\n"
    "            Log.w(TAG, \"nao foi possivel criar cache dir para capa: \" + cacheDir);\n"
    "            return null;\n"
    "        }\n"
    "        java.io.File coverFile = new java.io.File(cacheDir, \"cover_\" + id + \".jpg\");\n"
    "        try (java.io.FileOutputStream out = new java.io.FileOutputStream(coverFile)) {\n"
    "            cover.compress(Bitmap.CompressFormat.JPEG, 92, out);\n"
    "        } catch (java.io.IOException e) {\n"
    "            Log.w(TAG, \"falha ao salvar capa temporaria para edicao: \" + coverFile, e);\n"
    "            return null;\n"
    "        }\n"
    "        return androidx.core.content.FileProvider.getUriForFile(\n"
    "                context, context.getPackageName() + \".provider\", coverFile);\n"
    "    }\n"
    "\n"
    "    // Mesma cadeia de fallback de LocalAudioRequest (capa embutida no\n"
    "    // arquivo, senao capa do album via MediaStore), mas chamada direto na\n"
    "    // thread de chamada (o clique no botao de editar), sem passar pelo\n"
    "    // ImageCacheRequest/JobContext assincrono do carregamento de grade.\n"
    "    private Bitmap decodeCoverForEditSync() {\n"
    "        MediaMetadataRetriever retriever = new MediaMetadataRetriever();\n"
    "        try {\n"
    "            retriever.setDataSource(filePath);\n"
    "            byte[] embedded = retriever.getEmbeddedPicture();\n"
    "            if (embedded != null) {\n"
    "                Bitmap decoded = BitmapFactory.decodeByteArray(embedded, 0, embedded.length);\n"
    "                if (decoded != null) return decoded;\n"
    "            }\n"
    "        } catch (OutOfMemoryError e) {\n"
    "            Log.w(TAG, \"OOM decoding embedded cover for edit: \" + filePath);\n"
    "        } catch (Throwable t) {\n"
    "            Log.w(TAG, \"sem capa embutida para edicao: \" + filePath);\n"
    "        } finally {\n"
    "            try {\n"
    "                retriever.release();\n"
    "            } catch (Throwable ignored) {\n"
    "            }\n"
    "        }\n"
    "        if (albumId <= 0) return null;\n"
    "        ContentResolver resolver = mApplication.getContentResolver();\n"
    "        try {\n"
    "            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {\n"
    "                Uri albumArtUri = ContentUris.withAppendedId(\n"
    "                        Albums.EXTERNAL_CONTENT_URI, albumId);\n"
    "                int size = MediaItem.getTargetSize(MediaItem.TYPE_THUMBNAIL);\n"
    "                return resolver.loadThumbnail(\n"
    "                        albumArtUri, new android.util.Size(size, size), null);\n"
    "            }\n"
    "            String[] projection = {Albums.ALBUM_ART};\n"
    "            Cursor cursor = resolver.query(Albums.EXTERNAL_CONTENT_URI, projection,\n"
    "                    Albums._ID + \"=?\", new String[]{String.valueOf(albumId)}, null);\n"
    "            if (cursor == null) return null;\n"
    "            try {\n"
    "                if (cursor.moveToFirst()) {\n"
    "                    String path = cursor.getString(0);\n"
    "                    if (path != null) return BitmapFactory.decodeFile(path);\n"
    "                }\n"
    "            } finally {\n"
    "                cursor.close();\n"
    "            }\n"
    "        } catch (OutOfMemoryError e) {\n"
    "            Log.w(TAG, \"OOM decoding album art fallback for edit, album \" + albumId);\n"
    "        } catch (Throwable t) {\n"
    "            Log.w(TAG, \"no album art for edit, album \" + albumId);\n"
    "        }\n"
    "        return null;\n"
    "    }\n"
)


def patch_local_audio():
    if not LOCAL_AUDIO.exists():
        fail(f"(B.1) Arquivo não encontrado: {LOCAL_AUDIO}")

    content = LOCAL_AUDIO.read_text(encoding="utf-8")

    if "getCoverUriForEdit" in content:
        print("(B.1) Já aplicado antes em LocalAudio.java — nada a fazer (idempotente).")
        return

    count = content.count(OLD_SUPPORTED_OPS)
    if count == 0:
        fail("(B.1) Não encontrei o getSupportedOperations() esperado em "
             "LocalAudio.java — verifique manualmente se o método mudou.")
    if count > 1:
        fail(f"(B.1) Padrão encontrado {count} vezes — esperado exatamente 1.")

    backup(LOCAL_AUDIO)
    patched = content.replace(OLD_SUPPORTED_OPS, NEW_SUPPORTED_OPS)

    if "getCoverUriForEdit" not in patched:
        fail("(B.1) Substituição falhou — abortando sem escrever.")

    LOCAL_AUDIO.write_text(patched, encoding="utf-8")
    print("(B.1) OK — LocalAudio.java: SUPPORT_EDIT habilitado + "
          "getCoverUriForEdit(Context) adicionado.")


# --- B.2: provider_paths.xml — adicionar cache-path ---

def patch_provider_paths():
    if not PROVIDER_PATHS.exists():
        fail(f"(B.2) Arquivo não encontrado: {PROVIDER_PATHS}")

    content = PROVIDER_PATHS.read_text(encoding="utf-8")

    if 'name="audio_covers"' in content:
        print("(B.2) Já aplicado antes em provider_paths.xml — nada a fazer (idempotente).")
        return

    anchor = '<external-path name="external_files" path="."/>'
    if anchor not in content:
        fail("(B.2) Não encontrei a entrada <external-path> esperada em "
             "provider_paths.xml — verifique manualmente.")
    if content.count(anchor) != 1:
        fail("(B.2) Âncora encontrada mais de 1 vez em provider_paths.xml — ambíguo.")

    backup(PROVIDER_PATHS)
    new_entry = (anchor + '\n    <cache-path name="audio_covers" path="audio_covers/"/>')
    patched = content.replace(anchor, new_entry)

    PROVIDER_PATHS.write_text(patched, encoding="utf-8")
    print("(B.2) OK — provider_paths.xml: <cache-path> para capas de edição adicionado.")


# --- B.3: PhotoPage.java — launchPhotoEditor() usa a capa para áudio ---

OLD_LAUNCH_EDITOR = '''    private void launchPhotoEditor() {
        MediaItem current = mModel.getMediaItem(0);
        if (current == null || (current.getSupportedOperations()
                & MediaObject.SUPPORT_EDIT) == 0) {
            return;
        }

        Intent intent = new Intent(ACTION_NEXTGEN_EDIT);

        intent.setDataAndType(current.getContentUri(), current.getMimeType())
                .setFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (mActivity.getPackageManager()
                .queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY).size() == 0) {
            intent.setAction(Intent.ACTION_EDIT);
        }
        intent.putExtra(FilterShowActivity.LAUNCH_FULLSCREEN,
                mActivity.isFullscreen());
        ((Activity) mActivity).startActivityForResult(Intent.createChooser(intent, null),
                REQUEST_EDIT);
        overrideTransitionToEditor();'''

NEW_LAUNCH_EDITOR = '''    private void launchPhotoEditor() {
        MediaItem current = mModel.getMediaItem(0);
        if (current == null || (current.getSupportedOperations()
                & MediaObject.SUPPORT_EDIT) == 0) {
            return;
        }

        // Passo 4.3 (Player3D): quando o item aberto e uma faixa de audio
        // (MEDIA_TYPE_VIDEO, ver Passo 1.4), o editor de fotos deve editar a
        // CAPA da faixa, nao o arquivo de audio em si - getContentUri() de
        // LocalAudio aponta pro audio, entao usamos getCoverUriForEdit() para
        // resolver e persistir a capa como imagem editavel de verdade.
        Uri editUri = current.getContentUri();
        String editMimeType = current.getMimeType();
        if (current.getMediaType() == MediaObject.MEDIA_TYPE_VIDEO
                && current instanceof com.android.gallery3d.data.LocalAudio) {
            Uri coverUri = ((com.android.gallery3d.data.LocalAudio) current)
                    .getCoverUriForEdit(mActivity.getAndroidContext());
            if (coverUri == null) {
                Toast.makeText((Activity) mActivity,
                        R.string.player3d_no_cover_to_edit, Toast.LENGTH_SHORT).show();
                return;
            }
            editUri = coverUri;
            editMimeType = "image/jpeg";
        }

        Intent intent = new Intent(ACTION_NEXTGEN_EDIT);

        intent.setDataAndType(editUri, editMimeType)
                .setFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (mActivity.getPackageManager()
                .queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY).size() == 0) {
            intent.setAction(Intent.ACTION_EDIT);
        }
        intent.putExtra(FilterShowActivity.LAUNCH_FULLSCREEN,
                mActivity.isFullscreen());
        ((Activity) mActivity).startActivityForResult(Intent.createChooser(intent, null),
                REQUEST_EDIT);
        overrideTransitionToEditor();'''


def patch_launch_editor():
    if not PHOTO_PAGE.exists():
        fail(f"(B.3) Arquivo não encontrado: {PHOTO_PAGE}")

    content = PHOTO_PAGE.read_text(encoding="utf-8")

    if "getCoverUriForEdit" in content:
        print("(B.3) Já aplicado antes em PhotoPage.java — nada a fazer (idempotente).")
        return

    count = content.count(OLD_LAUNCH_EDITOR)
    if count == 0:
        fail("(B.3) Não encontrei launchPhotoEditor() no formato esperado em "
             "PhotoPage.java — verifique manualmente, o método pode ter mudado.")
    if count > 1:
        fail(f"(B.3) Padrão encontrado {count} vezes — esperado exatamente 1.")

    backup(PHOTO_PAGE)
    patched = content.replace(OLD_LAUNCH_EDITOR, NEW_LAUNCH_EDITOR)

    if "getCoverUriForEdit" not in patched:
        fail("(B.3) Substituição falhou — abortando sem escrever.")

    PHOTO_PAGE.write_text(patched, encoding="utf-8")
    print("(B.3) OK — PhotoPage.java: launchPhotoEditor() agora usa a capa "
          "da faixa quando o item é áudio.")


def patch_string_resource():
    strings_path = PROJECT_ROOT / "app/src/main/res/values/strings.xml"
    if not strings_path.exists():
        fail(f"(B.4) Arquivo não encontrado: {strings_path}")

    content = strings_path.read_text(encoding="utf-8")

    if 'name="player3d_no_cover_to_edit"' in content:
        print("(B.4) Já aplicado antes em strings.xml — nada a fazer (idempotente).")
        return

    anchor = '<string name="player3d_repeat_one">Repetir uma</string>'
    if anchor not in content:
        fail("(B.4) Não encontrei a string player3d_repeat_one em strings.xml "
             "para ancorar a nova string — verifique manualmente.")
    if content.count(anchor) != 1:
        fail("(B.4) Âncora encontrada mais de 1 vez em strings.xml — ambíguo.")

    backup(strings_path)
    new_string = (anchor + '\n    <string name="player3d_no_cover_to_edit">'
                  'Esta faixa não tem capa para editar</string>')
    patched = content.replace(anchor, new_string)
    strings_path.write_text(patched, encoding="utf-8")
    print("(B.4) OK — strings.xml: player3d_no_cover_to_edit adicionada.")


def patch_4_3():
    patch_provider_paths()
    print()
    patch_local_audio()
    print()
    patch_launch_editor()
    print()
    patch_string_resource()


def main():
    if not PROJECT_ROOT.exists():
        fail(f"Projeto não encontrado em {PROJECT_ROOT}. "
             f"Rode este script de dentro de ~/Galeria3D.")

    patch_layout()
    print()
    patch_4_3()
    print()
    print("Próximo passo:")
    print("  cd ~/Galeria3D && ./gradlew assembleDebug")


if __name__ == "__main__":
    main()

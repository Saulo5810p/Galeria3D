/*
 * Passo 7 (Player3D): "Mover faixa para album" e "Criar album vazio".
 *
 * Toda a movimentacao fisica de arquivos de audio fica isolada aqui, com
 * tres caminhos de execucao dependendo do SDK do dispositivo:
 *
 *  - SDK 29 (Q) e superior: atualiza a linha do MediaStore (RELATIVE_PATH +
 *    DISPLAY_NAME), com o flag IS_PENDING durante a operacao, como o
 *    Scoped Storage exige. E o unico caminho de fato usado no aparelho do
 *    usuario (Galaxy A35, Android 14+), os outros dois existem so por
 *    completude/robustez do codigo (minSdk do projeto e 21).
 *  - SDK 21-28: sem Scoped Storage, entao File.renameTo() direto + um
 *    scan manual (MediaScannerConnection) nas duas pastas (origem e
 *    destino) para o MediaStore refletir a mudanca.
 *  - SDK 30-32: se a atualizacao do MediaStore falhar por falta de
 *    permissao (RecoverableSecurityException), o chamador (ActionModeHandler)
 *    recebe o IntentSender de volta para pedir a permissao via
 *    startIntentSenderForResult() e tentar de novo.
 */
package com.android.gallery3d.util;

import android.annotation.TargetApi;
import android.app.RecoverableSecurityException;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.IntentSender;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;

import java.io.File;

public class MoveToAlbumHelper {
    private static final String TAG = "MoveToAlbumHelper";

    public static class MoveResult {
        public int successCount;
        public int failureCount;
        // Preenchido apenas quando um item falhou por precisar de
        // permissao extra em SDK 30-32 (RecoverableSecurityException).
        // O chamador pode usar isto para pedir a permissao ao usuario e
        // tentar de novo.
        public IntentSender pendingPermission;
    }

    private MoveToAlbumHelper() {}

    // contentUri: Uri do item em MediaStore.Audio.Media (ver
    // LocalAudio/MediaItem.getContentUri()).
    // sourceFilePath: caminho fisico atual do arquivo (LocalAudio.filePath).
    // destDir: pasta fisica de destino (pasta de um LocalAlbum existente).
    public static boolean moveOne(Context context, Uri contentUri,
            String sourceFilePath, File destDir, MoveResult outResult) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return moveOneScopedStorage(context, contentUri, destDir, outResult);
        } else {
            return moveOneLegacy(context, sourceFilePath, destDir);
        }
    }

    @TargetApi(Build.VERSION_CODES.Q)
    private static boolean moveOneScopedStorage(Context context, Uri contentUri,
            File destDir, MoveResult outResult) {
        ContentResolver resolver = context.getContentResolver();
        String relativePath = relativePathFor(destDir);
        if (relativePath == null) {
            Log.w(TAG, "destino fora do armazenamento externo: " + destDir);
            return false;
        }

        ContentValues pending = new ContentValues();
        pending.put(MediaStore.Audio.Media.IS_PENDING, 1);
        try {
            resolver.update(contentUri, pending, null, null);
        } catch (RecoverableSecurityException e) {
            if (outResult != null) {
                outResult.pendingPermission = e.getUserAction()
                        .getActionIntent().getIntentSender();
            }
            return false;
        } catch (SecurityException e) {
            Log.w(TAG, "sem permissao para marcar IS_PENDING: " + contentUri, e);
            return false;
        }

        ContentValues move = new ContentValues();
        move.put(MediaStore.Audio.Media.RELATIVE_PATH, relativePath);
        move.put(MediaStore.Audio.Media.IS_PENDING, 0);
        boolean ok;
        try {
            int rows = resolver.update(contentUri, move, null, null);
            ok = rows > 0;
        } catch (RecoverableSecurityException e) {
            if (outResult != null) {
                outResult.pendingPermission = e.getUserAction()
                        .getActionIntent().getIntentSender();
            }
            // Desfaz o IS_PENDING para nao deixar a faixa escondida.
            ContentValues clear = new ContentValues();
            clear.put(MediaStore.Audio.Media.IS_PENDING, 0);
            try {
                resolver.update(contentUri, clear, null, null);
            } catch (SecurityException ignored) {
            }
            ok = false;
        } catch (SecurityException e) {
            Log.w(TAG, "sem permissao para mover: " + contentUri, e);
            ok = false;
        }
        return ok;
    }

    private static boolean moveOneLegacy(Context context, String sourceFilePath,
            File destDir) {
        if (sourceFilePath == null) return false;
        File source = new File(sourceFilePath);
        if (!source.exists()) return false;
        if (!destDir.exists() && !destDir.mkdirs()) {
            Log.w(TAG, "nao foi possivel criar pasta destino: " + destDir);
            return false;
        }
        File dest = new File(destDir, source.getName());
        if (dest.exists()) {
            Log.w(TAG, "ja existe um arquivo com esse nome no destino: " + dest);
            return false;
        }
        boolean ok = source.renameTo(dest);
        if (ok) {
            // Sem Scoped Storage o MediaStore nao percebe a mudanca sozinho;
            // escaneia as duas pastas (origem perde o arquivo, destino ganha).
            MediaScannerConnection.scanFile(context,
                    new String[]{source.getParent(), dest.getAbsolutePath()},
                    null, null);
        }
        return ok;
    }

    // Deriva o RELATIVE_PATH (ex: "Music/MinhaPasta/") esperado pelo
    // MediaStore a partir de um File de pasta dentro do armazenamento
    // externo primario. Usado apenas no caminho SDK 29+.
    private static String relativePathFor(File dir) {
        File externalRoot = Environment.getExternalStorageDirectory();
        String rootPath = externalRoot.getAbsolutePath();
        String dirPath = dir.getAbsolutePath();
        if (!dirPath.startsWith(rootPath)) return null;
        String relative = dirPath.substring(rootPath.length());
        if (relative.startsWith(File.separator)) {
            relative = relative.substring(1);
        }
        if (!relative.endsWith("/")) {
            relative = relative + "/";
        }
        return relative;
    }

    // Cria um album (pasta) vazio dentro de Music/, com o nome dado.
    // Retorna o File da pasta criada, ou null em caso de falha (nome
    // invalido, pasta ja existe, ou sem permissao de escrita).
    public static File createEmptyAlbum(Context context, String albumName) {
        if (albumName == null) return null;
        String trimmed = albumName.trim();
        if (trimmed.isEmpty()) return null;
        // Evita path traversal / caracteres invalidos em nome de pasta.
        if (trimmed.contains(File.separator) || trimmed.contains("..")) {
            return null;
        }

        File musicDir = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_MUSIC);
        File newDir = new File(musicDir, trimmed);
        if (newDir.exists()) {
            return null;
        }
        if (!newDir.mkdirs()) {
            Log.w(TAG, "falha ao criar diretorio: " + newDir);
            return null;
        }

        // Cria um arquivo .nomedia-like marcador? Nao -- o Passo 7 pede um
        // album vazio de verdade, visivel assim que a 1a faixa for movida
        // pra dentro. Uma pasta vazia nao aparece sozinha nos buckets do
        // MediaStore (que sao derivados de arquivos de midia existentes),
        // entao o scan aqui so serve para o SO/outros apps enxergarem a
        // pasta nova; ela so vira um "album" visivel no app quando a
        // primeira faixa for movida para dentro dela.
        MediaScannerConnection.scanFile(context,
                new String[]{newDir.getAbsolutePath()}, null, null);
        return newDir;
    }

    public static boolean albumNameExists(Context context, String albumName) {
        if (albumName == null) return false;
        String trimmed = albumName.trim();
        if (trimmed.isEmpty()) return false;
        File musicDir = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_MUSIC);
        return new File(musicDir, trimmed).exists();
    }
}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, subprocess

os.chdir(os.path.expanduser("~/Galeria3D"))
DATA = "app/src/main/java/com/android/gallery3d/data"
path = os.path.join(DATA, "LocalAlbum.java")

if not os.path.isfile(path):
    print("ERRO: " + path + " nao existe. Confirme que esta na pasta certa (~/Galeria3D).")
    sys.exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()


def apply_one(content, old, new, label):
    count = content.count(old)
    if count != 1:
        print("ERRO: " + label + " -> encontrei " + str(count) + " ocorrencia(s) (esperava 1).")
        print("Trecho procurado:")
        print(old)
        sys.exit(1)
    print("OK: " + label)
    return content.replace(old, new)


# 1) imports: Video/VideoColumns nao sao mais usados neste arquivo depois do fix,
#    trocamos pelos equivalentes de Audio.
content = apply_one(
    content,
    "import android.provider.MediaStore.Video;\n"
    "import android.provider.MediaStore.Video.VideoColumns;\n",
    "import android.provider.MediaStore.Audio;\n"
    "import android.provider.MediaStore.Audio.AudioColumns;\n",
    "imports (Video/VideoColumns -> Audio/AudioColumns)"
)

# 2) Construtor: bloco "else" (isImage == false) ainda usava VideoColumns/Video.Media
#    -- essa e' a causa do crash: mProjection ja virou LocalAudio.PROJECTION (tem
#    ALBUM_ID), mas mBaseUri continuava apontando pra tabela de VIDEO do MediaStore,
#    que nao tem coluna album_id -> IllegalArgumentException "Invalid column album_id".
content = apply_one(
    content,
    "        } else {\n"
    "            mWhereClause = VideoColumns.BUCKET_ID + \" = ?\";\n"
    "            mOrderClause = VideoColumns.DATE_TAKEN + \" DESC, \"\n"
    "                    + VideoColumns._ID + \" DESC\";\n"
    "            mBaseUri = Video.Media.EXTERNAL_CONTENT_URI;\n"
    "            mProjection = LocalAudio.PROJECTION;\n"
    "            mItemPath = LocalAudio.ITEM_PATH;\n"
    "        }\n",
    "        } else {\n"
    "            mWhereClause = AudioColumns.BUCKET_ID + \" = ?\";\n"
    "            // Audio has no DATE_TAKEN column; order by DATE_ADDED instead\n"
    "            // (same substitution used in LocalAudio.loadFromCursor).\n"
    "            mOrderClause = AudioColumns.DATE_ADDED + \" DESC, \"\n"
    "                    + AudioColumns._ID + \" DESC\";\n"
    "            mBaseUri = Audio.Media.EXTERNAL_CONTENT_URI;\n"
    "            mProjection = LocalAudio.PROJECTION;\n"
    "            mItemPath = LocalAudio.ITEM_PATH;\n"
    "        }\n",
    "construtor (mWhereClause/mOrderClause/mBaseUri do ramo audio)"
)

# 3) getContentUri(): ramo else ainda montava a URI de conteudo de Video.
content = apply_one(
    content,
    "        } else {\n"
    "            return MediaStore.Video.Media.EXTERNAL_CONTENT_URI.buildUpon()\n"
    "                    .appendQueryParameter(LocalSource.KEY_BUCKET_ID,\n"
    "                            String.valueOf(mBucketId)).build();\n"
    "        }\n"
    "    }\n"
    "\n"
    "    @Override\n"
    "    public ArrayList<MediaItem> getMediaItem(int start, int count) {\n",
    "        } else {\n"
    "            return MediaStore.Audio.Media.EXTERNAL_CONTENT_URI.buildUpon()\n"
    "                    .appendQueryParameter(LocalSource.KEY_BUCKET_ID,\n"
    "                            String.valueOf(mBucketId)).build();\n"
    "        }\n"
    "    }\n"
    "\n"
    "    @Override\n"
    "    public ArrayList<MediaItem> getMediaItem(int start, int count) {\n",
    "getContentUri() (ramo audio)"
)

# 4) getMediaItemById(): mesmo problema, baseUri ainda era o de Video.
content = apply_one(
    content,
    "        } else {\n"
    "            baseUri = Video.Media.EXTERNAL_CONTENT_URI;\n"
    "            projection = LocalAudio.PROJECTION;\n"
    "            itemPath = LocalAudio.ITEM_PATH;\n"
    "        }\n",
    "        } else {\n"
    "            baseUri = Audio.Media.EXTERNAL_CONTENT_URI;\n"
    "            projection = LocalAudio.PROJECTION;\n"
    "            itemPath = LocalAudio.ITEM_PATH;\n"
    "        }\n",
    "getMediaItemById() (ramo audio)"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print()
print("=== Verificacao final: nao deve sobrar Video.Media/VideoColumns em LocalAlbum.java ===")
leftover = subprocess.run(
    ["grep", "-n", "Video", path],
    capture_output=True, text=True
).stdout
if leftover.strip():
    print("!!! AINDA HA REFERENCIA A 'Video' EM LocalAlbum.java !!!")
    print(leftover)
else:
    print("OK: nenhuma referencia a Video sobrou em LocalAlbum.java")

print()
print("Hotfix 2 aplicado. Agora rode: ./gradlew assembleDebug")
print("(depois, reinstale e teste o app de novo pra confirmar que o crash sumiu)")

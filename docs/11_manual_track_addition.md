# Manual Track Addition

現時点では楽曲追加画面は未実装です。新しい曲を追加する場合は、AP EC2へ音源を配置し、
Oracle DBへ曲マスタと配信用パスを登録します。

## Flow

```text
1. AP EC2へ音源を一時配置する
2. DBへ tracks / artists / track_artists / track_sources を追加する
3. 採番された track_source_id を使って音源を正式配置する
4. hosted_audio_files を有効化する
5. random推薦と音声配信を確認する
```

複数曲をまとめて追加する場合は、TSVを使う方法を推奨します。

## Batch Addition With TSV

新規曲追加用TSVは、既存の `hosted_audio_manifest.tsv` とは列が違います。

```text
title<TAB>artist<TAB>source_path<TAB>duration_sec
```

`duration_sec` は任意です。不要な場合は3列で構いません。

例:

```text
二人スケッチ	Rin'ca	/tmp/new_tracks/2-01 二人スケッチ.m4a
ファイトソング	Eve	/tmp/new_tracks/01 ファイトソング.m4a
Girl meets Love	片霧烈火&鈴湯	/tmp/new_tracks/03 Girl meets Love.mp3
```

手元端末からAP EC2へ音源とTSVを転送します。

```bash
ssh ap 'mkdir -p /tmp/new_tracks'
scp '/path/to/song1.m4a' ap:/tmp/new_tracks/
scp '/path/to/song2.m4a' ap:/tmp/new_tracks/
scp '/path/to/song3.mp3' ap:/tmp/new_tracks/
scp /path/to/new_tracks.tsv ap:/tmp/new_tracks.tsv
```

AP EC2でdry-runします。

```bash
ssh ap
cd /home/ubuntu/music_app
. .venv/bin/activate
set -a
. app/.env
set +a

python3 deploy/python_ec2/register_new_tracks.py \
  --manifest /tmp/new_tracks.tsv \
  --dry-run
```

問題なければ登録します。

```bash
python3 deploy/python_ec2/register_new_tracks.py \
  --manifest /tmp/new_tracks.tsv
```

このスクリプトは次をまとめて実行します。

- `tracks` へ曲を追加
- `artists` へアーティストを追加、既存アーティストは再利用
- `track_artists` へ曲とアーティストの関連を追加
- `track_sources` へ `source_name='local'` の行を追加
- `/data/music-app/audio/<track_source_id>.<ext>` へ音源をコピー
- `hosted_audio_files` へ配信可能状態で登録

同じ `normalized_title` と `normalized_artist` のlocal曲が既にある場合は
二重登録せずskipします。

TSVにヘッダー行を付ける場合:

```text
title	artist	source_path	duration_sec
```

実行時に `--has-header` を付けます。

```bash
python3 deploy/python_ec2/register_new_tracks.py \
  --manifest /tmp/new_tracks.tsv \
  --has-header
```

登録後の確認:

```bash
python3 deploy/python_ec2/check_hosted_audio.py
curl 'http://127.0.0.1:8000/api/recommendations/random?limit=10'
```

追加した `track_source_id` がスクリプト出力に表示されるため、音声配信も確認します。

```bash
curl --range 0-1023 \
  http://127.0.0.1:8000/tracks/<track_source_id>/audio \
  --output /dev/null --verbose
```

`206 Partial Content` が返れば配信成功です。

## 1. Copy Audio To AP

1曲だけ追加する場合は、以下の手順でも実行できます。手元端末からAP EC2へ転送します。

```bash
scp /path/to/new-song.m4a ap:/tmp/new-song.m4a
```

AP EC2で拡張子とサイズを確認します。

```bash
ssh ap
ls -lh /tmp/new-song.m4a
stat -c '%s' /tmp/new-song.m4a
```

## 2. Insert DB Rows

AP EC2で実行します。`title`、`artist`、`ext` を追加する曲に合わせて変更します。

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
cd app
set -a
. ./.env
set +a

python3 - <<'PY'
import os
from pathlib import Path

import oracledb

title = "曲名を入れる"
artist = "アーティスト名を入れる"
ext = ".m4a"

normalized_title = title.strip().lower()
normalized_artist = artist.strip().lower()

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=os.environ["ORACLE_DSN"],
) as conn:
    with conn.cursor() as cur:
        track_id_var = cur.var(oracledb.NUMBER)
        artist_id_var = cur.var(oracledb.NUMBER)
        source_id_var = cur.var(oracledb.NUMBER)

        cur.execute(
            """
            INSERT INTO tracks (title, normalized_title)
            VALUES (:title, :normalized_title)
            RETURNING track_id INTO :track_id
            """,
            title=title,
            normalized_title=normalized_title,
            track_id=track_id_var,
        )
        track_id = int(track_id_var.getvalue()[0])

        cur.execute(
            """
            MERGE INTO artists target
            USING (
                SELECT :name AS name, :normalized_name AS normalized_name
                FROM dual
            ) source
            ON (target.normalized_name = source.normalized_name)
            WHEN NOT MATCHED THEN INSERT (name, normalized_name)
            VALUES (source.name, source.normalized_name)
            """,
            name=artist,
            normalized_name=normalized_artist,
        )

        cur.execute(
            """
            SELECT artist_id
            FROM artists
            WHERE normalized_name = :normalized_name
            """,
            normalized_name=normalized_artist,
        )
        artist_id = int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO track_artists (track_id, artist_id)
            VALUES (:track_id, :artist_id)
            """,
            track_id=track_id,
            artist_id=artist_id,
        )

        cur.execute(
            """
            INSERT INTO track_sources (
                track_id,
                source_name,
                raw_title,
                raw_artist,
                normalized_title,
                normalized_artist,
                availability_status
            ) VALUES (
                :track_id,
                'local',
                :raw_title,
                :raw_artist,
                :normalized_title,
                :normalized_artist,
                'available'
            )
            RETURNING track_source_id INTO :track_source_id
            """,
            track_id=track_id,
            raw_title=title,
            raw_artist=artist,
            normalized_title=normalized_title,
            normalized_artist=normalized_artist,
            track_source_id=source_id_var,
        )
        track_source_id = int(source_id_var.getvalue()[0])

        hosted_path = Path("/data/music-app/audio") / f"{track_source_id}{ext}"

        cur.execute(
            """
            INSERT INTO hosted_audio_files (
                track_source_id,
                track_id,
                file_path_linux,
                is_available
            ) VALUES (
                :track_source_id,
                :track_id,
                :file_path_linux,
                0
            )
            """,
            track_source_id=track_source_id,
            track_id=track_id,
            file_path_linux=str(hosted_path),
        )

    conn.commit()

print(f"track_id={track_id}")
print(f"track_source_id={track_source_id}")
print(f"hosted_path={hosted_path}")
PY
```

この時点では `is_available=0` のため、まだ推薦候補には出ません。

## 3. Move Audio To Final Path

直前の出力に表示された `hosted_path` へ音源を移動します。

```bash
mv /tmp/new-song.m4a /data/music-app/audio/<track_source_id>.m4a
ls -lh /data/music-app/audio/<track_source_id>.m4a
```

## 4. Enable Hosted Audio

ファイルサイズをDBへ反映し、配信可能にします。

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
cd app
set -a
. ./.env
set +a

TRACK_SOURCE_ID=<track_source_id>
FILE_SIZE=$(stat -c '%s' /data/music-app/audio/${TRACK_SOURCE_ID}.m4a)

python3 - <<PY
import os
import oracledb

track_source_id = int("${TRACK_SOURCE_ID}")
file_size = int("${FILE_SIZE}")

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=os.environ["ORACLE_DSN"],
) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE hosted_audio_files
            SET file_size_bytes = :file_size,
                is_available = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE track_source_id = :track_source_id
            """,
            file_size=file_size,
            track_source_id=track_source_id,
        )
    conn.commit()
PY
```

## 5. Check

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
set -a
. app/.env
set +a

python3 deploy/python_ec2/check_hosted_audio.py
curl 'http://127.0.0.1:8000/api/recommendations/random?limit=10'
curl --range 0-1023 \
  http://127.0.0.1:8000/tracks/<track_source_id>/audio \
  --output /dev/null --verbose
```

`206 Partial Content` が返れば音声配信は成功です。

## Notes

- 日本語や `&` を含む曲名、アーティスト名でも、上記Python手順ならSQL*Plusの
  置換変数問題を避けられます。
- 同じ曲を二重登録しないよう、追加前に `tracks` と `track_sources` を検索します。
- 楽曲追加画面は未実装です。恒常運用にする場合は、バックログの
  `楽曲追加機能` として画面/API化します。

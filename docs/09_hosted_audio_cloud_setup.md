# Hosted Audio Cloud Setup

この手順は、zephyで確認済みの配信方式をPython EC2へ再現します。

```text
Browser
  -> http://<python-ec2>/music/
  -> Python EC2 Apache
  -> FastAPI
  -> /data/music-app/audio/<track_source_id>.<ext>
```

Python EC2上の音源パスは `hosted_audio_files` に登録します。

## 1. Security Group

Python EC2:

- inbound TCP 80: 利用するIP範囲のみ
- inbound SSH管理ポート: 管理元IPのみ
- outbound TCP 1521: Oracle EC2のprivate IP
- outbound TCP 443: `0.0.0.0/0`

Ubuntuで `ufw` がactiveの場合:

```bash
sudo ufw allow 80/tcp
sudo ufw status
```

現状の配信APIにはログイン機能がありません。  
インターネット全体へTCP 80を公開しないでください。

## 2. DB Table

Oracle EC2のDBへ `sql/003_hosted_audio_files.sql` を適用します。

```bash
sqlplus music_app_v2/<password>@//<oracle-ec2-private-ip>:1521/FREEPDB1 \
  @sql/003_hosted_audio_files.sql
```

既にテーブルがあるDB dumpを復元した場合は、再適用しません。

## 3. Audio Directory

Python EC2で音源配置先を作ります。

```bash
sudo mkdir -p /data/music-app/audio
sudo chown -R ubuntu:ubuntu /data/music-app
```

`app/.env` に配置先を設定します。

```text
HOSTED_AUDIO_ROOT=/data/music-app/audio
```

## 4. Manifest

クラウド移行前のzephy DBから、次の3列を持つUTF-8 TSVを出力します。

```text
track_source_id<TAB>track_id<TAB>original_path
```

`original_path` は転送元でのみ使用します。zephyから転送する場合は、
zephy上の `/home/codex/work/oracle/hosted_audio/...` です。このパスをOracle EC2へ
dumpで引き継ぎません。

zephy DBからTSVを出力するSQL*Plusコマンド:

```bash
sqlplus -s music_app_v2/<password>@//localhost:1521/FREEPDB1 <<'SQL'
SET HEADING OFF
SET FEEDBACK OFF
SET PAGESIZE 0
SET LINESIZE 4000
SET TRIMSPOOL ON
SET TAB OFF
SPOOL /tmp/hosted_audio_manifest_db.tsv
SELECT
    track_source_id || CHR(9) ||
    track_id || CHR(9) ||
    file_path_linux
FROM hosted_audio_files
WHERE is_available = 1
ORDER BY track_source_id;
SPOOL OFF
EXIT
SQL
```

転送元端末へTSVを置き、実ファイルの存在確認と容量取得を行います。

```bash
python3 deploy/source/build_hosted_audio_manifest.py
```

正常終了後、次の4列を持つ転送用TSVが生成されます。

```text
track_source_id<TAB>track_id<TAB>original_path<TAB>file_size_bytes
```

例:

```text
1464	1366	/mnt/d/music/example.m4a	7558349
```

TSVにはローカル音源パスが含まれます。Gitへ登録しないでください。

## 5. Transfer

転送元端末で実行します。

```bash
while IFS=$'\t' read -r source_id track_id source_path bytes; do
  ext="${source_path##*.}"
  rsync -av --progress \
    "$source_path" \
    "ubuntu@<python-ec2>:/data/music-app/audio/${source_id}.${ext}"
done < /tmp/hosted_audio_manifest.tsv
```

途中で停止した場合は、同じコマンドを再実行できます。

manifestもPython EC2へ転送します。

```bash
scp /tmp/hosted_audio_manifest.tsv \
  ubuntu@<python-ec2>:/tmp/hosted_audio_manifest.tsv
```

## 6. Register

Python EC2で実行します。

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
set -a
. app/.env
set +a
python3 deploy/python_ec2/register_hosted_audio.py
```

期待値:

```text
processed=<transferred files> missing=0 available=<registered files>
```

再実行しても、既存行は `MERGE` で更新されます。

登録時に `file_path_linux` はPython EC2の配置先へ置き換わります。

```text
/data/music-app/audio/<track_source_id>.<ext>
```

## 7. Check

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
set -a
. app/.env
set +a
python3 deploy/python_ec2/check_hosted_audio.py
```

API確認:

```bash
curl http://127.0.0.1:8000/api/recommendations/random?limit=10
curl --range 0-1023 \
  http://127.0.0.1:8000/tracks/<track_source_id>/audio \
  --output /dev/null --verbose
```

ブラウザ:

```text
http://<python-ec2-public-ip>/music/
```

## 8. Hosted AI Recommendation

画面の `Run Recommendation` は、`hosted_audio_files.is_available = 1`
の曲だけを候補としてOpenAI APIへ渡します。

次を設定してから使用します。

```text
OPENAI_API_KEY=<your-key>
```

接続確認:

```bash
curl -sS -o /dev/null -w 'http_code=%{http_code}\n' \
  --max-time 8 https://api.openai.com/v1/models
```

APIキーなしのcurlでは `401` が正常です。タイムアウトする場合は、AP EC2の
Outbound TCP 443、Network ACL、ルートテーブルを確認します。

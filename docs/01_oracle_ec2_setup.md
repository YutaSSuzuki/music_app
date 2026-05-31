# Oracle EC2 Setup

Oracle EC2には、コンテナではなくOracle AI Database 26ai FreeをRPMで直接
インストールします。

## 1. EC2

推奨:

- AMI: Oracle Linux 9 x86-64
- Instance: `t3.medium` 以上
- EBS: gp3 30GB以上
- Security Group:
  - inbound TCP 22: 管理元IPのみ
  - inbound TCP 1521: Python EC2のSecurity Groupのみ

Oracle AI Database FreeのRPMインストール対象はOracle Linux 8/9または
RHEL 8/9です。Oracle EC2ではAmazon LinuxやUbuntuを選択しません。

Free版の上限:

- CPU: 2
- RAM: 2GB
- ユーザーデータ: 12GB

RPMインストールでは `/opt` 配下に約9GBの空き容量も必要です。

## 2. RPM Download

Oracle公式ページから、EL9 x86-64向けのpreinstall RPMとDatabase Free RPMを
ダウンロードします。RHEL 10ではEL8向けpreinstall RPMの依存関係を解決できなかった
ため、RHEL 9またはOracle Linux 9を使用します。

```text
https://www.oracle.com/database/free/get-started/
```

取得した2つのRPMをOracle EC2の `/tmp` へ転送します。

例:

```bash
scp oracle-ai-database-preinstall-26ai-*.el9.x86_64.rpm \
  oracle-ai-database-free-26ai-*.el9.x86_64.rpm \
  ec2-user@<oracle-ec2-public-ip>:/tmp/
```

## 3. Install

Oracle EC2へSSH接続します。

```bash
ssh ec2-user@<oracle-ec2-public-ip>
```

**RHEL Linux 9**で実行します。

```bash
sudo dnf update -y
sudo dnf install -y /tmp/oracle-ai-database-preinstall-26ai-*.el9.x86_64.rpm
sudo dnf install -y /tmp/oracle-ai-database-free-26ai-*.el9.x86_64.rpm
```

preinstall RPMは、`oracle` ユーザー、必要なグループ、カーネル設定などを準備します。
同じ処理は、RPMのファイル名を引数にして実行できます。

```bash
bash deploy/oracle_ec2/bootstrap_oracle_linux_9.sh \
  /tmp/oracle-ai-database-preinstall-26ai-*.el9.x86_64.rpm \
  /tmp/oracle-ai-database-free-26ai-*.el9.x86_64.rpm
```

## 4. Configure Database

DBを作成します。

```bash
sudo /etc/init.d/oracle-free-26ai configure
```

プロンプトで管理ユーザー用パスワードを設定します。

この処理で以下が作成されます。

```text
CDB:      FREE
PDB:      FREEPDB1
Listener: TCP 1521
```

状態を確認します。

```bash
sudo /etc/init.d/oracle-free-26ai status
sudo ss -ltnp | grep 1521
```

## 5. Oracle Environment

Oracle EC2でSQL*PlusやData Pumpを使う場合は、`oracle` ユーザーへ切り替えます。

```bash
sudo su - oracle
export ORACLE_SID=FREE
export ORAENV_ASK=NO
. /opt/oracle/product/26ai/dbhomeFree/bin/oraenv
export NLS_LANG=.AL32UTF8
```

PDBへ接続します。

```bash
sqlplus system@//localhost:1521/FREEPDB1
```

`NLS_LANG=.AL32UTF8` は、UTF-8で保存したSQLファイル内の日本語を文字化けさせない
ために必要です。毎回入力しないよう、`oracle` ユーザーの `~/.bash_profile` に
追加します。

```bash
cat >> ~/.bash_profile <<'EOF'
export ORACLE_SID=FREE
export ORAENV_ASK=NO
. /opt/oracle/product/26ai/dbhomeFree/bin/oraenv
export NLS_LANG=.AL32UTF8
EOF

. ~/.bash_profile
```

## 6. Application User

新規DBへスキーマを作る場合は、PDBへ管理ユーザーで接続して実行します。

```sql
CREATE USER music_app_v2 IDENTIFIED BY "<application-db-password>";
GRANT CONNECT, RESOURCE TO music_app_v2;
ALTER USER music_app_v2 QUOTA UNLIMITED ON USERS;
```

DDLを適用します。

`<repository-root>` は `sql/` ディレクトリを含むGit clone先です。Oracle EC2へ
SQLファイルだけ転送した場合は、`@/home/oracle/002_revised_schema.sql` のように
絶対パスを指定します。

```bash
cd <repository-root>
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/002_revised_schema.sql
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/003_hosted_audio_files.sql
```

zephyのdumpを復元する場合は、dumpに含まれるテーブルを再作成しません。

DDL適用結果を確認します。

```bash
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1
```

```sql
SET LINESIZE 200
SET PAGESIZE 100

SELECT table_name
FROM user_tables
ORDER BY table_name;

SELECT column_id, column_name, data_type, nullable
FROM user_tab_columns
WHERE table_name = 'HOSTED_AUDIO_FILES'
ORDER BY column_id;

SELECT constraint_name, constraint_type, status
FROM user_constraints
WHERE table_name = 'HOSTED_AUDIO_FILES'
ORDER BY constraint_name;

SELECT index_name, status
FROM user_indexes
WHERE table_name = 'HOSTED_AUDIO_FILES'
ORDER BY index_name;

EXIT
```

最低限、次のテーブルが表示されることを確認します。

```text
ARTISTS
HOSTED_AUDIO_FILES
PLAY_EVENTS
RECOMMENDATION_ITEMS
RECOMMENDATION_RUNS
TRACKS
TRACK_ARTISTS
TRACK_FEATURES
TRACK_SOURCES
TRACK_TAGS
```

## 7. Three-Track Smoke Test

全件dumpを投入する前に、次の3曲のみでDB接続と音声配信を確認します。

| file | title | artist | bytes |
| --- | --- | --- | ---: |
| `sample-001.m4a` | 二人スケッチ | Rin'ca | 4475110 |
| `sample-002.m4a` | ファイトソング | Eve | 7558349 |
| `sample-003.mp3` | Girl meets Love | 片霧烈火&鈴湯 | 4057429 |

音源はPython EC2へ置きます。Oracle EC2やzephy固有のパスはDBへ登録しません。

```text
/data/music-app/audio/sample-001.m4a
/data/music-app/audio/sample-002.m4a
/data/music-app/audio/sample-003.mp3
```

Python EC2で配置先を作ります。

```bash
sudo mkdir -p /data/music-app/audio
sudo chown -R ubuntu:ubuntu /data/music-app
```

音源を持つ端末から3曲を転送します。WSLから実行する例:

```bash
scp \
  '/mnt/d/yu28s/Music/music_centor/Compilations/あざらしそふと コンプリートアルバム2[DISC-2]/2-01 二人スケッチ.m4a' \
  ubuntu@<python-ec2-public-ip>:/data/music-app/audio/sample-001.m4a

scp \
  '/mnt/d/yu28s/Music/Eve/ファイトソング - Single/01 ファイトソング.m4a' \
  ubuntu@<python-ec2-public-ip>:/data/music-app/audio/sample-002.m4a

scp \
  '/mnt/d/yu28s/Music/music_centor/Compilations/EGG-Extra Games Garden- anthology 2015/03 Girl meets Love.mp3' \
  ubuntu@<python-ec2-public-ip>:/data/music-app/audio/sample-003.mp3
```

Oracle EC2でサンプル行を登録します。

```bash
cd <repository-root>
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/004_seed_cloud_smoke_test.sql
```

SQLファイルでは `SET DEFINE OFF` を指定しています。これは、
`片霧烈火&鈴湯` に含まれる `&` をSQL*Plusの置換変数として解釈させないためです。
また、実行前に `echo "$NLS_LANG"` が `.AL32UTF8` であることを確認します。

既に日本語が `???` になったサンプル行を登録済みの場合は、一度削除してから
再登録します。

```bash
echo "$NLS_LANG"
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/005_delete_cloud_smoke_test.sql
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/004_seed_cloud_smoke_test.sql
```

日本語を含むSQLファイルを単発実行する場合は、次のラッパーも使用できます。

```bash
deploy/oracle_ec2/sqlplus_utf8.sh \
  music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/004_seed_cloud_smoke_test.sql
```

登録結果:

```bash
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1
```

```sql
SELECT
    ts.source_track_id,
    t.title,
    haf.file_path_linux,
    haf.file_size_bytes
FROM track_sources ts
JOIN tracks t ON t.track_id = ts.track_id
JOIN hosted_audio_files haf ON haf.track_source_id = ts.track_source_id
WHERE ts.source_track_id LIKE 'cloud-smoke-test-%'
ORDER BY ts.source_track_id;

EXIT
```

Python EC2でファイル実体とAPIを確認します。

```bash
ls -lh /data/music-app/audio/sample-*
curl http://127.0.0.1:8000/api/recommendations/random?limit=3
```

レスポンスに含まれる `audio_url` を使って部分配信を確認します。

```bash
curl --range 0-1023 \
  http://127.0.0.1:8000/tracks/<track_source_id>/audio \
  --output /dev/null --verbose
```

HTTPステータス `206 Partial Content` になれば部分配信に成功しています。

ブラウザからも再生を確認します。

```text
http://<python-ec2-public-ip>/music/
```

全件移行前にサンプル行を削除します。

```bash
cd <repository-root>
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/005_delete_cloud_smoke_test.sql
```

`REMAINING_CLOUD_SMOKE_TEST_ROWS` が `0` であることを確認します。

Python EC2からサンプル音源も削除します。

```bash
rm /data/music-app/audio/sample-001.m4a \
   /data/music-app/audio/sample-002.m4a \
   /data/music-app/audio/sample-003.mp3
```

## 8. DB Data Migration

zephyでData Pump dumpを作成し、Oracle EC2へprivateな経路で転送します。
dumpにはYouTube履歴やローカル音源パスが含まれるため、GitHubへ登録しません。

クラウド版では旧 `LOCAL_AUDIO_FILES` テーブルを使用しません。また、
`HOSTED_AUDIO_FILES` にはzephy固有のパスが入っているため、dumpから除外します。
Python EC2へ音源を転送した後に登録スクリプトで再生成します。

zephyではOracleをpodmanコンテナ `oracle-free` で動かしています。使用中の
`container-registry.oracle.com/database/free:latest-lite` イメージには `expdp`
コマンドが含まれません。SQL*Plusから `DBMS_DATAPUMP` を呼び出します。

ローカルPCからSQLファイルをzephyへ転送します。

```bash
scp sql/006_export_cloud_dump_with_dbms_datapump.sql \
  zephy-codex:/tmp/
scp sql/007_prepare_cloud_dump_export.sql \
  zephy-codex:/tmp/
```

zephyで実行します。

```bash
ssh zephy-codex
podman cp /tmp/006_export_cloud_dump_with_dbms_datapump.sql \
  oracle-free:/tmp/
podman cp /tmp/007_prepare_cloud_dump_export.sql \
  oracle-free:/tmp/
podman exec -it oracle-free bash
```

SYSDBAでアプリユーザーへData Pumpディレクトリ権限を付与し、前回失敗した
Data Pumpジョブがあれば削除します。

```bash
/opt/oracle/product/26ai/dbhomeFree/bin/sqlplus / as sysdba
```

```sql
@/tmp/007_prepare_cloud_dump_export.sql
EXIT
```

コンテナ内で実行します。

```bash
# 同名dumpが残っている場合は、先に別名へ退避または削除します。
/opt/oracle/product/26ai/dbhomeFree/bin/sqlplus \
  music_app_v2/<zephy-db-password>@//localhost:1521/FREEPDB1 \
  @/tmp/006_export_cloud_dump_with_dbms_datapump.sql
```

成功時は次のように表示されます。

```text
Data Pump job state: COMPLETED
```

dumpの出力先を確認します。

```bash
/opt/oracle/product/26ai/dbhomeFree/bin/sqlplus / as sysdba
```

```sql
ALTER SESSION SET CONTAINER = FREEPDB1;
SELECT directory_path
FROM dba_directories
WHERE directory_name = 'DATA_PUMP_DIR';
EXIT
```

コンテナから抜け、表示されたパスを使ってdumpをzephyへ取り出します。

```bash
exit
podman cp \
  oracle-free:<表示されたDATA_PUMP_DIR>/music_app_v2_cloud.dmp \
  /tmp/music_app_v2_cloud.dmp
ls -lh /tmp/music_app_v2_cloud.dmp
sha256sum /tmp/music_app_v2_cloud.dmp
exit
```

ローカルPCを中継してOracle EC2へ転送します。dumpはGitHubへ登録しません。

```bash
scp zephy-codex:/tmp/music_app_v2_cloud.dmp /tmp/
sha256sum /tmp/music_app_v2_cloud.dmp
scp /tmp/music_app_v2_cloud.dmp oracle:/tmp/
```

Oracle EC2でData Pumpディレクトリを確認します。

```bash
sudo su - oracle
export ORACLE_SID=FREE
export ORAENV_ASK=NO
. /opt/oracle/product/26ai/dbhomeFree/bin/oraenv
export NLS_LANG=.AL32UTF8

sqlplus / as sysdba
```

```sql
ALTER SESSION SET CONTAINER = FREEPDB1;
SELECT directory_name, directory_path
FROM dba_directories
WHERE directory_name = 'DATA_PUMP_DIR';
EXIT
```

dumpを、表示された `DATA_PUMP_DIR` のOSパスへ配置し、`oracle` ユーザーから
読めるようにします。

```bash
exit
sudo cp /tmp/music_app_v2_cloud.dmp <表示されたDATA_PUMP_DIR>/
sudo chown oracle:oinstall <表示されたDATA_PUMP_DIR>/music_app_v2_cloud.dmp
sudo su - oracle
```

初回のみ、Oracle EC2側でもアプリユーザーへData Pumpディレクトリ権限を付与します。

```bash
sqlplus / as sysdba
```

```sql
ALTER SESSION SET CONTAINER = FREEPDB1;
GRANT READ, WRITE ON DIRECTORY DATA_PUMP_DIR TO music_app_v2;
EXIT
```

既存DDLには外部キーがあります。`DATA_ONLY` importではテーブル処理順序を保証
できないため、import前にクラウドDBのデータを初期化して外部キーを一時無効化します。
これは新規Oracle EC2に対してのみ実行します。

```bash
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/008_reset_cloud_import_target.sql
```

全テーブルが `0` 件になったことを確認します。

import例:

```bash
impdp music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  schemas=music_app_v2 \
  directory=DATA_PUMP_DIR \
  dumpfile=music_app_v2_cloud.dmp \
  logfile=music_app_v2_imp.log \
  content=DATA_ONLY \
  table_exists_action=APPEND
```

import後に外部キーを再有効化し、整合性を検証します。

```bash
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/009_enable_cloud_import_constraints.sql
```

すべての外部キーが `ENABLED` かつ `VALIDATED` であることを確認します。

先にDDLを適用済みのため、`content=DATA_ONLY` でデータのみを投入します。
サンプルデータが残っている状態では実行しません。移行方法によっては、import前に
ユーザー作成や `REMAP_SCHEMA` が必要です。

import後に件数を確認します。

この時点の `HOSTED_AUDIO_FILES` は `0` 件が正常です。全音源をPython EC2へ
転送した後、`docs/09_hosted_audio_cloud_setup.md` の登録スクリプトで再生成します。

```bash
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1
```

```sql
SET LINESIZE 200
SET PAGESIZE 100

SELECT 'TRACKS' AS table_name, COUNT(*) AS row_count FROM tracks
UNION ALL
SELECT 'TRACK_SOURCES', COUNT(*) FROM track_sources
UNION ALL
SELECT 'HOSTED_AUDIO_FILES', COUNT(*) FROM hosted_audio_files
UNION ALL
SELECT 'PLAY_EVENTS', COUNT(*) FROM play_events
UNION ALL
SELECT 'RECOMMENDATION_RUNS', COUNT(*) FROM recommendation_runs
UNION ALL
SELECT 'RECOMMENDATION_ITEMS', COUNT(*) FROM recommendation_items;

EXIT
```

## 9. Python EC2 Connection

Python EC2の `app/.env` にOracle EC2のprivate IPを設定します。

```text
ORACLE_USER=music_app_v2
ORACLE_PASSWORD=<application-db-password>
ORACLE_DSN=<oracle-ec2-private-ip>:1521/FREEPDB1
```

Python EC2から確認します。

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
cd app
set -a
. ./.env
set +a
python3 03_matching_recommendation/phase1_cli.py health
```

## References

- Oracle AI Database Free: `https://www.oracle.com/database/free/get-started/`
- Oracle AI Database Free Installation Guide:
  `https://docs.oracle.com/en/database/oracle/oracle-database/26/xeinl/installing-oracle-database-free.html`

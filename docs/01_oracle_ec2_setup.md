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

Oracle公式ページから、Oracle Linux 9 x86-64向けの最新RPMをダウンロードします。

```text
https://www.oracle.com/database/free/get-started/
```

取得したRPMをOracle EC2の `/tmp` へ転送します。

例:

```bash
scp oracle-ai-database-free-26ai-*.el9.x86_64.rpm \
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
sudo dnf install -y oracle-database-preinstall* #Linux9の場合プリインストールが必要
sudo dnf install -y /tmp/oracle-ai-database-free-26ai-*.el9.x86_64.rpm #Oracle本体のインストール
```

preinstall RPMは、`oracle` ユーザー、必要なグループ、カーネル設定などを準備します。

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
```

PDBへ接続します。

```bash
sqlplus system@//localhost:1521/FREEPDB1
```

## 6. Application User

新規DBへスキーマを作る場合は、PDBへ管理ユーザーで接続して実行します。

```sql
CREATE USER music_app_v2 IDENTIFIED BY "<application-db-password>";
GRANT CONNECT, RESOURCE TO music_app_v2;
ALTER USER music_app_v2 QUOTA UNLIMITED ON USERS;
```

DDLを適用します。

```bash
cd /opt/music-app/oracle/cloud_lift
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/002_revised_schema.sql
sqlplus music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  @sql/003_hosted_audio_files.sql
```

zephyのdumpを復元する場合は、dumpに含まれるテーブルを再作成しません。

## 7. DB Data Migration

zephyでData Pump dumpを作成し、Oracle EC2へprivateな経路で転送します。
dumpにはYouTube履歴やローカル音源パスが含まれるため、GitHubへ登録しません。

クラウド版では旧 `LOCAL_AUDIO_FILES` テーブルを使用しません。zephyからexportする際に
除外します。

```bash
expdp music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  schemas=music_app_v2 \
  directory=DATA_PUMP_DIR \
  dumpfile=music_app_v2_cloud.dmp \
  logfile=music_app_v2_cloud_exp.log \
  exclude=TABLE:\"IN \(\'LOCAL_AUDIO_FILES\'\)\"
```

Oracle EC2でData Pumpディレクトリを確認します。

```bash
sudo su - oracle
export ORACLE_SID=FREE
export ORAENV_ASK=NO
. /opt/oracle/product/26ai/dbhomeFree/bin/oraenv

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

import例:

```bash
impdp music_app_v2/<application-db-password>@//localhost:1521/FREEPDB1 \
  schemas=music_app_v2 \
  directory=DATA_PUMP_DIR \
  dumpfile=music_app_v2_cloud.dmp \
  logfile=music_app_v2_imp.log
```

移行方法によっては、import前にユーザー作成や `REMAP_SCHEMA` が必要です。

## 8. Python EC2 Connection

Python EC2の `app/.env` にOracle EC2のprivate IPを設定します。

```text
ORACLE_USER=music_app_v2
ORACLE_PASSWORD=<application-db-password>
ORACLE_DSN=<oracle-ec2-private-ip>:1521/FREEPDB1
```

Python EC2から確認します。

```bash
cd /opt/music-app/oracle/cloud_lift/app
. .venv/bin/activate
set -a
. ./.env
set +a
python3 03_matching_recommendation/phase1_cli.py health
```

## References

- Oracle AI Database Free: `https://www.oracle.com/database/free/get-started/`
- Oracle AI Database Free Installation Guide:
  `https://docs.oracle.com/en/database/oracle/oracle-database/26/xeinl/installing-oracle-database-free.html`

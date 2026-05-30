# Oracle EC2 Setup

## 推奨インスタンス

最初は以下を推奨します。

- Instance: `t3.large` 以上
- OS: Amazon Linux 2023 or Ubuntu 22.04
- EBS: gp3 100GB以上
- Security Group:
  - SSH 22: 自分のIPのみ
  - Oracle 1521: Python EC2のSecurity Groupのみ

## Docker起動

`deploy/oracle_ec2/docker-compose.oracle.yml` と `deploy/oracle_ec2/oracle.env.example` をEC2へ配置します。

```bash
mkdir -p ~/music-app-oracle
cd ~/music-app-oracle
cp oracle.env.example oracle.env
vi oracle.env
docker compose -f docker-compose.oracle.yml up -d
docker logs -f oracle-free
```

## Schema作成

Oracleへ接続し、`music_app_v2` ユーザーを作成します。

例:

```sql
CREATE USER music_app_v2 IDENTIFIED BY "CHANGE_ME";
GRANT CONNECT, RESOURCE TO music_app_v2;
ALTER USER music_app_v2 QUOTA UNLIMITED ON USERS;
```

その後、Python EC2またはOracle EC2から以下を適用します。

```bash
sqlplus music_app_v2/CHANGE_ME@//localhost:1521/FREEPDB1 @sql/002_revised_schema.sql
```

## DBデータ移行

本番データ移行は別途Data Pumpを使うのが安全です。

候補:

```bash
expdp music_app_v2/CHANGE_ME@FREEPDB1 schemas=music_app_v2 directory=DATA_PUMP_DIR dumpfile=music_app_v2.dmp logfile=music_app_v2_exp.log
impdp music_app_v2/CHANGE_ME@FREEPDB1 schemas=music_app_v2 directory=DATA_PUMP_DIR dumpfile=music_app_v2.dmp logfile=music_app_v2_imp.log
```

注意:

- dumpにはYouTube履歴やローカル音源パスが含まれる
- GitHubには置かない
- S3へ置く場合もprivate bucketにする


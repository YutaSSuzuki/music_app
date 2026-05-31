# Operation Commands

## Python EC2

FastAPI status:

```bash
systemctl status music-app-web.service
journalctl -u music-app-web.service -f
```

API確認:

```bash
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/recommendations/random?limit=10
```

Apache確認:

```bash
curl http://127.0.0.1/music/api/status
```

再起動:

```bash
sudo systemctl restart music-app-web.service
sudo systemctl reload apache2
```

Amazon LinuxでApacheがhttpdの場合:

```bash
sudo systemctl reload httpd
```

Hosted audio確認:

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
set -a
. app/.env
set +a
python3 deploy/python_ec2/check_hosted_audio.py
```

## Oracle EC2

```bash
sudo /etc/init.d/oracle-free-26ai status
sudo ss -ltnp | grep 1521
```

DBリスナー確認:

```bash
sudo su - oracle
export ORACLE_SID=FREE
export ORAENV_ASK=NO
. /opt/oracle/product/26ai/dbhomeFree/bin/oraenv
export NLS_LANG=.AL32UTF8

sqlplus system@//localhost:1521/FREEPDB1
```

DB件数確認はPython EC2から実行:

```bash
cd /home/ubuntu/music_app
. .venv/bin/activate
cd app
set -a
. ./.env
set +a
python3 03_matching_recommendation/phase1_cli.py health
```

AP EC2からOracle EC2へのTCP疎通確認:

```bash
nc -vz -w 3 <oracle-ec2-private-ip> 1521
```

## OpenAI API Connection Check

AI推薦を使用する場合、AP EC2からインターネット向けTCP 443のOutbound通信が必要です。
OpenAI APIの接続先IPは固定値として扱わないため、AP EC2のSecurity Groupでは次を
許可します。

```text
Outbound
Protocol:    TCP
Port:        443
Destination: 0.0.0.0/0
```

AP EC2で名前解決とHTTPS疎通を確認します。

```bash
getent ahostsv4 api.openai.com
curl -sS -o /dev/null -w 'http_code=%{http_code}\n' \
  --max-time 8 https://api.openai.com/v1/models
```

APIキーを付けていない状態では、`401` が正常です。`401` はOpenAI APIまで到達した
ことを示します。`curl: (28) Connection timed out` の場合は、AP EC2のSecurity
Group、サブネットのNetwork ACL、ルートテーブルの順に確認します。

FastAPIで発生したOpenAI APIエラーはsystemdログで確認します。

```bash
sudo journalctl -u music-app-web.service --no-pager -n 120
```

## Troubleshooting

| symptom | likely cause | check |
| --- | --- | --- |
| `/music/` が `503 Service Unavailable` | FastAPIがTCP 8000で待受していない | `sudo ss -ltnp \| grep ':8000 '` |
| `music-app-web.service` が起動しない | Ubuntu上のユーザー名または配置先とservice定義が不一致 | `systemctl cat music-app-web.service` |
| APからOracle接続がtimeout | TCP 1521のSecurity GroupまたはNetwork ACL | `nc -vz -w 3 <oracle-private-ip> 1521` |
| SQL*Plusで日本語が `???` | `NLS_LANG` が未設定 | `echo "$NLS_LANG"` |
| SQL*Plusが `Enter value for ...` を表示 | SQL内の `&` を置換変数として解釈 | SQLファイル先頭の `SET DEFINE OFF` |
| AI推薦がtimeout | AP EC2からインターネット向けTCP 443が未許可 | `curl --max-time 8 https://api.openai.com/v1/models` |

SQL*Plusは `sudo su - oracle` のように `-` 付きでログインシェルを開始します。
`sudo su oracle` では `~/.bash_profile` が読み込まれません。

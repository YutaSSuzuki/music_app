# Ubuntu AP EC2 Setup

## 推奨インスタンス

- Instance: `t3.small` or `t3.medium`
- OS: Ubuntu
- EBS: gp3 20GB以上
- Security Group:
  - HTTP 80: 自分のIPまたは利用範囲
  - SSH管理ポート: 自分のIPのみ
  - outbound TCP 1521: Oracle EC2のprivate IP
  - outbound TCP 443: `0.0.0.0/0`

Oracle EC2側のSecurity Groupでも、AP EC2からのinbound TCP 1521を許可します。
可能であればAP EC2のSecurity GroupをSourceに指定します。

## OS Setup

```bash
cd /home/ubuntu/music_app
bash deploy/python_ec2/bootstrap_ubuntu.sh
```

Git clone前に実行する場合:

```bash
sudo apt update
sudo apt install -y apache2 curl git netcat-openbsd python3-venv ufw
sudo a2enmod proxy proxy_http headers
sudo systemctl enable --now apache2
sudo ufw allow 80/tcp
sudo mkdir -p /data/music-app/audio
sudo chown -R ubuntu:ubuntu /data/music-app
```

`ufw` がactiveの場合は、Security Groupだけでなく `sudo ufw allow 80/tcp` も必要です。
確認:

```bash
sudo ss -ltnp | grep ':80 '
sudo ufw status
curl http://127.0.0.1/
```

## 配置先

今回のUbuntu AP EC2:

```text
/home/ubuntu/music_app
```

GitHubから取得する場合:

```bash
cd /home/ubuntu
git clone <YOUR_REPOSITORY_URL> music_app
cd music_app
```

## Python環境

Ubuntuでは、OS標準Python用の `venv` を先に導入します。

```bash
sudo apt update
sudo apt install -y python3-venv
```

Ubuntu標準リポジトリに `python3.14-venv` がない環境では、個別バージョン名を
指定しません。次のコマンドはOS標準の `python3` で仮想環境を作ります。

```bash
cd /home/ubuntu/music_app
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r app/04_web_preview/requirements.txt
pip install -r app/03_matching_recommendation/requirements.txt
```

Python 3.14をUbuntu標準リポジトリ以外から個別に導入している場合は、先に
`python3.14 -m venv .venv` がそのまま動くか確認します。失敗した場合は、
Python 3.14を導入した配布元の手順に従って `venv` または `ensurepip` を追加します。
Ubuntu標準の `python3-venv` と外部配布のPython 3.14を混在させません。

## 環境変数

`deploy/python_ec2/music-app.env.example` を参考に `/home/ubuntu/music_app/app/.env` を作成します。

```bash
cd /home/ubuntu/music_app/app
cp ../deploy/python_ec2/music-app.env.example .env
vi .env
```

重要:

```text
ORACLE_DSN=<oracle-ec2-private-ip>:1521/FREEPDB1
OPENAI_API_KEY=<your-key>
```

## 手動起動確認

```bash
cd /home/ubuntu/music_app/app
set -a
. ./.env
set +a
../.venv/bin/uvicorn 04_web_preview.app:app --host 127.0.0.1 --port 8000
```

別端末で確認:

```bash
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/recommendations/random?limit=10
```

`curl: (7) Failed to connect to 127.0.0.1 port 8000` の場合はFastAPIが起動して
いません。systemd導入後は次で確認します。

```bash
sudo systemctl status music-app-web.service
sudo journalctl -u music-app-web.service --no-pager -n 80
sudo ss -ltnp | grep ':8000 '
```

## systemd

`deploy/python_ec2/music-app-web.service` を `/etc/systemd/system/music-app-web.service` へ配置します。

```bash
cd /home/ubuntu/music_app
sudo cp deploy/python_ec2/music-app-web.service /etc/systemd/system/music-app-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now music-app-web.service
sudo systemctl status music-app-web.service
```

このserviceファイルはUbuntuの `/home/ubuntu/music_app` 配置用です。

## Apache

`deploy/python_ec2/music-app-apache.conf` をApacheへ配置します。

```bash
sudo a2enmod proxy proxy_http headers
sudo cp deploy/python_ec2/music-app-apache.conf /etc/apache2/conf-available/music-app.conf
sudo a2enconf music-app
sudo apache2ctl configtest
sudo systemctl reload apache2
```

## Browser

```text
http://<python-ec2-public-ip>/music/
```

Python EC2自身から音源を配信する場合は、`docs/09_hosted_audio_cloud_setup.md`
の手順で `hosted_audio_files` と音源ディレクトリを準備します。

## Oracle Connection Check

AP EC2からOracle EC2のTCP 1521へ接続できることを確認します。

```bash
nc -vz -w 3 <oracle-ec2-private-ip> 1521
```

期待値:

```text
Connection to <oracle-ec2-private-ip> 1521 port [tcp/*] succeeded!
```

タイムアウトする場合は、AP EC2のOutbound、Oracle EC2のInbound、Network ACLの
順に確認します。

## OpenAI Connection Check

AP EC2からOpenAI APIへ到達できることを確認します。

```bash
curl -sS -o /dev/null -w 'http_code=%{http_code}\n' \
  --max-time 8 https://api.openai.com/v1/models
```

APIキーを付けていないため `401` が正常です。タイムアウトする場合は、AP EC2の
Outbound TCP 443、Network ACL、ルートテーブルの順に確認します。

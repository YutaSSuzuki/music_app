# Python EC2 Setup

## 推奨インスタンス

- Instance: `t3.small` or `t3.medium`
- OS: Amazon Linux 2023 or Ubuntu 22.04
- Security Group:
  - HTTP 80: 自分のIPまたは利用範囲
  - SSH 22: 自分のIPのみ
  - outbound 1521: Oracle EC2へ
  - outbound 443: OpenAI APIへ

## 配置先

```text
/opt/music-app/oracle
```

GitHubから取得する場合:

```bash
sudo mkdir -p /opt/music-app
sudo chown -R ec2-user:ec2-user /opt/music-app
cd /opt/music-app
git clone <YOUR_REPOSITORY_URL> oracle
cd oracle/cloud_lift
```

## Python環境

```bash
cd /opt/music-app/oracle/cloud_lift/app
python3 -m venv .venv
. .venv/bin/activate
pip install -r 04_web_preview/requirements.txt
pip install -r 03_matching_recommendation/requirements.txt
```

## 環境変数

`deploy/python_ec2/music-app.env.example` を参考に `/opt/music-app/oracle/cloud_lift/app/.env` を作成します。

```bash
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
cd /opt/music-app/oracle/cloud_lift/app
. .venv/bin/activate
set -a
. ./.env
set +a
uvicorn 04_web_preview.app:app --host 127.0.0.1 --port 8000
```

別端末で確認:

```bash
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/recommendations/random?limit=10
```

## systemd

`deploy/python_ec2/music-app-web.service` を `/etc/systemd/system/music-app-web.service` へ配置します。

```bash
sudo cp deploy/python_ec2/music-app-web.service /etc/systemd/system/music-app-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now music-app-web.service
sudo systemctl status music-app-web.service
```

## Apache

`deploy/python_ec2/music-app-apache.conf` をApacheへ配置します。

Ubuntu:

```bash
sudo a2enmod proxy proxy_http headers
sudo cp deploy/python_ec2/music-app-apache.conf /etc/apache2/conf-available/music-app.conf
sudo a2enconf music-app
sudo systemctl reload apache2
```

Amazon Linux系:

```bash
sudo cp deploy/python_ec2/music-app-apache.conf /etc/httpd/conf.d/music-app.conf
sudo systemctl reload httpd
```

## Browser

```text
http://<python-ec2-public-ip>/music/
```

Python EC2自身から音源を配信する場合は、`docs/09_hosted_audio_cloud_setup.md`
の手順で `hosted_audio_files` と音源ディレクトリを準備します。

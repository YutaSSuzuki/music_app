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
cd /opt/music-app/oracle/cloud_lift
. app/.venv/bin/activate
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

sqlplus system@//localhost:1521/FREEPDB1
```

DB件数確認はPython EC2から実行:

```bash
cd /opt/music-app/oracle/cloud_lift/app
. .venv/bin/activate
set -a
. ./.env
set +a
python3 03_matching_recommendation/phase1_cli.py health
```

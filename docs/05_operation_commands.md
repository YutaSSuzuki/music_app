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

## Oracle EC2

```bash
docker ps
docker logs -f oracle-free
```

DB件数確認:

```bash
cd /opt/music-app/oracle/cloud_lift/app
. .venv/bin/activate
set -a
. ./.env
set +a
python3 03_matching_recommendation/phase1_cli.py health
```


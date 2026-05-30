# GitHub Upload Plan

## GitHubに置くもの

- `cloud_lift/app/`
- `cloud_lift/deploy/`
- `cloud_lift/docs/`
- `cloud_lift/sql/`
- `cloud_lift/data/local_library_registration_plan_after_import/`

## GitHubに置かないもの

- `.env`
- `watch-history.json`
- Oracle dump file
- OpenAI API key
- Oracle password
- 音源ファイル
- `__pycache__`
- `.venv`

## EC2から取り込む流れ

```bash
sudo mkdir -p /opt/music-app
sudo chown -R ec2-user:ec2-user /opt/music-app
cd /opt/music-app
git clone <YOUR_REPOSITORY_URL> oracle
cd oracle/cloud_lift
```

その後:

```bash
cd app
python3 -m venv .venv
. .venv/bin/activate
pip install -r 04_web_preview/requirements.txt
pip install -r 03_matching_recommendation/requirements.txt
```


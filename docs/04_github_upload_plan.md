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
cd /home/ubuntu
git clone <YOUR_REPOSITORY_URL> music_app
cd music_app
```

その後:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r app/04_web_preview/requirements.txt
pip install -r app/03_matching_recommendation/requirements.txt
```

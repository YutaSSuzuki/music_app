# GitHub Upload Plan

## GitHubに置くもの

- `cloud_lift/app/`
- `cloud_lift/deploy/`
- `cloud_lift/docs/`
- `cloud_lift/sql/`

## GitHubに置かないもの

- `.env`
- `watch-history.json`
- Oracle dump file
- 音源manifest TSV
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

その後は `docs/02_python_ec2_setup.md` に従います。

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r app/04_web_preview/requirements.txt
pip install -r app/03_matching_recommendation/requirements.txt
```

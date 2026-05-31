# Oracle Music App Cloud Lift

このディレクトリは、現在のローカル/zephy版アプリをAWSへ段階移行するための資料と必要ファイルをまとめたものです。

最初の移行先は、Lambdaではなく次の2台EC2構成にします。

```text
Browser
  |
  | http://python-ec2/music/
  v
Python EC2
  - Apache
  - FastAPI / uvicorn
  - OpenAI API call
  - hosted audio files
  |
  | Oracle Net 1521
  v
Oracle EC2
  - Oracle AI Database 26ai Free RPM installation
```

この段階でWeb画面、DB接続、AI推薦、YouTube履歴取り込み、音声配信まで確認します。  
その後に、画面をS3へ、APIをLambda/API Gatewayへ移します。

## Directory

```text
cloud_lift/
  app/                         current application files
  data/                        local library registration ledger
  deploy/
    python_ec2/                Apache/systemd/env/bootstrap examples
    oracle_ec2/                Oracle Linux 9 RPM setup and legacy container examples
    client/                    Windows client helper
    source/                    source audio manifest helper
  docs/                        migration documents
  sql/                         Oracle schema SQL
```

## First Target

まず目指す状態:

- Python EC2で `http://<public-ip-or-domain>/music/` が開ける
- Python EC2のFastAPIからOracle EC2へ接続できる
- 初期表示でDBランダム10曲が出る
- Random推薦が保存される
- YouTube履歴のDry run/importが動く
- OpenAI APIキー設定後にAI推薦が動く
- 音声ファイルをPython EC2から配信できる
- Python EC2上の音源だけを候補にしてAI推薦できる

## Important Files

- Web API: `app/04_web_preview/app.py`
- Web UI: `app/04_web_preview/static/index.html`
- Recommendation logic: `app/03_matching_recommendation/phase1_cli.py`
- YouTube import: `app/01_youtube_history/youtube_takeout_import.py`
- DB schema: `sql/002_revised_schema.sql`
- Hosted audio schema: `sql/003_hosted_audio_files.sql`
- Hosted audio cloud guide: `docs/09_hosted_audio_cloud_setup.md`
- Tested zephy hosted state: `docs/10_zephy_hosted_audio_state.md`
- Python EC2 guide: `docs/02_python_ec2_setup.md`
- Oracle EC2 guide: `docs/01_oracle_ec2_setup.md`
- Migration order: `docs/00_migration_plan.md`

## Files Not Included

以下はGitHubへアップロードしない前提です。

- `.env`
- OpenAI API key
- Oracle password with real value
- YouTube Takeout raw `watch-history.json`
- 音源ファイル本体
- Oracle database dump containing personal history, unless private repository/storage is used

# Oracle Music App Cloud Lift

AWSへのクラウドリフトは完了しています。現在は次の2台EC2構成です。

```text
Browser
  |
  | http://<ap-public-ip>/music/
  v
AP EC2 (Ubuntu)
  - Apache
  - FastAPI / uvicorn systemd
  - OpenAI API call
  - /data/music-app/audio/
  |
  | Oracle Net 1521
  v
Oracle EC2 (RHEL 9)
  - Oracle AI Database 26ai Free RPM installation
  - FREEPDB1 / MUSIC_APP_V2
```

gerbera音声APIとzephy固有の音源パスはクラウド版で使用しません。AP EC2に配置した
音源をFastAPIからHTTP Range対応で配信します。

## Validated State

2026-05-31に次を確認済みです。

- Apache経由の画面表示
- AP EC2からOracle EC2への接続
- DBからのrandom推薦
- OpenAI APIを使うAI推薦
- YouTube Music履歴を含むDB移行
- 音源644件、3.15 GiBの転送とDB登録
- 音声再生、連続再生、HTTP `206 Partial Content`

詳細は `docs/07_current_state.md` を参照してください。

## Directory

```text
cloud_lift/
  app/                         FastAPI、Web画面、推薦、履歴取り込み
  deploy/
    python_ec2/                Ubuntu AP EC2用の設定と音源登録スクリプト
    oracle_ec2/                Oracle EC2用のRPMセットアップ補助
    source/                    転送前音源manifest作成
  docs/                        構築、運用、将来移行の手順書
  sql/                         DDL、疎通確認、Data Pump補助SQL
```

## Start Here

- 現在状態: `docs/07_current_state.md`
- Oracle EC2再構築: `docs/01_oracle_ec2_setup.md`
- AP EC2再構築: `docs/02_python_ec2_setup.md`
- 音源の再転送とDB登録: `docs/09_hosted_audio_cloud_setup.md`
- 手動での曲追加: `docs/11_manual_track_addition.md`
- 日常運用: `docs/05_operation_commands.md`
- 将来のS3/Lambda移行: `docs/06_next_lambda_s3.md`
- 次週以降の改修バックログ: `docs/10_next_iteration_backlog.md`

## Files Not Included

次はGitHubへ登録しません。

- `.env`
- OpenAI API key
- Oracle password
- YouTube Takeoutの `watch-history.json`
- 音源ファイル本体
- Oracle dump
- 音源manifest TSV

# Manifest

## App

- `app/04_web_preview/`: FastAPI Web/APIとブラウザ画面
- `app/03_matching_recommendation/`: Oracleコンテキスト作成とOpenAI推薦
- `app/01_youtube_history/`: YouTube Takeout履歴取り込み

## SQL

- `sql/002_revised_schema.sql`: 現行スキーマ
- `sql/003_hosted_audio_files.sql`: AP EC2配信用音源テーブル
- `sql/004_seed_cloud_smoke_test.sql`: 3曲の疎通確認データ
- `sql/005_delete_cloud_smoke_test.sql`: 疎通確認データ削除
- `sql/006_export_cloud_dump_with_dbms_datapump.sql`: liteコンテナからの全件dump出力
- `sql/007_prepare_cloud_dump_export.sql`: Data Pump権限付与と残存ジョブ削除
- `sql/008_reset_cloud_import_target.sql`: 再import前の対象DB初期化と外部キー無効化
- `sql/009_enable_cloud_import_constraints.sql`: import後の外部キー有効化と検証

## Deploy

- `deploy/python_ec2/bootstrap_ubuntu.sh`: Ubuntu AP EC2初期設定
- `deploy/python_ec2/music-app-web.service`: uvicorn用systemd service
- `deploy/python_ec2/music-app-apache.conf`: Apache `/music/` reverse proxy
- `deploy/python_ec2/music-app.env.example`: AP EC2環境変数例
- `deploy/python_ec2/register_hosted_audio.py`: 転送済み音源のDB登録
- `deploy/python_ec2/register_new_tracks.py`: TSVから新規曲をまとめて追加
- `deploy/python_ec2/check_hosted_audio.py`: 音源登録とファイル実体の検証
- `deploy/oracle_ec2/bootstrap_oracle_linux_9.sh`: RHEL 9 / Oracle Linux 9用RPMセットアップ補助
- `deploy/oracle_ec2/sqlplus_utf8.sh`: UTF-8設定付きSQL*Plus起動
- `deploy/source/build_hosted_audio_manifest.py`: 転送前ファイル存在確認と容量計算

## Docs

- `docs/00_migration_plan.md`: 完了済み構成と将来計画
- `docs/01_oracle_ec2_setup.md`: Oracle EC2再構築とDB移行
- `docs/02_python_ec2_setup.md`: Ubuntu AP EC2再構築
- `docs/03_audio_delivery.md`: 音声配信方式
- `docs/04_github_upload_plan.md`: GitHub登録対象
- `docs/05_operation_commands.md`: 運用コマンド
- `docs/06_next_lambda_s3.md`: 将来のLambda/S3移行案
- `docs/07_current_state.md`: 2026-05-31時点のAWS稼働状態
- `docs/08_current_architecture_and_flow.md`: 構成と処理フロー
- `docs/09_hosted_audio_cloud_setup.md`: 音源の再転送とDB登録
- `docs/10_next_iteration_backlog.md`: 次週以降の構成改善と機能追加
- `docs/11_manual_track_addition.md`: 画面未実装時の手動曲追加手順

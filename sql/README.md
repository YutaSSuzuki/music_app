# SQL

## Current Schema

- `002_revised_schema.sql`: 現行DDL
- `003_hosted_audio_files.sql`: AP EC2から配信する音源パスの追加DDL

主要テーブル:

- `tracks`
- `artists`
- `track_artists`
- `track_sources`
- `play_events`
- `track_features`
- `track_tags`
- `recommendation_runs`
- `recommendation_items`
- `hosted_audio_files`

クラウド版ではgerbera音声API用の `local_audio_files` を使用しません。

## Smoke Test

- `004_seed_cloud_smoke_test.sql`: 配信確認用の3曲を登録
- `005_delete_cloud_smoke_test.sql`: 配信確認用の3曲を削除

## Data Migration

- `006_export_cloud_dump_with_dbms_datapump.sql`: liteコンテナから全件dumpを出力
- `007_prepare_cloud_dump_export.sql`: Data Pump権限付与と残存ジョブ削除
- `008_reset_cloud_import_target.sql`: 再import前の対象DB初期化と外部キー無効化
- `009_enable_cloud_import_constraints.sql`: import後の外部キー有効化と整合性検証

再構築手順は `docs/01_oracle_ec2_setup.md` を参照してください。

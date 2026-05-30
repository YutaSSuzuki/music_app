# SQL メモ

## 初期PoC構成

- `artists`: アーティスト名の正規化用マスタ
- `tracks`: 手元の曲マスタ
- `play_history_youtube`: YouTube Music 再生履歴
- `play_history_sony`: Sony Music Center 再生履歴
- `track_features`: BPM、キー、ジャンル、ムードなど
- `track_tags`: 任意タグ
- `recommendation_logs`: 推薦結果の保存

## 補足

- `albums` は今は入れていません
- アルバム単位で扱いたくなったら後から追加できます
- 履歴テーブルには `raw_title`, `raw_artist` を持たせています
  - これは手元曲にまだ一致しない履歴も保存するためです

## ファイル

- `001_initial_schema.sql`: 初期PoC DDL
- `002_revised_schema.sql`: 双方向推薦に対応する改訂DDL
- `003_seed_phase1_mock.sql`: 改訂DDL用の最小モックデータ

## 改訂構成

今後はYouTube Music履歴からローカル曲を推薦するだけでなく、ローカル再生履歴からYouTube Music側のおすすめを作る可能性がある。

そのため、履歴テーブルをサービスごとに分けず、以下の共通構成にする。

- `tracks`: 曲そのもの
- `artists`: アーティスト
- `track_artists`: 曲とアーティストの対応
- `track_sources`: 曲が存在する場所。`local`, `youtube_music`, `sony_music_center`
- `local_audio_files`: ローカルファイルの実体。DドライブはWSLでは `/mnt/d/...`
- `play_events`: 再生履歴。YouTube Music、ローカル、Sonyなどを `source_name` で区別
- `track_features`: BPM、キー、ジャンルなど
- `track_tags`: 任意タグ
- `recommendation_runs`: 推薦実行単位
- `recommendation_items`: 推薦された曲

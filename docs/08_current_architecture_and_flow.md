# Cloud Architecture and Processing Flow

この資料は2026-05-31に稼働確認したクラウド構成と、画面操作ごとの処理内容を説明します。

## 1. System Overview

```text
Browser
  |
  | Web screen, JSON API, audio delivery
  | http://<python-ec2>/music/
  v
Python EC2
  Apache
    /music/ -> http://127.0.0.1:8000/
  FastAPI / uvicorn
    app/04_web_preview/app.py
  Audio files
    /data/music-app/audio/<track_source_id>.<ext>
  |
  | Oracle Net 1521
  v
Oracle EC2
  Oracle AI Database 26ai Free
  schema: music_app_v2
  |
  | OpenAI Responses API
  v
OpenAI API
```

gerbera上の音声APIはクラウド版では使用しません。

## 2. Main Database Tables

| Table | Purpose |
|---|---|
| `tracks` | 曲の基本情報 |
| `artists` | アーティスト情報 |
| `track_artists` | 曲とアーティストの関連 |
| `track_sources` | local、YouTube Musicなど曲の出所 |
| `hosted_audio_files` | Python EC2から配信する音源パス |
| `play_events` | YouTube Musicなどの再生履歴 |
| `recommendation_runs` | 推薦実行単位のログ |
| `recommendation_items` | 推薦結果の各曲 |
| `track_features` | BPM、キー、energy、mood、genreなど |
| `track_tags` | 自由形式のタグ |

`track_sources.source_name = 'local'` は所有曲を表します。物理ファイルは
`hosted_audio_files` で管理します。

## 3. Browser Initial Display

画面を開くと次を取得します。

```text
GET /api/status
GET /api/prompt-templates
GET /api/models
GET /api/recommendations/random?limit=10
```

初期表示はAIを使わず、`hosted_audio_files.is_available = 1` の曲から
Oracle DBがランダムに選びます。

## 4. Random

```text
POST /api/recommendations/run
  recommendation_mode = "random"
```

Oracle DBが配信可能曲を選び、推薦ログへ保存します。OpenAI APIは呼びません。

## 5. AI Recommendation

```text
POST /api/recommendations/run
  recommendation_mode = "youtube_history"
```

FastAPIはYouTube Music履歴と配信可能な所有曲をOpenAI APIへ渡します。
AIは `track_id` と理由だけを返し、FastAPIがDB候補と照合して保存します。

## 6. Audio Playback

推薦結果には配信URLが含まれます。

```text
Browser
  -> GET /tracks/{track_source_id}/audio
  -> FastAPI
  -> hosted_audio_files.file_path_linux
  -> audio file response
```

画面は連続再生に対応します。

## 7. YouTube Music History Import

```text
POST /api/youtube-history/import
```

Google Takeoutの `watch-history.json` からYouTube Music履歴を取り込みます。
Dry runでは最後にrollbackします。

## 8. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Web画面 |
| `GET` | `/api/status` | 設定状態 |
| `GET` | `/api/models` | AIモデル一覧 |
| `GET` | `/api/prompt-templates` | プロンプトテンプレート一覧 |
| `PUT` | `/api/prompt-templates/{id}` | テンプレート保存 |
| `POST` | `/api/youtube-history/import` | Takeout履歴Dry run/import |
| `POST` | `/api/recommendations/run` | RandomまたはAI推薦 |
| `GET` | `/api/recommendations/latest` | 最終保存済み推薦 |
| `GET` | `/api/recommendations/random?limit=10` | 初期表示 |
| `GET` | `/tracks/{track_source_id}/audio` | Python EC2上の音源配信 |

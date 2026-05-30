# Current Architecture and Processing Flow

取得日: 2026-05-30

この資料は、クラウド移行前の現行システム構成と、画面操作ごとの処理内容を説明するものです。

## 1. System Overview

現行システムは、zephyとgerberaの2台に分かれています。

```text
Browser on gerbera / Windows
  |
  | Web screen and JSON API
  | http://music-app.test/music/
  v
zephy
  Apache
    /music/ -> http://127.0.0.1:8000/
  FastAPI / uvicorn
    04_web_preview/app.py
  Oracle Database Free container
    schema: music_app_v2
  |
  | OpenAI Responses API
  v
OpenAI API

Browser
  |
  | Audio file request
  | http://127.0.0.1:8765/audio?path=...
  v
gerbera
  Local audio FastAPI
    05_local_audio_server/app.py
  Music files
    /mnt/d/yu28s/Music
```

重要な点:

- Web画面と推薦APIはzephyで動く
- Oracle DBもzephyで動く
- 音源ファイルはgerberaから見えるローカルディスクにある
- 音声再生時、ブラウザはzephy経由ではなくgerberaの音声APIへ直接アクセスする

## 2. Machine Responsibilities

### 2.1 zephy

zephyはWebアプリとDBを担当します。

```text
Apache:
  /music/ -> http://127.0.0.1:8000/

FastAPI:
  /home/codex/work/oracle/04_web_preview/app.py
  uvicorn 04_web_preview.app:app --host 127.0.0.1 --port 8000

Oracle:
  Oracle Database Free container
  schema: music_app_v2
  DSN: localhost:1521/FREEPDB1
```

FastAPIはsystemdで起動します。

```text
music-app-web.service
```

### 2.2 gerbera

gerberaはブラウザから再生する音源ファイルを返します。

```text
FastAPI:
  05_local_audio_server/app.py

Start command:
  python3 -m uvicorn 05_local_audio_server.app:app \
    --host 127.0.0.1 --port 8765
```

標準の許可ディレクトリ:

```text
/mnt/d/yu28s/Music
/home/suzu/Music
```

音声APIは、要求されたファイルパスが許可ディレクトリ配下にあることを確認してからファイルを返します。

### 2.3 Browser

ブラウザは2種類のHTTPアクセスを行います。

| 目的 | 接続先 |
|---|---|
| 画面、推薦API、YouTube履歴取り込み | zephy Web API |
| 音声ファイル再生 | gerbera local audio API |

現行画面では音声API URLが固定です。

```text
http://127.0.0.1:8765
```

そのため、ブラウザを開く端末上でgerbera音声APIへ到達できる必要があります。

## 3. Browser Access

ブラウザからzephyのApacheへ直接アクセスします。

```text
http://music-app.test/music/
```

名前解決を設定していない端末では、zephyのIPアドレスを使用します。

```text
http://<zephy-ip>/music/
```

Apacheは `/music/` をzephy内のFastAPI `http://127.0.0.1:8000/` へ転送します。

## 4. Main Database Tables

| Table | Purpose |
|---|---|
| `tracks` | 曲の基本情報。曲名などを保持する |
| `artists` | アーティスト情報 |
| `track_artists` | 曲とアーティストの関連 |
| `track_sources` | local、YouTube Musicなど、曲の入手元・表記 |
| `local_audio_files` | ローカル音源ファイルのパス |
| `play_events` | YouTube Musicなどの再生履歴 |
| `recommendation_runs` | 推薦実行単位のログ |
| `recommendation_items` | 推薦結果の各曲 |
| `track_features` | BPM、キー、energy、mood、genreなどの特徴量格納先 |
| `track_tags` | 作品名など自由形式のタグ格納先 |

`track_id` と `track_source_id` の違い:

```text
track_id:
  曲そのものを表すID

track_source_id:
  その曲のlocal音源、YouTube Music履歴など、出所ごとのID
```

同じ曲にlocal音源とYouTube Music履歴がある場合、`track_id` は共通で、`track_source_id` は別になります。

## 5. Browser Initial Display

画面を開くと、ブラウザは次の処理を行います。

```text
1. GET /api/status
2. GET /api/prompt-templates
3. GET /api/models
4. GET /api/recommendations/random?limit=10
```

初期表示の10曲はAIを使いません。Oracle DBがランダムに選びます。

主な抽出条件:

```text
track_sources.source_name = 'local'
track_sources.availability_status = 'available'
local_audio_files.is_available = 1
```

`track_id` 単位で重複排除した後、`DBMS_RANDOM.VALUE` で並び替えて10曲返します。

この初期表示は推薦ログへ保存しません。

## 6. Random Button

`Random` ボタンは、指定曲数分をOracle DB側でランダムに選びます。OpenAI APIは呼びません。

```text
Browser
  -> POST /api/recommendations/run
     recommendation_mode = "random"
  -> FastAPI
  -> Oracle DB random selection
  -> recommendation_runs / recommendation_items に保存
  -> GET /api/recommendations/latest
  -> Browser display
```

Randomで使用する主な値:

| UI | Purpose |
|---|---|
| `Recommendations` | 返す曲数 |

Randomでは以下は使いません。

- Model
- History days
- Candidate tracks
- Prompt template
- OpenAI API

推薦ログ:

```text
recommendation_type = web_random_db
model_name = oracle-db-random
```

## 7. Run Recommendation Button

`Run Recommendation` ボタンは、YouTube Music履歴とlocal曲候補をOpenAI APIへ渡し、AIに推薦させます。

```text
Browser
  -> edited prompt template save
  -> POST /api/recommendations/run
     recommendation_mode = "youtube_history"
  -> FastAPI
  -> Oracle DBから履歴と候補曲を取得
  -> OpenAI APIへJSON contextを送信
  -> OpenAI APIは track_id と reason のみ返却
  -> FastAPIがDB候補と照合
  -> title / artist / track_source_id をDB候補から補完
  -> recommendation_runs / recommendation_items に保存
  -> GET /api/recommendations/latest
  -> Browser display
```

### 7.1 History

Oracleの `play_events` から、次の条件でYouTube Music履歴を取得します。

```text
source_name = 'youtube_music'
match_status <> 'ignored'
played_at >= current UTC timestamp - History days
ORDER BY played_at DESC
```

`All history` を押すと期間条件を外します。

現行画面では取得上限は20件です。

### 7.2 Candidate Tracks

AIへ渡す候補曲は、local音源が利用可能な曲だけです。

```text
track_sources.source_name = 'local'
track_sources.availability_status = 'available'
local_audio_files.is_available = 1
```

通常は `Candidate tracks` で指定した件数を渡します。  
`All candidates` を押すと、利用可能な候補を全件渡します。

候補曲は履歴上の再生回数が多い順、同数なら `track_id` 順です。

### 7.3 JSON Sent to OpenAI

概略:

```json
{
  "task": "recommend_music_from_library",
  "input_source": "youtube_music",
  "target_source": "local",
  "history_days": 7,
  "use_history": true,
  "library_track_count": 595,
  "library_sample_strategy": "top_play_count",
  "constraints": [
    "Recommend only tracks included in library_tracks.",
    "Return only track_id and reason for each recommendation."
  ],
  "recent_history": [
    {
      "play_event_id": 1,
      "title": "example watched title",
      "artist": "example artist",
      "played_at": "2026-05-24T00:00:00"
    }
  ],
  "library_tracks": [
    {
      "track_id": 2,
      "track_source_id": 2,
      "title": "逆光",
      "artist": "坂本 真綾",
      "play_count": 1
    }
  ],
  "expected_output_shape": {
    "recommendations": [
      {
        "track_id": "number",
        "reason": "string"
      }
    ]
  }
}
```

実際のJSONには、候補曲の正規化済み表記やファイルパスも含まれます。

### 7.4 JSON Returned by OpenAI

OpenAI APIにはJSON Schemaを指定しています。返却させるのは `track_id` と `reason` のみです。

```json
{
  "recommendations": [
    {
      "track_id": 2,
      "reason": "履歴にある楽曲の雰囲気と合うため。"
    }
  ]
}
```

AIには `title`、`artist`、`track_source_id` を返させません。

理由:

- AIが曲名とファイルを誤って組み合わせるのを防ぐ
- 実際の音源ファイルをDB側で確実に引き当てる

FastAPIはAI返却後に、候補一覧の `track_id` と一致する情報を使って次を補完します。

```text
track_source_id
title
artist
```

候補にない `track_id` や重複した `track_id` が返った場合は、推薦結果を保存しません。

## 8. Prompt Templates

現在のテンプレート:

| Template | Purpose |
|---|---|
| `youtube_history` | YouTube Music履歴を参考に推薦 |
| `upbeat` | アップテンポ寄り |
| `calm` | 落ち着いた雰囲気 |
| `emotional` | 感情的、印象的な曲 |

画面で編集して保存すると、zephyの次のファイルが更新されます。

```text
04_web_preview/prompt_templates/<template-id>.txt
```

## 9. YouTube Music History Import

画面からGoogle Takeoutの `watch-history.json` を選択して取り込みます。

```text
Browser
  -> file content read
  -> POST /api/youtube-history/import
  -> FastAPI
  -> youtube_takeout_import.py
  -> YouTube Music entries only
  -> duplicate check
  -> local track matching
  -> play_events insert or rollback
  -> preview table response
```

### 9.1 Target Entries

次のいずれかを満たす履歴だけ対象です。

```text
header = "YouTube Music"
titleUrl starts with "https://music.youtube.com/"
```

### 9.2 Duplicate Check

次の値で既存履歴を確認します。

```text
source_name = 'youtube_music'
played_at
source_url
```

URLがない場合は `normalized_title` も使います。

### 9.3 Matching

YouTube Music履歴の曲名とアーティスト名を正規化し、local曲と照合します。

一致した場合:

```text
match_status = matched
track_id and track_source_id are set
```

一致しない場合:

```text
match_status = unmatched
track_id and track_source_id are null
```

### 9.4 Dry Run

Dry runはDBへ確定保存しない確認モードです。

処理中は通常取り込みと同じSQLを実行しますが、最後に `ROLLBACK` します。  
画面には、insert対象、duplicate、matched/unmatched、曲名、アーティスト、URLなどを表形式で表示します。

## 10. Audio Playback

推薦結果にはDBから取得したローカルファイルパスが含まれます。

画面はそのパスを使い、gerbera音声APIへアクセスします。

```text
Browser
  -> GET http://127.0.0.1:8765/audio?path=<encoded-local-path>
  -> gerbera local audio API
  -> allowed root check
  -> file exists check
  -> audio file response
```

画面側では以下も実装されています。

- 再生中に別の曲を再生すると、前の曲を停止
- 曲の終了後、次曲を自動再生
- ブラウザが自動再生を止めた場合は、次曲の再生操作を促す

## 11. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Web画面 |
| `GET` | `/api/status` | OpenAI API key設定状態とOracle接続先表示 |
| `GET` | `/api/models` | 選択可能なAIモデル |
| `GET` | `/api/prompt-templates` | プロンプトテンプレート一覧 |
| `GET` | `/api/prompt-templates/{id}` | テンプレート取得 |
| `PUT` | `/api/prompt-templates/{id}` | テンプレート保存 |
| `POST` | `/api/youtube-history/import` | Takeout履歴Dry run/import |
| `POST` | `/api/recommendations/run` | RandomまたはAI推薦を実行 |
| `GET` | `/api/recommendations/latest` | 最終保存済み推薦を取得 |
| `GET` | `/api/recommendations/random?limit=10` | 初期表示用ランダム曲取得 |
| `GET` | `/tracks/{track_source_id}/audio` | Web APIサーバー自身に音源がある場合の配信 |

gerbera音声API:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | 許可ディレクトリと存在確認 |
| `GET` | `/audio?path=...` | 許可済みローカル音源を配信 |

## 12. Current Limitations

- Web APIの `/api/status` はOracleへの実接続確認までは行わない
- YouTube履歴のマッチングは曲名とアーティスト名の完全一致に近い
- BPM、mood、作品名などを格納するテーブルはあるが、推薦JSONではまだ活用していない
- 現行画面の音声API URLは `http://127.0.0.1:8765` 固定
- 音源ファイルはクラウド保存されていない

## 13. Mapping to First Cloud Phase

最初のクラウド移行では、次のように置き換えます。

| Current | First AWS Phase |
|---|---|
| zephy Apache/FastAPI | Python EC2 Apache/FastAPI |
| zephy Oracle container | Oracle EC2 Oracle Database Free container |
| gerbera local audio files | 最初はPython EC2へ少数音源を配置して確認 |
| gerbera local audio API | Python EC2のFastAPI `/tracks/{track_source_id}/audio` を利用 |

EC2 2台構成で動作確認した後、S3画面とLambda/API Gatewayへ段階移行します。

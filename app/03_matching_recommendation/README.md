# Phase 1 CLI

Oracleに入っている最小サンプルデータを読み出し、LLMへ渡す推薦用JSONを作るCLIです。

`002_revised_schema.sql` の改訂スキーマを前提にします。

## 前提

zephyの `codex` ユーザーで実行します。

```bash
cd ~/work/oracle
. .venv/bin/activate
```

接続先の既定値:

```text
ORACLE_USER=music_app_v2
ORACLE_PASSWORD=CHANGE_ME
ORACLE_DSN=localhost:1521/FREEPDB1
```

変更したい場合は環境変数で上書きします。

## 疎通確認

```bash
python 03_matching_recommendation/phase1_cli.py health
```

期待する内容:

```json
{
  "database_user": "MUSIC_APP",
  "tracks": 4,
  "track_sources": 8,
  "local_audio_files": 4,
  "youtube_music_events": 4,
  "matched_youtube_music_events": 4
}
```

## LLM用JSON作成

標準出力に表示:

```bash
python 03_matching_recommendation/phase1_cli.py context
```

YouTube Music履歴からローカル曲を推薦する材料を作る場合:

```bash
python 03_matching_recommendation/phase1_cli.py context \
  --input-source youtube_music \
  --target-source local
```

将来、ローカル履歴からYouTube Music側の曲を推薦する場合:

```bash
python 03_matching_recommendation/phase1_cli.py context \
  --input-source local \
  --target-source youtube_music
```

ファイルに保存:

```bash
python 03_matching_recommendation/phase1_cli.py context --output 99_sandbox/llm_context_sample.json
```

このJSONをLLMへ渡して、`library_tracks` の中からおすすめ曲を選ばせます。

## OpenAI APIでおすすめ生成

APIキーはファイルに書かず、環境変数で渡します。

```bash
export OPENAI_API_KEY='新しく作ったAPIキー'
```

実行:

```bash
python 03_matching_recommendation/phase1_cli.py recommend
```

モデルを変える場合:

```bash
OPENAI_MODEL=gpt-4.1-mini python 03_matching_recommendation/phase1_cli.py recommend
```

結果を保存:

```bash
python 03_matching_recommendation/phase1_cli.py recommend --output 99_sandbox/recommendations_sample.json
```

返却された `track_id` が `library_tracks` に存在するか、CLI側で `validation` として確認します。

推薦結果をDBにも保存:

```bash
python 03_matching_recommendation/phase1_cli.py recommend \
  --output 99_sandbox/recommendations_sample.json \
  --save-db
```

保存先:

```text
recommendation_runs
recommendation_items
```

`validation.valid` が `false` の場合、DB保存は行いません。

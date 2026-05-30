# Current State

取得日: 2026-05-29

zephy側の現行DB状態:

```json
{
  "database_user": "MUSIC_APP_V2",
  "tracks": 598,
  "track_sources": 651,
  "local_audio_files": 644,
  "youtube_music_events": 145,
  "matched_youtube_music_events": 9,
  "recommendation_runs": 26,
  "recommendation_items": 198
}
```

現行zephy設定:

```text
FastAPI:
  WorkingDirectory=/home/codex/work/oracle
  EnvironmentFile=-/home/codex/work/oracle/.env
  ExecStart=/home/codex/work/oracle/.venv/bin/uvicorn 04_web_preview.app:app --host 127.0.0.1 --port 8000

Apache:
  /music/ -> http://127.0.0.1:8000/
```

EC2移行時はこの構成をPython EC2に再現します。


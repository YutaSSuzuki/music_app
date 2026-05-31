# Current AWS State

取得日: 2026-05-31

クラウドリフトは完了しています。zephyは移行元データの保管先であり、AWS上の
アプリ実行時には参照しません。

## AP EC2

```text
OS:                Ubuntu
Repository:        /home/ubuntu/music_app
Python venv:       /home/ubuntu/music_app/.venv
Environment file:  /home/ubuntu/music_app/app/.env
Audio files:       /data/music-app/audio/
Apache:            TCP 80 /music/ -> http://127.0.0.1:8000/
FastAPI:           music-app-web.service
```

## Oracle EC2

```text
OS:        RHEL 9
Database:  Oracle AI Database 26ai Free RPM installation
Service:   FREEPDB1
Schema:    MUSIC_APP_V2
Listener:  TCP 1521
```

## Database Counts

```text
TRACKS                        598
TRACK_SOURCES                 651
HOSTED_AUDIO_FILES            644
PLAY_EVENTS                   247
MATCHED_YOUTUBE_MUSIC_EVENTS   11
RECOMMENDATION_RUNS            37
RECOMMENDATION_ITEMS          285
```

音源は644件、合計3.15 GiBです。欠損ファイルはありません。

## Validated

- ブラウザから `http://<ap-public-ip>/music/` を表示
- ApacheからFastAPIへreverse proxy
- AP EC2からOracle EC2へTCP 1521接続
- random推薦
- OpenAI APIを使うAI推薦
- 音声再生と連続再生
- HTTP Range requestによる `206 Partial Content`

## Capacity Note

音源転送後、AP EC2の8 GiB EBSは空き容量が少なくなっています。運用前にgp3を
20 GiB以上へ拡張し、`df -h / /data/music-app/audio` で確認します。

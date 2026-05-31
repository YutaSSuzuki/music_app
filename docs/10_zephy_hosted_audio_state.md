# Zephy Hosted Audio State

取得日: 2026-05-30

この資料はzephy上で配信方式を検証した時点の断面です。クラウド版では検証用の
`/music/haishin/` ではなく `/music/` を使用します。

zephyから音源を配信する構成を確認済みです。

## Browser

```text
Hosted audio playback:
  http://192.168.11.23/music/haishin/
```

## Hosted Audio

```text
Table: hosted_audio_files
Available files: 644
Total size: 3.15 GiB
Missing files: 0
```

zephy上の配置先:

```text
/home/codex/work/oracle/hosted_audio/<track_source_id>.<ext>
```

クラウドのPython EC2では、次へ置き換えます。

```text
/data/music-app/audio/<track_source_id>.<ext>
```

## API

```text
GET  /api/haishin/recommendations/random?limit=10
POST /api/haishin/recommendations/run
GET  /haishin/tracks/{track_source_id}/audio
```

確認済み:

- Random表示
- HTTP Range requestによる `206 Partial Content`
- FLAC、M4A、MP3配信
- 連続再生
- hosted audioだけを候補にしたOpenAI推薦
- スマートフォンからのLAN内アクセス

## Cloud Mapping

| zephy | Python EC2 |
|---|---|
| `/home/codex/work/oracle/hosted_audio/` | `/data/music-app/audio/` |
| `http://192.168.11.23/music/haishin/` | `http://<python-ec2>/music/` |
| local Oracle container | Oracle EC2 Oracle Linux 9 RPM installation |

再現手順は `docs/09_hosted_audio_cloud_setup.md` を参照してください。

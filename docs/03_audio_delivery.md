# Audio Delivery

クラウド版では、所有しているローカル音源をすべてPython EC2へ転送して配信します。
gerbera上の音声APIは使用しません。

## Audio Directory

Python EC2上の配置先:

```text
/data/music-app/audio/<track_source_id>.<ext>
```

## Database

音源パスは `hosted_audio_files` に登録します。

```bash
sqlplus music_app_v2/<password>@//<oracle-ec2-private-ip>:1521/FREEPDB1 \
  @sql/003_hosted_audio_files.sql
```

主要列:

```text
track_source_id
track_id
file_path_linux
file_size_bytes
is_available
```

## Delivery API

ブラウザはPython EC2のFastAPIから音源を取得します。

```text
GET /tracks/{track_source_id}/audio
```

FastAPIは `hosted_audio_files.file_path_linux` を参照してファイルを返します。
HTTP Range requestによる部分配信に対応します。

## Setup

音源転送、DB登録、検証手順は `docs/09_hosted_audio_cloud_setup.md` を参照してください。

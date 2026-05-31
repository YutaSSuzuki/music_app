# Migration Plan

## 方針

いきなりLambda/API Gateway/S3へ移すのではなく、まずEC2 2台で現在の構成に近い形を作ります。

理由:

- Lambda + Oracle接続はVPC/NAT/package/CORSが同時に絡む
- 音声ファイル配信方式がまだクラウド前提になっていない
- 現在のFastAPIはApache配下で安定している
- 先にAWS上でDB/API/音声が動くことを確認した方が切り分けしやすい

## Phase 1: EC2 2台構成（完了）

```text
Python EC2:
  Apache
  FastAPI
  uvicorn systemd
  application files
  hosted audio files

Oracle EC2:
  Oracle AI Database 26ai Free RPM installation
  music_app_v2 schema
```

確認項目:

- `/api/status`
- `/api/recommendations/random?limit=10`
- `/api/recommendations/run` random mode
- YouTube history dry run
- YouTube history import
- AI recommendation
- audio playback

2026-05-31に、DB移行、音源644件の登録、random推薦、AI推薦、音声配信まで
確認済みです。現在の運用構成は `docs/07_current_state.md` を参照してください。

## Phase 2: 画面だけS3（未実施）

FastAPIはPython EC2のまま、`index.html` だけS3へ移します。

確認項目:

- S3画面からPython EC2 APIを呼べる
- CORSが正しく通る
- 音声再生が維持できる

## Phase 3: Lambda/API Gateway（未実施）

APIをLambdaへ移します。

確認項目:

- LambdaからOracle EC2へ1521接続できる
- LambdaからOpenAI APIへ出られる
- NAT Gateway要否を確定する
- oracledb/openai依存関係をLambda package/layerで処理できる

## Phase 4: 音声ファイルのS3化（未実施）

必要であれば音源をS3へ移し、DBにS3 object keyや署名付きURL生成用情報を持たせます。

# Next Iteration Backlog

記録日: 2026-05-31

クラウドリフト完了後、次週以降に実施する改修候補です。現行のEC2 2台構成は
`docs/07_current_state.md` に記録しています。

## Architecture

| Priority | Item | Purpose | Completion Check |
| --- | --- | --- | --- |
| 1 | 手順確認のための作り直し | 手順書だけで環境を再現できることを確認する | 新規環境で画面表示、random推薦、AI推薦、音声再生まで確認できる |
| 2 | Cognito認証の追加 | 未認証ユーザーによる画面、API、音源へのアクセスを防ぐ | 未認証アクセスを拒否し、ログイン後のみ利用できる |
| 3 | private subnetへの移行 | APとOracle DBをインターネットから直接到達できない構成にする | 外部公開経路を限定し、APからDBとOpenAI APIへ接続できる |
| 4 | APサーバーのserverless化 | AP EC2の常時運用を減らし、APIをLambda/API Gatewayへ移す | random推薦、AI推薦、履歴取り込みがLambda経由で動く |
| 5 | CloudFrontキャッシュ | 静的画面と音源配信の負荷、転送量、待ち時間を抑える | キャッシュ対象とTTLを定義し、音源再生と認証が両立する |

CloudFront導入時は、音源をS3 private bucketへ移し、CloudFrontの署名付きURLまたは
署名付きCookieを使用する構成を検討します。認証前の音源を公開キャッシュしないように
します。

private subnet移行時は、OpenAI APIへのoutbound通信経路も必要です。NAT Gateway、
NAT instance、または構成変更による代替案を比較します。

## Features

| Priority | Item | Purpose | Completion Check |
| --- | --- | --- | --- |
| 1 | 楽曲追加機能 | 画面または管理処理から音源と曲情報を追加する | ファイル配置、DB登録、random推薦、音声再生まで反映される |
| 2 | 音楽特徴量の追加 | 推薦精度を上げるためDBへ特徴量を保存する | BPM、ジャンル、ムードなどを登録し、推薦プロンプトで利用できる |
| 3 | 好みに合わない楽曲の削除 | 推薦候補から不要曲を除外する | 物理削除か論理削除かを決め、削除後に推薦対象から外れる |
| 4 | マイリスト機能 | 任意の曲をまとめて保存、再生する | マイリスト作成、曲追加、曲削除、一覧表示、連続再生ができる |

## Design Notes

- Cognito導入後はユーザー単位のデータ所有者を識別できるようにする。
- 楽曲削除は誤操作に備え、最初は論理削除を基本とする。
- マイリストはCognitoユーザー単位で管理する。
- 特徴量は既存の `track_features` を拡張できるか確認してからDDLを追加する。
- CloudFront、S3、Lambdaの具体化は `docs/06_next_lambda_s3.md` も参照する。

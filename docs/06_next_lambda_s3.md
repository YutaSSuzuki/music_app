# Later: Lambda and S3

EC2 2台構成で動作確認できた後、以下の順で移します。

次週以降の改修候補全体と優先順は `docs/10_next_iteration_backlog.md` を参照してください。

## 1. 画面だけS3

- `04_web_preview/static/index.html` をS3へ置く
- API base URLをPython EC2へ向ける
- FastAPIにCORSを追加する

## 2. APIをLambdaへ

- FastAPIをMangumでLambda handler化する
- API Gateway HTTP APIを作る
- LambdaをVPC内に置く
- Lambda SGからOracle EC2 1521へ接続許可する
- OpenAI APIへ出るためのNAT Gateway要否を確認する

## 3. 音声をS3へ

- 音源をS3 private bucketへ置く
- DBにS3 keyを保持する
- APIが署名付きURLを返す
- ブラウザは署名付きURLで再生する

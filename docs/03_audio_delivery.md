# Audio Delivery

現行アプリでは、DBの `local_audio_files.file_path_linux` / `file_path_windows` にローカルPC前提のパスが入っています。

クラウドで音を出すには、以下のどちらかが必要です。

## Option A: Python EC2へ音源を置く

最初の確認ではこの方式が簡単です。

例:

```text
/data/music/...
```

DBの `local_audio_files.file_path_linux` をPython EC2上の実パスへ更新します。

メリット:

- 今のFastAPIの `/tracks/{track_source_id}/audio` を使いやすい
- S3や署名付きURLの設計が不要

注意:

- EBS容量が必要
- 音源バックアップを考える必要がある

## Option B: S3へ音源を置く

後段の本格運用向けです。

DBにはローカルパスではなくS3 keyを持たせ、APIで署名付きURLを発行する設計に変えます。

メリット:

- Lambda/API Gateway化しやすい
- 音源ファイルをEC2に置かなくてよい

注意:

- DBスキーマまたは追加テーブルの変更が必要
- ブラウザ再生URLの作り方を変える必要がある

## 最初の推奨

まずはOption Aで、Python EC2上に少数の音源だけ置いて再生確認します。  
全曲移行は、DB/API/画面が動いた後で実施します。


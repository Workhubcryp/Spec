# File Browser

LAN 内の指定ディレクトリを読み取り専用で閲覧する Flask アプリケーションです。
MVP では、フォルダ移動、親フォルダへの移動、ファイルダウンロード、
テキスト・画像・PDF のプレビューに対応しています。

## 起動

プロジェクトルートから実行する場合:

```bash
FILE_BROWSER_BASE_DIR="$PWD/file-browser/sample-data" \
  .pythonlibs/bin/python file-browser/app.py
```

または `file-browser` ディレクトリへ移動して:

```bash
cd file-browser
python app.py
```

ブラウザで `http://localhost:8000/` を開きます。LAN の別端末からは、
サーバーのLAN内IPアドレスを使ってアクセスします。

## 設定

`.env.example` を参考に環境変数を設定してください。

`FILE_BROWSER_BASE_DIR` は必須の運用設定です。未指定時はカレントディレクトリを
使いますが、実運用では必ず明示的な読み取り対象ディレクトリを指定してください。

## テスト

プロジェクトルートから:

```bash
.pythonlibs/bin/pytest -q file-browser/tests
```

テストでは、Path Traversal、絶対パス、外部シンボリックリンク、
BASE_DIR と似た名前の兄弟ディレクトリへのアクセスを検証します。

## セキュリティ上の注意

- MVP は読み取り専用です。アップロード・削除・名前変更は未実装です。
- 認証なしでインターネットへ公開しないでください。
- ルーターのポート開放は行わず、信頼できるLANまたはVPN内で運用してください。
- Flask のデバッグモードは本番運用で有効にしないでください。
- サーバーは `BASE_DIR` 外のパス、Path Traversal、外部を指すシンボリックリンクを拒否します。
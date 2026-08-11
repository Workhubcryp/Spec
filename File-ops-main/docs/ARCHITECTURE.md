# File Management System — Architecture

## 1. 文書の目的

本書は、LAN 内の指定ディレクトリを安全にブラウズする File Management
System の実装方針を定義する。対象は、アップロードされた仕様書に記載された
MVP と、将来のファイル管理機能を無理なく追加できる拡張構成である。

この段階ではアプリケーションコードを実装せず、責務・境界・データ契約・安全性
および段階的な開発順序を確定する。

## 2. 目標と非目標

### 2.1 MVP の目標

- 設定した `BASE_DIR` 配下のディレクトリをブラウザで閲覧できる
- ディレクトリへ移動し、親ディレクトリへ戻れる
- ファイル名、種類、サイズ、更新日時を一覧表示できる
- ファイルをダウンロードできる
- テキスト・画像・PDFなど、ブラウザ表示に適したファイルをプレビューできる
- `BASE_DIR` より上位へアクセスできない
- Path Traversal と、`BASE_DIR` 外を指すシンボリックリンクを拒否する
- PC とスマートフォンの双方で利用できる
- LAN 内で `HOST` と `PORT` を指定して起動できる

### 2.2 MVP に含めないもの

以下は設計上の拡張ポイントとして残すが、MVP では実装しない。

- アップロード、削除、名前変更、移動、コピー、フォルダ作成
- 全文検索
- ユーザー管理、ログイン、ユーザー別権限
- 圧縮・解凍
- 複数の保存領域
- 外部公開を前提にした HTTPS 終端
- ファイルメタデータをデータベースへ同期する仕組み

書き込み操作を MVP から除外することで、誤操作と攻撃面を小さくし、
まず「安全な読み取り専用 File Browser」を完成させる。

## 3. アーキテクチャ概要

### 3.1 採用方針

初期実装は、1つの Flask アプリケーション内に責務を分離した
**Modular Monolith** とする。

```text
Web Browser
    │ HTTP（LAN内のMVP） / HTTPS（将来）
    ▼
Reverse Proxy（任意。MVPでは省略可能）
    ▼
Gunicorn または Flask Server
    ▼
Presentation / Templates
    ▼
Routing Layer
    ▼
Service Layer
    ▼
Security Layer（Path Resolver / Permission）
    ▼
Filesystem Adapter
    ▼
BASE_DIR
```

認証や検索を追加する場合も、Route から直接 `os` / `pathlib` を呼び出さず、
Service と Security の境界を経由する。

### 3.2 レイヤー依存方向

```text
Presentation
    ↓
Routes
    ↓
Services
    ↓
Security + Filesystem Adapter
    ↓
Operating System Filesystem
```

依存は上から下への一方向とする。Filesystem の具体的な実装を
`FilesystemAdapter` に隔離することで、テスト用の一時ディレクトリや将来の
別ストレージへの差し替えを容易にする。

## 4. コンポーネント責務

### 4.1 Application / Configuration

責務:

- Flask の Application Factory を生成する
- 設定を環境変数から読み込む
- Blueprint、エラーハンドラ、ロギングを登録する
- 起動時に `BASE_DIR` の存在・ディレクトリ種別・読み取り可否を検証する

主要設定:

| 設定 | 既定値 | 説明 |
| --- | --- | --- |
| `FILE_BROWSER_BASE_DIR` | 必須 | ブラウズのルートディレクトリ |
| `FILE_BROWSER_HOST` | `0.0.0.0` | 待受アドレス |
| `FILE_BROWSER_PORT` | `8000` | 待受ポート |
| `FILE_BROWSER_DEBUG` | `false` | 本番では必ず無効 |
| `FILE_BROWSER_MAX_PREVIEW_BYTES` | 例: 2 MiB | テキストプレビュー上限 |
| `FILE_BROWSER_AUTH_ENABLED` | `false` | MVPでは認証なし |
| `FILE_BROWSER_LOG_LEVEL` | `INFO` | ログレベル |

秘密情報は環境変数または実行環境の Secret 管理に置き、リポジトリへ
コミットしない。

### 4.2 Presentation Layer

責務:

- HTML テンプレートと CSS / JavaScript の提供
- 一覧、パンくず、親ディレクトリ、ソート状態、エラー画面の表示
- サーバーから渡された表示用 DTO のレンダリング

Presentation Layer はファイルシステムのパスを解決しない。画面に表示する
パスは、物理パスではなく `BASE_DIR` からの相対的な仮想パスを使用する。
サーバーの絶対パスを公開しない。

### 4.3 Routing Layer

責務:

- HTTP リクエストを受け取る
- URL パラメータとクエリを最低限検証する
- Service を呼び出す
- DTO を HTML または JSON に変換する
- 例外を HTTP ステータスへ変換する

Route では `os.listdir`、`send_file` の対象パス組み立て、`open` などの
Filesystem 操作を直接行わない。

### 4.4 Service Layer

MVP のサービス:

- `DirectoryService`
  - ディレクトリ一覧取得
  - 親ディレクトリ取得
  - エントリの表示用メタデータ生成
- `FileService`
  - ファイル存在確認
  - ダウンロード対象の取得
  - MIME 種別判定
- `PreviewService`
  - プレビュー可能種別の判定
  - テキストのサイズ上限・文字コード処理
  - プレビュー用レスポンスデータの作成

将来追加するサービス:

- `UploadService`
- `MutationService`（削除、名前変更、移動、コピー、フォルダ作成）
- `SearchService`
- `ArchiveService`
- `PermissionService`

Service は「何をするか」を表現し、ユーザーから与えられたパスを直接
信頼しない。すべてのパスは Security Layer の resolver を通す。

### 4.5 Security Layer

Security Layer は Filesystem に触れる直前の必須境界である。

- `PathResolver`
  - 仮想相対パスを受け取り、`BASE_DIR` 内の安全なパスへ変換する
  - ルート外なら例外を送出する
- `PathPolicy`
  - 読み取り、ダウンロード、プレビュー、将来の書き込み権限を判定する
- `RequestSecurity`
  - リクエストサイズ、メソッド、Content-Type などの共通検査
- `AuthPolicy`（将来）
  - ログイン状態とユーザー権限を判定する

Security Layer は、Route や Template から迂回できないように Service の
共通入口として設計する。

### 4.6 Filesystem Adapter

標準ライブラリの `pathlib` を基本とし、Filesystem の読み取り操作を
`FilesystemAdapter` に集約する。

```text
FilesystemAdapter.list_directory(safe_path)
FilesystemAdapter.stat(safe_path)
FilesystemAdapter.open_for_download(safe_path)
FilesystemAdapter.read_preview(safe_path, max_bytes)
```

Adapter が受け取るのは、PathResolver で検証済みの `SafePath` のみとする。
未検証の文字列パスを引数に取る公開メソッドは作らない。

## 5. 推奨ディレクトリ構成

仕様書の責務分割を、テストと拡張性を考慮して次の構成に整理する。

```text
file-browser/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
│
├── src/
│   └── file_browser/
│       ├── __init__.py
│       ├── app.py                  # Application Factory
│       ├── config.py               # 環境変数の読み込みと検証
│       │
│       ├── routes/
│       │   ├── web.py              # HTML画面
│       │   ├── files.py            # ファイル一覧・ダウンロード
│       │   ├── preview.py          # ファイルプレビュー
│       │   └── api.py              # 将来のREST API
│       │
│       ├── services/
│       │   ├── directory_service.py
│       │   ├── file_service.py
│       │   └── preview_service.py
│       │
│       ├── security/
│       │   ├── path_resolver.py
│       │   ├── policies.py
│       │   └── exceptions.py
│       │
│       ├── filesystem/
│       │   ├── adapter.py
│       │   └── models.py
│       │
│       ├── infrastructure/
│       │   ├── logging.py
│       │   └── mime_types.py
│       │
│       ├── templates/
│       │   ├── base.html
│       │   ├── index.html
│       │   ├── preview.html
│       │   └── error.html
│       │
│       └── static/
│           ├── css/style.css
│           └── js/app.js
│
└── tests/
    ├── conftest.py
    ├── test_browse.py
    ├── test_download.py
    ├── test_preview.py
    ├── test_path_security.py
    └── test_error_handling.py
```

`models/` は最初からデータベースモデルを意味する名前ではなく、
Filesystem の表示用 DTO は `filesystem/models.py` に置く。DB導入時に
`metadata/` または `persistence/` を別途追加し、実ファイルと混同しない。

## 6. パスとセキュリティ設計

### 6.1 仮想パスの原則

URL には `BASE_DIR` の絶対パスを含めず、常に `BASE_DIR` からの相対パスを
使用する。

```text
URL:          /files/projects/demo
仮想パス:     projects/demo
物理パス:     BASE_DIR / projects / demo
```

URL とファイルシステムの変換は `PathResolver` の一箇所だけで行う。

### 6.2 Resolver の検証手順

MVP のすべての read endpoint は、次の順序で検証する。

1. URL パラメータを URL デコードする
2. NUL 文字を拒否する
3. OS に依存しない相対仮想パスとして解釈する
4. 絶対パス、ドライブレター、UNC パスを拒否する
5. `.`、`..` を正規化する
6. `BASE_DIR` を `resolve()` して基準パスを固定する
7. 対象パスを `resolve()` する
8. 対象が `BASE_DIR` 自身またはその配下かを `relative_to()` で確認する
9. 配下でなければ `403 Forbidden` として拒否する
10. 対象の種別（ディレクトリ、通常ファイル、その他）を確認してから操作する

文字列の `startswith(BASE_DIR)` だけで判定してはならない。例えば
`/data/spec-other` は `/data/spec` の配下ではないため、Path の境界を持つ
比較を使用する。

### 6.3 シンボリックリンク

安全性を優先し、`BASE_DIR` 外へ解決されるシンボリックリンクは一覧表示・
移動・ダウンロード・プレビューのすべてで拒否する。

- エントリ一覧では `lstat` と解決後のパスを確認する
- 外部を指すリンクは「アクセス不可」として表示するか、MVPでは一覧から除外する
- リンク先が存在しない場合も、通常ファイルとして扱わない
- 将来の書き込み操作では、リンクを辿らないポリシーを既定にする

なお、`resolve()` 後の検査と実際の open の間にファイルが置き換わる
TOCTOU を高い脅威モデルで防ぐ必要がある場合は、Linux では
`openat`、`O_NOFOLLOW`、ディレクトリ FD を使う実装へ拡張する。
MVP では LAN 内の読み取り専用運用を前提としつつ、この拡張余地を残す。

### 6.4 その他の入力防御

- ファイル名を HTML に埋め込む際はテンプレートの自動エスケープを有効にする
- Content-Disposition のファイル名は RFC 互換の安全な生成を行う
- 例外メッセージに物理パス、環境変数、スタックトレースを表示しない
- `send_file` や `send_from_directory` に未検証のユーザー入力を渡さない
- 大きなテキストを全量メモリへ読み込まず、プレビュー上限を設ける
- 隠しファイルを無条件に除外するかどうかは設定として決める

## 7. HTTP / URL 設計

### 7.1 MVP の画面ルート

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/` | BASE_DIR のルート一覧 |
| `GET` | `/browse/<path>` | 指定ディレクトリの一覧 |
| `GET` | `/download/<path>` | ファイルのダウンロード |
| `GET` | `/preview/<path>` | プレビュー画面またはインライン表示 |

仕様書の `/` と `/<path>` という表現は、将来の静的ファイルや API と衝突
しやすい。そのため実装では `/browse/<path>` を正規ルートとし、必要なら
互換用に `/<path>` からリダイレクトする。ルート衝突を避けることを優先する。

### 7.2 将来の REST API

HTML と API の責務を分け、API は `/api/v1` を名前空間にする。

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/api/v1/files?path=` | 一覧取得 |
| `GET` | `/api/v1/files/<path>` | エントリ情報取得 |
| `GET` | `/api/v1/download/<path>` | ダウンロード |
| `GET` | `/api/v1/preview/<path>` | プレビュー情報取得 |
| `GET` | `/api/v1/search?q=&path=` | 将来の検索 |
| `POST` | `/api/v1/files/upload` | 将来のアップロード |

HTML と REST API は同じ Service を呼び出し、認可とパス検証を共有する。

### 7.3 一覧レスポンスの表示用モデル

```text
FileEntry
├── name: string
├── relative_path: string
├── kind: "directory" | "file" | "symlink" | "unavailable"
├── size_bytes: integer | null
├── modified_at: ISO-8601 string | null
├── mime_type: string | null
├── previewable: boolean
└── downloadable: boolean
```

`relative_path` は URL 生成に利用する仮想パスであり、物理パスを返さない。

## 8. ファイル表示・プレビュー

### 8.1 一覧

- ディレクトリを先に表示し、次にファイルを表示する
- 既定ソートは名前の昇順
- ソートキーは `name`、`size`、`modified`、`type`
- ソート順はサーバー側でホワイトリスト検証する
- 親ディレクトリは `BASE_DIR` 直下では表示しない
- 権限エラーや壊れたリンクは、サーバーエラーにせず個別エントリとして扱う

### 8.2 プレビュー

| 種類 | 既定動作 |
| --- | --- |
| UTF-8 テキスト（txt, md, py, json, yaml, html, css, js など） | テキスト表示 |
| 画像（jpg, png, webp など） | インライン表示 |
| PDF | ブラウザの PDF ビューアへインライン表示 |
| その他のバイナリ | ダウンロード |

拡張子だけを信頼せず、MIME 種別とファイル内容の扱いを組み合わせる。
HTML や SVG は、ブラウザで実行される可能性があるため、MVPでは
テキストとして表示するか、インライン表示を禁止する。

## 9. エラーと HTTP ステータス

| 状況 | HTTP | ユーザー向け表示 |
| --- | --- | --- |
| 対象が存在しない | `404` | ファイルまたはフォルダが見つからない |
| BASE_DIR 外、または拒否対象 | `403` | アクセスできない場所 |
| 認証が必要（将来） | `401` | ログインが必要 |
| 権限不足 | `403` | 権限がない |
| プレビュー上限超過 | `413` | プレビューできるサイズを超過 |
| 想定外の例外 | `500` | 処理に失敗した |

ユーザー向けレスポンスには内部パスや Python の例外内容を含めない。
詳細は構造化ログへ記録し、リクエスト ID で追跡できるようにする。

## 10. ロギングと監査

### 10.1 MVP のアプリケーションログ

JSON または key-value 形式で次の情報を記録する。

- timestamp
- request_id
- client_ip（保存方針を決めた場合のみ）
- HTTP method / route
- virtual path
- status code
- elapsed time
- error code

物理パス、パスに含まれる機密情報、Cookie、パスワード、Secret はログに
出力しない。

### 10.2 将来の操作監査ログ

認証・書き込み機能を追加する段階で、SQLite などに次を保存する。

```text
audit_logs
├── id
├── occurred_at
├── actor_id
├── action
├── relative_path
├── result
├── request_id
└── error_code
```

MVPではFilesystem の全エントリをDBへ同期しない。実ファイルが正の情報源
であり、DBは認証・権限・監査などのアプリケーションメタデータ専用とする。

## 11. 認証・権限の拡張方針

MVP は認証なしの信頼された LAN 内利用を前提とする。ただし、
`0.0.0.0` で待ち受けるため、実際の運用では以下を必須とする。

- 信頼できる LAN または VPN からのみ到達可能にする
- ルーターのポート開放を行わない
- デバッグモードを有効にしない
- 認証なしのままインターネットへ公開しない

将来認証を追加する場合は、認証（本人確認）とFilesystem権限（操作許可）を
分離する。

```text
Identity
  └── User / Group
        └── Permission
              ├── read
              ├── download
              ├── preview
              ├── upload
              └── delete
```

ユーザーごとの許可ルートは `BASE_DIR` の配下に限定し、PathResolver の
containment 検査に加えて PermissionPolicy でも検証する。認証を導入する
際には、実行環境に適した管理された認証基盤を優先し、アプリ独自の
パスワード保存を安易に追加しない。

## 12. SQLite 導入時の境界

DB を導入する場合も、次の情報だけを保存する。

```text
users
permissions
sessions または認証連携情報
audit_logs
settings
```

ファイル一覧、サイズ、更新日時をキャッシュする設計は、検索や大量ファイル
対策が必要になってから検討する。キャッシュを導入する場合も、実アクセス
時に現在の存在・パス・権限を再検証し、DBだけを信頼しない。

## 13. デプロイメント

### 13.1 LAN 内の最小構成

```text
Linux / Windows
    └── Python
          └── Flask development server
                └── 0.0.0.0:8000
                      └── read-only BASE_DIR
```

開発サーバーでの運用は、検証用またはごく小規模な LAN に限定する。

### 13.2 推奨運用構成

```text
Browser
  ▼
Nginx または Caddy（必要ならTLS/VPN境界）
  ▼
Gunicorn
  ▼
Flask Application
  ├── SQLite（将来のメタデータ）
  └── Host volume / BASE_DIR
```

コンテナ化する場合は、ファイル領域を read-only volume としてマウントする
構成を MVP の既定とし、書き込み機能を追加する時だけ必要な領域に限定して
write 権限を付与する。

Windows 対応では、パスの区切り文字を URL に漏らさず、`pathlib` と仮想
パス変換を使用する。Linux 固有の `openat` 強化はプラットフォーム別実装に
隔離する。

## 14. テスト戦略

### 14.1 Unit Test

- `BASE_DIR` 自身を解決できる
- 正常な子ディレクトリを解決できる
- `..`、絶対パス、NUL 文字を拒否できる
- プレフィックスが似た兄弟ディレクトリを拒否できる
- `BASE_DIR` 外を指す symlink を拒否できる
- 壊れた symlink を安全に扱える
- ソートキーのホワイトリストが機能する
- MIME とプレビュー可否が期待通りになる

### 14.2 Flask Integration Test

- ルート一覧が `200` を返す
- 子ディレクトリへ移動できる
- 親リンクがルートより上へ遷移しない
- ファイルをダウンロードできる
- テキスト・画像・PDFの表示方式が期待通りになる
- 不存在、拒否対象、権限不足が適切なステータスになる
- エラーレスポンスに物理パスが漏れない

### 14.3 セキュリティ回帰テスト

最低限、次の入力を毎回テストする。

```text
../
../../etc/passwd
%2e%2e%2f
/etc/passwd
..\..\Windows\System32
BASE_DIR/../sibling
BASE_DIR/link-to-outside
```

## 15. 実装フェーズ

### Phase 0 — アーキテクチャ確定

- 本書の責務と境界を合意する
- `BASE_DIR` の運用場所と利用者モデルを決める
- Python / Flask を実装ターゲットとするか確定する

### Phase 1 — 安全な読み取り専用MVP

- 設定・Application Factory
- `PathResolver`
- `FilesystemAdapter`
- ディレクトリ一覧
- 親ディレクトリ移動
- ダウンロード
- レスポンシブなHTML
- 404 / 403 / 413 / 500
- Path Traversal と symlink のテスト

### Phase 2 — 読み取り体験

- ソート
- テキスト、画像、PDFプレビュー
- 構造化ログ
- API v1 の一覧・ダウンロード
- Docker / Gunicorn の運用設定

### Phase 3 — 書き込み機能

- アップロード
- フォルダ作成
- 名前変更、移動、コピー
- サイズ制限、拡張子ポリシー、CSRF対策
- 書き込み操作の監査ログ

### Phase 4 — 認証・検索

- 管理された認証基盤との連携
- ユーザー・グループ・権限
- ファイル名検索
- 必要性が確認できた場合のみ全文検索インデックス

### Phase 5 — 高度な運用

- HTTPS / リバースプロキシ
- レート制限
- `openat` / `O_NOFOLLOW` によるTOCTOU対策
- 大量ファイル向けの非同期検索・ページネーション
- 複数のFilesystem backend

## 16. 受け入れ条件（MVP）

- 起動時に存在しない `BASE_DIR` を受け付けず、原因が分かるエラーを出す
- `BASE_DIR` 内のディレクトリとファイルを一覧表示できる
- ディレクトリ移動と親移動ができる
- 通常ファイルをダウンロードできる
- `BASE_DIR` 外への全アクセスが拒否される
- 外部 symlink のリンク先を読めない
- 物理絶対パスを画面・APIレスポンスへ出さない
- スマートフォン幅で横スクロールなしに主要操作ができる
- 上記のセキュリティ回帰テストが通過する
- LAN 内運用時の制約と、外部公開禁止の注意を README に明記する

## 17. 未決事項

実装開始前に次を決定する。

1. 実装ターゲットを仕様書どおり Python / Flask とするか
2. MVP のプレビュー対象（テキストのみか、画像・PDFまで含めるか）
3. 隠しファイルを表示するか
4. ファイル名の文字コードと不正なファイル名の表示方針
5. 想定ファイル数と一覧のページネーション要否
6. LAN の信頼境界（VPNを含むか、認証をPhase 1へ前倒しするか）
7. 将来の書き込み操作を許可するFilesystem領域
8. API を同一プロセスで提供するか、将来分離するか

これらは実装上の細部ではなく、セキュリティ境界・運用コスト・ユーザー体験
に影響するため、Phase 1 着手前に確定する。
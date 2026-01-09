# SnapLog

<p align="center">
  <strong>📸 スクリーンショットから自動で日報素材を収集するmacOSツール</strong>
</p>

<p align="center">
  毎分画面をキャプチャ → OCRでテキスト化 → ログ蓄積 → ローカルLLMで日報生成
</p>

---

## 🚧 ステータス

このリポジトリは **仕様・設計の整備が先行** しています（実装はこれから更新していきます）。

## ✨ 特徴

- **完全ローカル動作** - 外部APIへの送信なし、課金なし
- **自動バックグラウンド収集** - 起動したら放置でOK
- **プライバシー保護** - パスワードマネージャーや銀行サイトを自動除外
- **macOS標準機能活用** - Vision FrameworkでOCR、追加アプリ不要
- **ローカルLLM連携** - LM Studio / Ollamaで日報を自動生成

---

## 🎯 こんな人向け

- 日報を書くのが面倒
- 1日何をしていたか振り返りたい
- 作業ログを自動で残したい
- プライバシーを守りつつ記録したい

---

## 📋 動作環境

| 項目 | 要件 |
|------|------|
| OS | macOS Ventura (13.0) 以降 |
| Python | 3.10以上 |
| メモリ | 8GB以上推奨 |
| ストレージ | 数MB/日（テキストログのみ） |

---

## 🚀 クイックスタート

※ 現状は設計段階のため、手順・コマンドは実装に合わせて更新予定です。

### 1. インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd SnapLog

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. macOS権限設定

初回実行前に、以下の権限を付与してください：

1. **システム設定** を開く
2. **プライバシーとセキュリティ** > **画面収録**
   - Terminal（またはお使いのターミナルアプリ）を追加
3. **プライバシーとセキュリティ** > **アクセシビリティ**
   - Terminal（またはお使いのターミナルアプリ）を追加

### 3. 設定ファイルの準備

```bash
# 設定ファイルをコピー
cp config/settings.yaml.example config/settings.yaml

# 必要に応じて編集
vim config/settings.yaml
```

※ `config/settings.yaml` は個人環境用の設定ファイルです。公開リポジトリには含めない想定です。

### 4. 起動

```bash
# フォアグラウンドで実行（テスト用）
python -m src.main

# バックグラウンドで実行
./scripts/start.sh
```

### 5. 日報生成（Phase 2）

```bash
# 今日の日報を生成
python -m src.report

# 特定の日の日報を生成
python -m src.report --date 2025-01-15
```

### 6. 日報フォーマット

出力はMarkdownで、ヘッダーと以下の固定セクションで構成されます。

```markdown
# 2025-01-15 日報

## 目的
（1〜2行で、今日の目的や狙い）

## やったこと
- 目的に対して実施した内容と結果

## 学び・気づき
- 技術的な発見やハマった点と解決策

## AI出力ログ
- 有用だったAIの出力（プロンプトと回答の要約、生成コードなど）
（該当なしの場合は「（なし）」と記載）

## 次やること
- 次回のTODOや未解決事項
```

---

## ⚙️ 設定

`config/settings.yaml` で動作をカスタマイズできます：

```yaml
# キャプチャ間隔（秒）
capture:
  interval: 60
  mode: "fullscreen"

# 除外するアプリ
filter:
  exclude_apps:
    - "1Password"
    - "Keychain Access"
  
  # 除外するウィンドウタイトル（部分一致）
  exclude_title_keywords:
    - "銀行"
    - "クレジットカード"

# ローカルLLM設定
llm:
  endpoint: "http://localhost:1234/v1/chat/completions"
  model: "llama3.2"

# 保存ポリシー（推奨）
storage:
  retention_days: 14
```

詳細は `snaplog-architecture.md` の「settings.yaml」を参照してください。

---

## 📁 ディレクトリ構成

```
SnapLog/
├── src/
│   ├── main.py           # エントリーポイント
│   ├── capture.py        # スクリーンキャプチャ
│   ├── ocr.py            # Vision Framework OCR
│   ├── filter.py         # 除外フィルタ
│   ├── storage.py        # JSONL保存
│   ├── report.py         # 日報生成
│   └── config.py         # 設定管理
├── config/
│   └── settings.yaml     # 設定ファイル
├── scripts/
│   ├── start.sh          # 起動スクリプト
│   ├── stop.sh           # 停止スクリプト
│   └── generate_report.sh
├── tests/
├── requirements.txt
└── README.md
```

### データ保存先

```
~/Documents/SnapLog/
├── logs/                 # 日次ログ（JSONL）
│   └── activity_log_2025-01-15.jsonl
└── reports/              # 生成された日報
    └── report_2025-01-15.md
```

---

## 🔧 コマンド一覧

| コマンド | 説明 |
|----------|------|
| `./scripts/start.sh` | バックグラウンドで起動 |
| `./scripts/stop.sh` | 停止 |
| `python -m src.main` | フォアグラウンドで起動 |
| `python -m src.report` | 今日の日報を生成 |
| `python -m src.report --date YYYY-MM-DD` | 指定日の日報を生成 |

---

## 🤖 ローカルLLM設定

日報生成には、ローカルLLMが必要です。以下のいずれかをセットアップしてください：

### LM Studio（GUI、初心者向け）

1. [LM Studio](https://lmstudio.ai/) をダウンロード
2. アプリを起動し、モデルをダウンロード（推奨: `llama3.2` または `elyza:jp8b`）
3. 左メニュー「Local Server」→「Start Server」
4. `settings.yaml` の `llm.endpoint` を `http://localhost:1234/v1/chat/completions` に設定

### Ollama（CLI、上級者向け）

```bash
# インストール
brew install ollama

# モデルをダウンロード
ollama pull llama3.2

# サーバー起動
ollama serve
```

`settings.yaml` の `llm.endpoint` を `http://localhost:11434/v1/chat/completions` に設定

---

## 🛡️ プライバシー

SnapLogはプライバシーを重視して設計されています：

- **ローカル完結** - すべての処理はMac内で完結。外部サーバーへの送信なし
- **画像即削除** - スクリーンショットはOCR後に即削除
- **除外機能** - パスワードマネージャー、銀行サイト等を自動除外
- **パターンマッチ** - クレカ番号、電話番号等をOCR結果から検出して除外
- **注意（MVPのキャプチャ範囲）** - `capture.mode=fullscreen` の場合、背面ウィンドウの情報が混入し得ます（将来的に `active_window` を追加予定）

---

## 🗺️ ロードマップ

- [ ] Phase 1: 素材収集（MVP）
  - [ ] スクリーンキャプチャ（デフォルト: fullscreen）
  - [ ] アクティブウィンドウ情報取得
  - [ ] Vision Framework OCR
  - [ ] JSONL保存
  - [ ] 基本フィルタ（アプリ名/タイトル/パターン）

- [ ] Phase 2: 日報生成
  - [ ] ログ前処理（グルーピング/圧縮/分割）
  - [ ] ローカルLLM連携（OpenAI互換エンドポイント）
  - [ ] 日報テンプレート/Markdown出力

- [ ] Phase 3: 改善
  - [ ] キャプチャ範囲の改善（active_window等）
  - [ ] メニューバーUI（停止/一時停止/状態表示）
  - [ ] フィルタ強化（許可リスト運用、精度改善）

---

## 📄 ログ形式

各ログエントリは以下の形式で保存されます：

```json
{
  "timestamp": "2025-01-15T14:32:00+09:00",
  "app_name": "Cursor",
  "window_title": "main.py - MyProject",
  "ocr_text": "def capture_screen():...",
  "ocr_length": 1234
}
```

---

## 🐛 トラブルシューティング

### 権限エラーが出る

```
Error: Screen capture failed
```

→ システム設定 > プライバシーとセキュリティ > 画面収録 で実行アプリ（Terminal等）を許可してください

### OCRが動作しない

```
Error: Vision Framework initialization failed
```

→ macOS Ventura以降が必要です。OSバージョンを確認してください

### LLMに接続できない

```
Error: Connection refused to localhost:1234
```

→ LM StudioまたはOllamaが起動しているか確認してください

### launchd等の自動起動で権限が効かない

→ 画面収録/アクセシビリティは「どのアプリから実行したか」に依存します。Terminalで許可しても、launchd配下の実行では別扱いになる場合があります。まずは `./scripts/start.sh`（Terminal起動）で動作確認し、安定した自動起動は `snaplog-architecture.md` の起動・停止方針に従ってください。

---

## 🤝 コントリビューション

バグ報告や機能リクエストはリポジトリのIssuesへお願いします。

---

## 📜 ライセンス

MIT License

---

## 🙏 謝辞

このツールは、日々の作業振り返りを楽にしたいというニーズから着想しています。

---

<p align="center">
  Made with ☕ by BOSS
</p>

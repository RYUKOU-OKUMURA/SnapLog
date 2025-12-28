# SnapLog

<p align="center">
  <strong>📸 スクリーンショットから自動で日報素材を収集するmacOSツール</strong>
</p>

<p align="center">
  毎分画面をキャプチャ → OCRでテキスト化 → ログ蓄積 → ローカルLLMで日報生成
</p>

---

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

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/snaplog.git
cd snaplog

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

### 4. 起動

```bash
# フォアグラウンドで実行（テスト用）
python src/main.py

# バックグラウンドで実行
./scripts/start.sh
```

### 5. 日報生成（Phase 2）

```bash
# 今日の日報を生成
python src/report.py

# 特定の日の日報を生成
python src/report.py --date 2025-01-15
```

---

## ⚙️ 設定

`config/settings.yaml` で動作をカスタマイズできます：

```yaml
# キャプチャ間隔（秒）
capture:
  interval: 60

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
```

詳細は [設定リファレンス](docs/configuration.md) を参照してください。

---

## 📁 ディレクトリ構成

```
snaplog/
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
| `python src/main.py` | フォアグラウンドで起動 |
| `python src/report.py` | 今日の日報を生成 |
| `python src/report.py --date YYYY-MM-DD` | 指定日の日報を生成 |

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

---

## 🗺️ ロードマップ

- [x] Phase 1: 素材収集（MVP）
  - [x] スクリーンキャプチャ
  - [x] Vision Framework OCR
  - [x] JSONL保存
  - [x] アプリ名による除外

- [ ] Phase 2: 日報生成
  - [ ] ローカルLLM連携
  - [ ] 日報テンプレート
  - [ ] Markdown出力

- [ ] Phase 3: 改善
  - [ ] ウィンドウタイトルによる除外
  - [ ] OCRパターンによる除外
  - [ ] メニューバーUI

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

→ システム設定 > プライバシー > 画面収録 でTerminalを許可してください

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

---

## 🤝 コントリビューション

バグ報告や機能リクエストは [Issues](https://github.com/yourusername/snaplog/issues) へお願いします。

---

## 📜 ライセンス

MIT License

---

## 🙏 謝辞

このツールは、Xで見かけた[@username](https://x.com/username)さんのアイデアにインスパイアされて作成しました。

---

<p align="center">
  Made with ☕ by BOSS
</p>

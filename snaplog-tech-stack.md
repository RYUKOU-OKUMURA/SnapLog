# SnapLog 技術スタック詳細

## 1. 技術スタック概要

```
┌─────────────────────────────────────────────────────────────────┐
│                        アプリケーション層                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Python 3.10+                                             │  │
│  │  - main.py（エントリーポイント）                            │  │
│  │  - 各種モジュール                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        ライブラリ層                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │   pyobjc    │ │   PyYAML    │ │  requests   │              │
│  │  (Vision)   │ │  (設定管理)  │ │ (LLM連携)   │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                        macOS API層                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │screencapture│ │ AppleScript │ │   Vision    │              │
│  │  (CLI)      │ │ (osascript) │ │ Framework   │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                        外部サービス層                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ローカルLLM（LM Studio / Ollama）                       │   │
│  │  - REST API（localhost）                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                           OS層                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  macOS Ventura (13.0) 以降                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 言語・ランタイム

### 2.1 Python

| 項目 | 内容 |
|------|------|
| バージョン | 3.10以上（3.11推奨） |
| 理由 | pyobjcの互換性、型ヒント、match文対応 |
| インストール | Homebrew推奨 |

**インストール方法**
```bash
# Homebrewでインストール
brew install python@3.11

# バージョン確認
python3 --version
# Python 3.11.x

# pipアップグレード
python3 -m pip install --upgrade pip
```

**仮想環境（推奨）**
```bash
# venv作成
python3 -m venv venv

# 有効化
source venv/bin/activate

# 無効化
deactivate
```

### 2.2 なぜPythonか

| 観点 | 評価 |
|------|------|
| macOS API連携 | ◎ pyobjcで直接アクセス可能 |
| 開発速度 | ◎ スクリプト言語で素早く開発 |
| LLM連携 | ◎ requestsで簡単にAPI呼び出し |
| 学習コスト | ◎ BOSSさんに馴染みあり |
| 実行速度 | △ 毎分1回なので問題なし |

---

## 3. Pythonライブラリ

### 3.1 依存関係一覧

```
# requirements.txt
pyobjc-framework-Vision>=10.0
pyobjc-framework-Quartz>=10.0
pyobjc-core>=10.0
PyYAML>=6.0
requests>=2.31.0
```

### 3.2 各ライブラリ詳細

#### pyobjc-framework-Vision

| 項目 | 内容 |
|------|------|
| 用途 | macOS Vision FrameworkをPythonから利用 |
| 主な機能 | OCR（テキスト認識） |
| バージョン | 10.0以上 |
| ドキュメント | https://pyobjc.readthedocs.io/ |

**使用例**
```python
import Vision
from Quartz import CIImage

def extract_text(image_path: str) -> str:
    # 画像読み込み
    image = CIImage.imageWithContentsOfURL_(
        Foundation.NSURL.fileURLWithPath_(image_path)
    )
    
    # リクエスト作成
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(["ja-JP", "en-US"])
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    
    # 実行
    handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
        image, None
    )
    handler.performRequests_error_([request], None)
    
    # 結果取得
    results = request.results()
    text = "\n".join([obs.topCandidates_(1)[0].string() for obs in results])
    
    return text
```

#### pyobjc-framework-Quartz

| 項目 | 内容 |
|------|------|
| 用途 | 画像処理（CIImage等） |
| 主な機能 | 画像の読み込み・変換 |
| バージョン | 10.0以上 |
| 備考 | Vision Frameworkと併用 |

#### pyobjc-core

| 項目 | 内容 |
|------|------|
| 用途 | pyobjcのコアライブラリ |
| 主な機能 | Objective-Cブリッジ |
| バージョン | 10.0以上 |
| 備考 | 自動的にインストールされる |

#### PyYAML

| 項目 | 内容 |
|------|------|
| 用途 | 設定ファイル（YAML）の読み書き |
| 主な機能 | YAML解析・シリアライズ |
| バージョン | 6.0以上 |
| ドキュメント | https://pyyaml.org/ |

**使用例**
```python
import yaml

# 読み込み
with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

# 書き込み
with open("config/settings.yaml", "w") as f:
    yaml.dump(config, f, allow_unicode=True)
```

#### requests

| 項目 | 内容 |
|------|------|
| 用途 | ローカルLLMへのHTTPリクエスト |
| 主な機能 | REST API呼び出し |
| バージョン | 2.31.0以上 |
| ドキュメント | https://requests.readthedocs.io/ |

**使用例**
```python
import requests

# LM Studioへのリクエスト
response = requests.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "local-model",
        "messages": [
            {"role": "user", "content": "日報を作成してください"}
        ]
    }
)

result = response.json()
```

### 3.3 オプションライブラリ

| ライブラリ | 用途 | 必要なフェーズ |
|-----------|------|---------------|
| rumps | メニューバーUI | Phase 3 |
| schedule | タスクスケジューリング | 代替手段 |
| rich | ターミナル出力装飾 | 開発時 |
| pytest | テスト | 開発時 |

---

## 4. macOS システムAPI

### 4.1 screencapture（コマンドライン）

| 項目 | 内容 |
|------|------|
| 用途 | スクリーンショット撮影 |
| 種別 | macOS標準コマンド |
| 場所 | /usr/sbin/screencapture |

**オプション一覧**

| オプション | 説明 |
|-----------|------|
| -x | 撮影音を無効化 |
| -C | カーソルを含める |
| -T <秒> | 遅延撮影 |
| -t <形式> | 出力形式（png, jpg, pdf等） |
| -R <x,y,w,h> | 指定領域のみ撮影 |
| -D <番号> | 特定ディスプレイのみ |

**capture.mode との関係（設計）**

- `fullscreen`（MVP）: `screencapture -x` で画面全体を撮影してOCR→即削除
- `active_window`（拡張）: Quartzで前面ウィンドウID/座標を取得し、`-l <windowid>` や `-R <x,y,w,h>`（クロップ）で前面ウィンドウのみを撮影して、背面ウィンドウの混入リスクを下げる

**使用例**
```python
import subprocess

def take_screenshot(output_path: str) -> bool:
    """
    画面全体をキャプチャ
    
    Args:
        output_path: 保存先パス
        
    Returns:
        bool: 成功したらTrue
    """
    result = subprocess.run(
        ["screencapture", "-x", output_path],
        capture_output=True
    )
    return result.returncode == 0
```

### 4.2 AppleScript / osascript

| 項目 | 内容 |
|------|------|
| 用途 | ウィンドウ情報取得 |
| 種別 | macOS標準スクリプト環境 |
| 実行 | osascriptコマンド経由 |

**アクティブアプリ名取得**
```python
import subprocess

def get_active_app() -> str:
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
    end tell
    return frontApp
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()
```

**ウィンドウタイトル取得**
```python
def get_window_title() -> str:
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        try
            set windowTitle to name of front window of frontApp
        on error
            set windowTitle to ""
        end try
    end tell
    return windowTitle
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()
```

### 4.3 Vision Framework

| 項目 | 内容 |
|------|------|
| 用途 | OCR（テキスト認識） |
| 種別 | macOSネイティブフレームワーク |
| アクセス | pyobjc経由 |
| 対応言語 | 日本語、英語、中国語、他多数 |

**対応言語コード（主要）**

| 言語 | コード |
|------|--------|
| 日本語 | ja-JP |
| 英語 | en-US |
| 中国語（簡体） | zh-Hans |
| 中国語（繁体） | zh-Hant |
| 韓国語 | ko-KR |

**認識レベル**

| レベル | 説明 | 用途 |
|--------|------|------|
| VNRequestTextRecognitionLevelAccurate | 高精度（遅い） | 本番用 |
| VNRequestTextRecognitionLevelFast | 高速（精度低） | テスト用 |

---

## 5. ローカルLLM

### 5.1 選択肢比較

| 項目 | LM Studio | Ollama |
|------|-----------|--------|
| GUI | ◎ あり | × なし |
| インストール | アプリDL | brew install |
| モデル管理 | GUIで検索・DL | コマンドでpull |
| API | OpenAI互換 | 独自 + OpenAI互換 |
| メモリ管理 | 自動 | 自動 |
| おすすめ度 | 初心者向け | CLI慣れてる人向け |

### 5.2 LM Studio

**インストール**
1. https://lmstudio.ai/ からダウンロード
2. アプリケーションフォルダに配置
3. 起動してモデルをダウンロード

**APIサーバー起動**
1. LM Studio起動
2. 左メニュー「Local Server」選択
3. 「Start Server」クリック
4. デフォルト: http://localhost:1234

**API仕様（OpenAI互換）**

```
エンドポイント: POST http://localhost:1234/v1/chat/completions

リクエスト:
{
  "model": "local-model",
  "messages": [
    {"role": "system", "content": "システムプロンプト"},
    {"role": "user", "content": "ユーザーメッセージ"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}

レスポンス:
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "生成されたテキスト"
      }
    }
  ]
}
```

**Pythonでの呼び出し**
```python
import requests

def call_lm_studio(prompt: str) -> str:
    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "local-model",
            "messages": [
                {
                    "role": "system",
                    "content": "あなたは日報作成アシスタントです。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

### 5.3 Ollama

**インストール**
```bash
# Homebrew
brew install ollama

# または公式サイトからダウンロード
# https://ollama.ai/
```

**基本コマンド**
```bash
# サーバー起動
ollama serve

# モデルダウンロード
ollama pull llama3.2
ollama pull gemma2
ollama pull elyza:jp8b  # 日本語特化

# モデル一覧
ollama list

# 対話モード
ollama run llama3.2
```

**API仕様（独自）**

```
エンドポイント: POST http://localhost:11434/api/generate

リクエスト:
{
  "model": "llama3.2",
  "prompt": "プロンプト",
  "stream": false
}

レスポンス:
{
  "response": "生成されたテキスト",
  "done": true
}
```

**OpenAI互換API（推奨）**
```
エンドポイント: POST http://localhost:11434/v1/chat/completions

※ LM Studioと同じ形式で使用可能
```

**Pythonでの呼び出し**
```python
import requests

def call_ollama(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": "あなたは日報作成アシスタントです。"},
                {"role": "user", "content": prompt},
            ],
        },
    )
    return response.json()["choices"][0]["message"]["content"]

# または公式ライブラリ
# pip install ollama
import ollama

response = ollama.generate(
    model="llama3.2",
    prompt=prompt
)
print(response["response"])
```

### 5.4 推奨モデル

| 用途 | モデル | サイズ | 備考 |
|------|--------|--------|------|
| 汎用 | llama3.2 | 3B/8B | バランス良い |
| 日本語特化 | elyza:jp8b | 8B | 日本語精度高い |
| 軽量 | gemma2:2b | 2B | メモリ少ない環境向け |
| 高性能 | qwen2.5:14b | 14B | 精度重視 |

**日報生成のおすすめ**: llama3.2:8b または elyza:jp8b

---

## 6. データフォーマット

### 6.1 JSONL（ログファイル）

| 項目 | 内容 |
|------|------|
| 形式 | JSON Lines（1行1JSON） |
| 拡張子 | .jsonl |
| エンコーディング | UTF-8 |
| 改行 | LF（\n） |

**スキーマ**
```json
{
  "timestamp": "2025-01-15T14:32:00+09:00",  // ISO 8601形式
  "app_name": "Cursor",                       // アプリケーション名
  "window_title": "main.py - MyProject",      // ウィンドウタイトル
  "ocr_text": "def capture_screen():...",     // OCR結果
  "ocr_length": 1234                          // OCRテキストの文字数
}
```

**読み書き例**
```python
import json
from datetime import datetime

# 書き込み（追記）
def append_log(log_entry: dict, filepath: str):
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

# 読み込み
def read_logs(filepath: str) -> list[dict]:
    logs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            logs.append(json.loads(line))
    return logs
```

### 6.2 YAML（設定ファイル）

| 項目 | 内容 |
|------|------|
| 形式 | YAML 1.2 |
| 拡張子 | .yaml |
| エンコーディング | UTF-8 |

**読み込み例**
```python
import yaml

def load_config(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
```

### 6.3 Markdown（日報）

| 項目 | 内容 |
|------|------|
| 形式 | CommonMark |
| 拡張子 | .md |
| エンコーディング | UTF-8 |

---

## 7. 開発環境

### 7.1 推奨エディタ

| エディタ | 備考 |
|----------|------|
| Cursor | BOSSさん愛用、AI補完あり |
| VS Code | 拡張機能豊富 |
| PyCharm | Python特化 |

### 7.2 推奨拡張機能（Cursor/VS Code）

| 拡張機能 | 用途 |
|----------|------|
| Python | Python言語サポート |
| Pylance | 型チェック・補完 |
| YAML | YAML編集サポート |
| Ruff | リンター（高速） |

### 7.3 コード品質ツール

```bash
# リンター＆フォーマッター
pip install ruff

# 実行
ruff check src/
ruff format src/

# 型チェック
pip install mypy
mypy src/
```

### 7.4 テストフレームワーク

```bash
pip install pytest pytest-cov

# テスト実行
pytest tests/

# カバレッジ付き
pytest --cov=src tests/
```

---

## 8. 実行環境

### 8.1 必要なmacOS権限

| 権限 | 必要性 | 設定場所 |
|------|--------|---------|
| 画面収録 | 必須 | システム設定 > プライバシーとセキュリティ > 画面収録 |
| アクセシビリティ | 必須 | システム設定 > プライバシーとセキュリティ > アクセシビリティ |

**権限付与手順**
1. システム設定を開く
2. プライバシーとセキュリティ > 画面収録
3. Terminalまたはスクリプト実行アプリを追加
4. 同様にアクセシビリティにも追加
5. 再起動（必要に応じて）

### 8.2 プロセス管理

**方法1: フォアグラウンド実行**
```bash
python -m src.main
# Ctrl+C で停止
```

**方法2: バックグラウンド実行**
```bash
# 起動
nohup python -m src.main > /dev/null 2>&1 &
echo $! > .pid

# 停止
kill $(cat .pid)
```

**方法3: launchd（自動起動）**

> 注意: 画面収録/アクセシビリティは「どのアプリとして実行したか」に依存します。Terminalで許可しても、launchd配下の実行で権限が再度必要になる場合があります。安定運用の方針は `snaplog-architecture.md` を参照してください。

```bash
# plistを配置
cp com.user.snaplog.plist ~/Library/LaunchAgents/

# 読み込み
launchctl load ~/Library/LaunchAgents/com.user.snaplog.plist

# 停止
launchctl unload ~/Library/LaunchAgents/com.user.snaplog.plist
```

---

## 9. バージョン管理

### 9.1 .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp

# プロジェクト固有
.pid
*.log
logs/
reports/

# macOS
.DS_Store

# 一時ファイル
/tmp/
*.png
```

---

## 10. セットアップ手順まとめ

```bash
# 1. リポジトリクローン
git clone <repository-url>
cd SnapLog

# 2. Python仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 3. 依存関係インストール
pip install -r requirements.txt

# 4. 設定ファイルコピー
cp config/settings.yaml.example config/settings.yaml
# 必要に応じて編集

# 5. macOS権限設定
# システム設定 > プライバシーとセキュリティ > 画面収録 で実行アプリを許可
# システム設定 > プライバシーとセキュリティ > アクセシビリティ で実行アプリを許可

# 6. 動作確認
python -m src.main

# 7. （オプション）LM Studioまたは Ollama起動
# LM Studio: アプリ起動 → Local Server → Start
# Ollama: ollama serve
```

---

*作成日: 2025年1月*
*バージョン: 1.0*

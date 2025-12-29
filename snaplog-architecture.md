# SnapLog アーキテクチャ設計書

## 1. システム全体像

### 1.1 アーキテクチャ概要

```
┌────────────────────────────────────────────────────────────────────┐
│                         macOS                                      │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                       SnapLog                                │  │
│  │                                                              │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │  │
│  │  │   Capture   │───▶│   Filter    │───▶│   Storage   │      │  │
│  │  │   Module    │    │   Module    │    │   Module    │      │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘      │  │
│  │         │                                     │              │  │
│  │         ▼                                     ▼              │  │
│  │  ┌─────────────┐                      ┌─────────────┐       │  │
│  │  │  macOS API  │                      │    JSONL    │       │  │
│  │  │ - screencap │                      │    Files    │       │  │
│  │  │ - AppleScript│                     └─────────────┘       │  │
│  │  │ - Vision    │                             │              │  │
│  │  └─────────────┘                             ▼              │  │
│  │                                       ┌─────────────┐       │  │
│  │                                       │   Report    │       │  │
│  │                                       │  Generator  │       │  │
│  │                                       └─────────────┘       │  │
│  │                                              │              │  │
│  │                                              ▼              │  │
│  │                                       ┌─────────────┐       │  │
│  │                                       │ Local LLM   │       │  │
│  │                                       │ (LM Studio/ │       │  │
│  │                                       │  Ollama)    │       │  │
│  │                                       └─────────────┘       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 処理フロー

```
[起動]
   │
   ▼
[設定ファイル読み込み]
   │
   ▼
[メインループ開始]◀──────────────────┐
   │                                │
   ▼                                │
[アクティブウィンドウ情報取得]        │
   │                                │
   ▼                                │
[除外判定①: アプリ名]                │
   │                                │
   ├─ 除外対象 ──▶ [スキップ] ───────┤
   │                                │
   ▼                                │
[除外判定②: ウィンドウタイトル]       │
   │                                │
   ├─ 除外対象 ──▶ [スキップ] ───────┤
   │                                │
   ▼                                │
[スクリーンキャプチャ]               │
   │                                │
   ▼                                │
[OCR処理]                           │
   │                                │
   ▼                                │
[除外判定③: OCR結果]                 │
   │                                │
   ├─ 除外対象 ──▶ [スキップ] ───────┤
   │                                │
   ▼                                │
[JSONLに保存]                        │
   │                                │
   ▼                                │
[画像削除]                           │
   │                                │
   ▼                                │
[インターバル待機] ─────────────────┘
```

---

## 2. ディレクトリ構成

### 2.1 プロジェクト構造

```
SnapLog/
├── src/
│   ├── __init__.py
│   ├── main.py                 # エントリーポイント
│   ├── capture.py              # キャプチャモジュール
│   ├── ocr.py                  # OCRモジュール
│   ├── filter.py               # 除外フィルタモジュール
│   ├── storage.py              # ログ保存モジュール
│   ├── report.py               # 日報生成モジュール（Phase 2）
│   └── config.py               # 設定管理モジュール
├── config/
│   └── settings.yaml           # 設定ファイル
├── scripts/
│   ├── start.sh                # 起動スクリプト
│   ├── stop.sh                 # 停止スクリプト
│   └── generate_report.sh      # 日報生成スクリプト
├── tests/
│   ├── test_capture.py
│   ├── test_ocr.py
│   ├── test_filter.py
│   └── test_storage.py
├── requirements.txt
├── README.md
└── .gitignore
```

### 2.2 データ保存構造

```
~/Documents/SnapLog/
├── logs/
│   ├── activity_log_2025-01-13.jsonl
│   ├── activity_log_2025-01-14.jsonl
│   └── activity_log_2025-01-15.jsonl
├── reports/
│   ├── report_2025-01-13.md
│   ├── report_2025-01-14.md
│   └── report_2025-01-15.md
└── config/
    └── settings.yaml           # ユーザー設定（オプション）
```

---

## 3. モジュール設計

### 3.1 main.py（エントリーポイント）

**責務**
- アプリケーションの起動・終了
- メインループの制御
- シグナルハンドリング（Ctrl+C等）

**フロー**
```python
def main():
    config = load_config()
    
    while running:
        try:
            # 1. ウィンドウ情報取得
            window_info = capture.get_active_window()
            
            # 2. 除外判定（アプリ名・タイトル）
            if filter.should_exclude_pre_capture(window_info, config):
                continue
            
            # 3. スクリーンキャプチャ
            image_path = capture.take_screenshot()
            
            # 4. OCR処理
            ocr_text = ocr.extract_text(image_path)
            
            # 5. 除外判定（OCR結果）
            if filter.should_exclude_post_capture(ocr_text, config):
                capture.delete_image(image_path)
                continue
            
            # 6. ログ保存
            storage.save_log(window_info, ocr_text)
            
            # 7. 画像削除
            capture.delete_image(image_path)
            
        except Exception as e:
            logger.error(f"Error: {e}")
        
        # 8. インターバル待機
        time.sleep(config.interval)
```

### 3.2 capture.py（キャプチャモジュール）

**責務**
- スクリーンショット撮影
- アクティブウィンドウ情報取得
- 一時画像ファイルの削除

**インターフェース**
```python
class CaptureModule:
    def get_active_window() -> WindowInfo:
        """
        アクティブウィンドウの情報を取得
        
        Returns:
            WindowInfo: {
                "app_name": str,      # アプリ名（例: "Cursor"）
                "window_title": str   # ウィンドウタイトル
            }
        """
        pass
    
    def take_screenshot() -> str:
        """
        スクリーンショットを撮影
        （`settings.yaml` の `capture.mode` に従って fullscreen / active_window を切り替える想定）
        
        Returns:
            str: 一時保存した画像のパス（/tmp/screenshot_xxx.png）
        """
        pass
    
    def delete_image(path: str) -> None:
        """
        画像ファイルを削除
        """
        pass
```

**内部実装**
```
get_active_window():
  └─ AppleScript実行
      └─ osascript -e 'tell application "System Events" to ...'

take_screenshot():
  ├─ fullscreenモード: subprocess.run(["screencapture", "-x", path])
  └─ active_windowモード: 
      ├─ ウィンドウID取得（AppleScript）
      └─ subprocess.run(["screencapture", "-x", "-l", window_id, path])
  
複数モニター環境での挙動:
- fullscreenモード: メインディスプレイ全体をキャプチャ
- active_windowモード: アクティブウィンドウが存在するディスプレイに関係なく、そのウィンドウのみをキャプチャ
```

### 3.3 ocr.py（OCRモジュール）

**責務**
- Vision Frameworkを使ったテキスト抽出
- 日本語・英語の認識

**インターフェース**
```python
class OCRModule:
    def extract_text(image_path: str) -> str:
        """
        画像からテキストを抽出
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            str: 抽出されたテキスト
        """
        pass
```

**内部実装**
```
extract_text():
  └─ pyobjc-framework-Vision
      ├─ VNRecognizeTextRequest
      ├─ VNImageRequestHandler
      └─ supportedRecognitionLanguages: ["ja-JP", "en-US"]
```

### 3.4 filter.py（除外フィルタモジュール）

**責務**
- アプリ名による除外判定
- ウィンドウタイトルによる除外判定
- OCR結果による除外判定（正規表現）

**インターフェース**
```python
class FilterModule:
    def should_exclude_pre_capture(window_info: WindowInfo, config: Config) -> bool:
        """
        キャプチャ前の除外判定（アプリ名・タイトル）
        
        Returns:
            bool: True = 除外する
        """
        pass
    
    def should_exclude_post_capture(ocr_text: str, config: Config) -> bool:
        """
        キャプチャ後の除外判定（OCR結果）
        
        Returns:
            bool: True = 除外する
        """
        pass
```

**除外パターン例**
```yaml
# アプリ名
exclude_apps:
  - "1Password"
  - "Keychain Access"
  - "キーチェーンアクセス"

# ウィンドウタイトル（部分一致）
exclude_title_keywords:
  - "銀行"
  - "クレジットカード"
  - "Credit Card"
  - "パスワード"

# OCR結果（正規表現）
exclude_patterns:
  - '\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}'  # クレカ番号
  - '\d{3}-\d{4}-\d{4}'                        # 電話番号
  - '\d{3}-\d{4}'                              # 郵便番号
```

### 3.5 storage.py（ストレージモジュール）

**責務**
- JSONLファイルへのログ追記
- 日付別ファイル管理
- ディレクトリの自動作成

**インターフェース**
```python
class StorageModule:
    def save_log(window_info: WindowInfo, ocr_text: str) -> None:
        """
        ログをJSONLファイルに保存
        
        ファイル名: activity_log_YYYY-MM-DD.jsonl
        """
        pass
    
    def get_today_logs() -> list[LogEntry]:
        """
        今日のログを取得
        """
        pass
    
    def get_logs_by_date(date: str) -> list[LogEntry]:
        """
        指定日のログを取得
        """
        pass

    def cleanup_old_files(retention_days: int) -> None:
        """
        古いログ/レポートを削除（リテンション）
        """
        pass
```

**JSONLレコード構造**
```json
{
  "timestamp": "2025-01-15T14:32:00+09:00",
  "app_name": "Cursor",
  "window_title": "main.py - MyProject",
  "ocr_text": "def capture_screen():...",
  "ocr_length": 1234
}
```

### 3.6 config.py（設定管理モジュール）

**責務**
- 設定ファイル（YAML）の読み込み
- デフォルト値の管理
- 設定値のバリデーション

**インターフェース**
```python
@dataclass
class Config:
    interval: int                    # キャプチャ間隔（秒）
    capture_mode: str                # キャプチャ方式（fullscreen / active_window）
    temp_dir: str                    # 一時ファイル保存先
    log_dir: str                     # ログ保存先
    report_dir: str                  # レポート保存先
    retention_days: int              # 保持日数（ログ/レポート）
    exclude_apps: list[str]          # 除外アプリ
    exclude_title_keywords: list[str] # 除外タイトルキーワード
    exclude_patterns: list[str]      # 除外正規表現
    llm_endpoint: str                # LLMのエンドポイント
    llm_model: str                   # LLMモデル名
    report_group_gap_minutes: int    # セッション分割の閾値
    report_chunk_chars: int          # LLM投入用の分割サイズ

def load_config(path: str = None) -> Config:
    """設定ファイルを読み込み"""
    pass
```

### 3.7 report.py（日報生成モジュール）- Phase 2

**責務**
- ログの読み込みと整形
- 入力のグルーピング/分割/圧縮（LLM投入サイズの制御）
- ローカルLLMへのリクエスト
- Markdown日報の生成・保存

**インターフェース**
```python
class ReportModule:
    def generate_report(date: str = None) -> str:
        """
        日報を生成
        
        Args:
            date: 対象日（省略時は今日）
            
        Returns:
            str: 生成された日報（Markdown）
        """
        pass
    
    def save_report(report: str, date: str) -> str:
        """
        日報をファイルに保存
        
        Returns:
            str: 保存先パス
        """
        pass
```

---

## 4. 設定ファイル

### 4.1 settings.yaml

```yaml
# SnapLog 設定ファイル

# ===== 基本設定 =====
capture:
  interval: 60                    # キャプチャ間隔（秒）
  mode: "fullscreen"              # fullscreen（MVP） / active_window（拡張）
  temp_dir: "/tmp"                # 一時ファイル保存先

# ===== 保存先 =====
storage:
  base_dir: "~/Documents/SnapLog"
  log_subdir: "logs"
  report_subdir: "reports"
  retention_days: 14              # 保持日数
  cleanup_on_start: true          # 起動時に古いファイルを削除

# ===== 除外設定 =====
filter:
  # 除外するアプリ名（完全一致）
  exclude_apps:
    - "1Password"
    - "1Password 7"
    - "Keychain Access"
    - "キーチェーンアクセス"
    - "Bitwarden"
  
  # 除外するウィンドウタイトル（部分一致）
  exclude_title_keywords:
    - "銀行"
    - "Bank"
    - "クレジットカード"
    - "Credit Card"
    - "パスワード"
    - "Password"
    - "ログイン"
    - "Sign in"
  
  # 除外するOCRパターン（正規表現）
  exclude_patterns:
    # クレジットカード番号（4桁×4）
    - '\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}'
    # 電話番号
    - '\d{2,4}-\d{2,4}-\d{4}'
    # マイナンバー
    - '\d{4}[-\s]?\d{4}[-\s]?\d{4}'

# ===== LLM設定（Phase 2）=====
llm:
  # LM Studioの場合
  endpoint: "http://localhost:1234/v1/chat/completions"
  # Ollamaの場合
  # endpoint: "http://localhost:11434/v1/chat/completions"
  model: "llama3.2"
  max_tokens: 2000

# ===== 日報生成（Phase 2）=====
report:
  group_gap_minutes: 10           # 10分以上の空きでセッション分割
  chunk_chars: 12000              # LLM投入用の分割（概算）

# ===== ログ設定 =====
logging:
  level: "INFO"                   # DEBUG, INFO, WARNING, ERROR
  file: "~/Documents/SnapLog/app.log"
```

---

## 5. 外部インターフェース

### 5.1 macOS API

| API | 用途 | 呼び出し方法 |
|-----|------|-------------|
| screencapture | スクリーンショット | subprocess |
| AppleScript | ウィンドウ情報取得 | subprocess + osascript |
| Vision Framework | OCR | pyobjc |

### 5.2 AppleScript詳細

**アクティブアプリ名取得**
```applescript
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
end tell
return frontApp
```

**ウィンドウタイトル取得**
```applescript
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set windowTitle to name of front window of frontApp
end tell
return windowTitle
```

### 5.3 ローカルLLM API

**LM Studio（OpenAI互換）**
```
POST http://localhost:1234/v1/chat/completions
Content-Type: application/json

{
  "model": "local-model",
  "messages": [
    {"role": "system", "content": "あなたは日報作成アシスタントです。"},
    {"role": "user", "content": "以下のログから日報を作成してください:\n..."}
  ]
}
```

**Ollama**
```
POST http://localhost:11434/v1/chat/completions
Content-Type: application/json

{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "あなたは日報作成アシスタントです。"},
    {"role": "user", "content": "以下のログから日報を作成してください:\n..."}
  ]
}
```

---

## 6. エラーハンドリング

### 6.1 エラー種別と対応

| エラー | 対応 | 継続 |
|--------|------|------|
| スクショ失敗 | ログ出力、スキップ | ○ |
| AppleScript失敗 | ログ出力、スキップ | ○ |
| OCR失敗 | ログ出力、スキップ | ○ |
| ファイル書き込み失敗 | ログ出力、リトライ | ○ |
| 設定ファイル読み込み失敗 | デフォルト値使用 | ○ |
| LLM接続失敗 | エラー表示、終了 | × |

### 6.2 ロギング

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

---

## 7. 起動・停止

### 7.1 起動スクリプト（start.sh）

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
nohup python src/main.py > /dev/null 2>&1 &
echo $! > .pid
echo "SnapLog started with PID: $(cat .pid)"
```

### 7.2 停止スクリプト（stop.sh）

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
if [ -f .pid ]; then
    kill $(cat .pid)
    rm .pid
    echo "SnapLog stopped"
else
    echo "SnapLog is not running"
fi
```

### 7.3 launchd（自動起動）- オプション

> 注意: 画面収録/アクセシビリティは「どのアプリとして実行したか」に依存します。Terminalで許可しても、launchd配下の実行で権限が再度必要になる場合があります。まずは `start.sh` で動作確認し、安定運用はログイン項目（ラッパーApp等）を推奨します。

```xml
<!-- ~/Library/LaunchAgents/com.user.snaplog.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.snaplog</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/SnapLog/src/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/snaplog.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/snaplog.err</string>
</dict>
</plist>
```

---

## 8. セキュリティ考慮事項

### 8.1 権限

| 権限 | 必要性 | 設定場所 |
|------|--------|---------|
| 画面収録 | 必須 | システム設定 > プライバシーとセキュリティ > 画面収録 |
| アクセシビリティ | 必須 | システム設定 > プライバシーとセキュリティ > アクセシビリティ |

### 8.2 データ保護

- ログファイルはユーザーディレクトリに保存（他ユーザーからアクセス不可）
- 一時ファイルは即削除
- 機密情報は除外フィルタで保護
- `capture.mode=fullscreen` の場合、背面ウィンドウの情報が混入し得るため、運用での注意（許可リスト/一時停止）と将来的な `active_window` 対応で軽減する

---

## 9. 依存関係

### 9.1 requirements.txt

```
pyobjc-framework-Vision>=10.0
pyobjc-framework-Quartz>=10.0
PyYAML>=6.0
requests>=2.31.0
```

### 9.2 システム要件

- macOS Ventura (13.0) 以降推奨
- Python 3.10以上
- Xcode Command Line Tools

---

## 10. 今後の拡張性

### 10.1 拡張ポイント

| 機能 | 実装方法 |
|------|---------|
| メニューバーUI | rumpsライブラリ追加 |
| 複数モニター対応 | screencaptureのオプション変更 |
| クラウド同期 | storage.pyに同期機能追加 |
| Web UI | Flask/Streamlit追加 |

### 10.2 モジュール追加時の規約

- 各モジュールは単一責務
- 依存は一方向（main → 各モジュール）
- 設定はconfig経由で注入

---

*作成日: 2025年1月*
*バージョン: 1.0*

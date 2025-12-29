# SnapLog 実装タスク計画（進捗管理用）

このドキュメントは、SnapLogの実装タスクをフェーズ別に分解し、チェックボックスで進捗を管理するためのものです。

## 使い方

- タスクが完了したら `- [ ]` を `- [x]` に変更します
- 迷ったら各フェーズ末尾の「受け入れ条件（Done）」を満たしているかで判断します

---

## Phase 0: 仕様確定・プロジェクト準備

- [x] 仕様4ドキュメントを整合リライト（`README.md` / `snaplog-architecture.md` / `snaplog-requirements.md` / `snaplog-tech-stack.md`）
- [x] `capture.mode`（`fullscreen`/`active_window`）方針を明文化
- [x] 保持期間（リテンション）方針（デフォルト14日）を明文化
- [x] 日報生成の前処理（グルーピング/分割/圧縮）方針を明文化
- [x] launchd運用時の権限注意点を明文化

- [x] リポジトリ構成を作成（`src/` `config/` `scripts/` `tests/`）
- [x] `requirements.txt` を作成（少なくとも `pyobjc-framework-Vision` `pyobjc-framework-Quartz` `PyYAML`、Phase 2で `requests`）
- [x] `config/settings.yaml.example` を作成（`snaplog-architecture.md` のスキーマ準拠）
- [x] `scripts/start.sh` / `scripts/stop.sh` / `scripts/generate_report.sh` を作成（実行権限も付与）
- [x] `.gitignore` を作成（`.pid` `*.log` `~/Documents/SnapLog` 相当の生成物を除外）
- [x] ログ保存先とレポート保存先のパス仕様を確定（`~/Documents/SnapLog/` 基準で統一）
- [x] エラーハンドリング方針を確定（「継続する/停止する」の境界を明文化）
- [x] ログスキーマ（JSONL）を確定（必須/任意フィールド、バージョン）

**Done（受け入れ条件）**
- [ ] ローカルで `python -m src.main` が起動でき、設定ファイル読み込みまで到達する（処理本体は未実装でもよい）

---

## Phase 1: 素材収集（MVP）

### 1.1 設定・ロギング基盤

- [x] `src/config.py` を実装（YAML読み込み、デフォルト値、パス展開 `~`、バリデーション）
- [x] `src/logging.py`（または `src/main.py` 内）にロガー初期化を実装（ファイル＋標準出力）
- [x] `storage.cleanup_on_start=true` のときに起動時クリーンアップが走るようにする

### 1.2 キャプチャ（fullscreen）

- [x] `src/capture.py` を実装（`capture.mode=fullscreen` の `screencapture -x`）
- [x] 一時ファイル名の規約を確定（衝突しない・後始末できる）
- [x] キャプチャ失敗時の挙動を実装（ログ出力して次ループ）

### 1.3 アクティブウィンドウ情報取得

- [x] `src/window_info.py`（または `capture.py`）でアクティブアプリ名取得（`osascript`）
- [x] ウィンドウタイトル取得（失敗時は空文字にフォールバック）
- [x] 取得に必要な権限エラーの検出とメッセージを整備

### 1.4 OCR（Vision Framework）

- [x] `src/ocr.py` を実装（Vision + Quartzで画像読み込み→テキスト抽出）
- [x] 言語設定（`ja-JP` `en-US`）を設定に追従できるようにする（将来拡張でもよい）
- [x] OCR失敗時の挙動を実装（ログ出力して破棄）

### 1.5 フィルタ（除外）

- [x] `src/filter.py` を実装（事前: アプリ名/タイトル、事後: OCR正規表現）
- [x] 除外時の挙動を実装（ログに「除外理由」を残すかどうかを決めて実装）
- [x] 正規表現のプリコンパイルとエラーハンドリング（壊れたregexで落ちない）

### 1.6 保存（JSONL）

- [x] `src/storage.py` を実装（JSONL追記、日付別ファイル、UTF-8、LF）
- [x] ログエントリのフィールドを揃える（`timestamp` `app_name` `window_title` `ocr_text` `ocr_length`）
- [x] ディレクトリ自動作成（`~/Documents/SnapLog/logs`）
- [x] 保持期間（`retention_days`）に従った削除を実装（ログ/レポート）

### 1.7 メインループ統合

- [x] `src/main.py` を実装（処理フローどおりに結線、例外で落ちない）
- [x] `capture.interval` に従ってスリープ（例外時も次ループへ）
- [x] SIGINT（Ctrl+C）で安全に終了できるようにする

### 1.8 テスト（最低限）

- [x] `tests/test_config.py`（設定の読み込み/デフォルト/バリデーション）
- [x] `tests/test_filter.py`（除外判定の単体テスト）
- [x] `tests/test_storage.py`（JSONL追記、パス生成、リテンション）
- [x] macOS依存部分はモック/DIでテスト可能にする（`subprocess` の差し替え等）

**Done（受け入れ条件）**
- [ ] 1分間隔で「キャプチャ→OCR→フィルタ→JSONL追記→画像削除」が回る
- [ ] 除外条件に一致した場合、ログに保存されず一時画像も残らない
- [ ] `retention_days` を小さくして古いログが削除されることを確認できる

---

## Phase 2: 日報生成（ローカルLLM）

### 2.1 ログ読み込み・前処理（入力圧縮）

- [x] `src/report_preprocess.py` を実装（ログ読み込み→整形）
- [x] セッション分割（`report.group_gap_minutes`）を実装
- [x] グルーピング（例: アプリ/ウィンドウ/時間帯）を実装
- [x] チャンク分割（`report.chunk_chars`）を実装（LLM投入上限対策）
- [x] 個人情報っぽいパターンの追加マスキング（任意、要件に合わせて）

### 2.2 LLMクライアント（OpenAI互換）

- [x] `src/llm_client.py` を実装（`/v1/chat/completions` 前提）
- [x] タイムアウト/リトライ/エラーメッセージを実装
- [x] モデル名（`llm.model`）と `max_tokens` を設定から反映

### 2.3 日報テンプレート・Markdown出力

- [x] 日報の固定テンプレートを確定（見出し構成、箇条書き、所感、課題、明日の予定など）
- [x] `src/report.py` を実装（`--date` 指定、出力先 `~/Documents/SnapLog/reports/`）
- [x] 大量ログ時に「分割生成→結合」できるようにする

### 2.4 スクリプト/UX

- [x] `scripts/generate_report.sh` を実装（今日/指定日）
- [x] 失敗時に「LLMが起動していない」など原因が分かるメッセージにする

### 2.5 テスト（最低限）

- [x] `tests/test_report_preprocess.py`（グルーピング/分割/チャンク）
- [x] `tests/test_llm_client.py`（HTTP部分はモック）

**Done（受け入れ条件）**
- [ ] `python -m src.report` で当日分のMarkdown日報が生成される
- [ ] ログが多い日でも入力上限で落ちず、分割して生成できる

---

## Phase 3: 改善（精度・UX・運用）

### 3.1 キャプチャ範囲改善（active_window）

- [x] `capture.mode=active_window` を実装（前面ウィンドウのみ撮影）
- [x] 複数モニター環境での挙動を定義し実装（メイン/全画面/前面ウィンドウ優先）
- [x] `fullscreen` と `active_window` の切り替えを設定で可能にする

### 3.2 プライバシー強化

- [x] 許可リスト（allowlist）運用の追加（「このアプリだけ記録」モード）
- [x] 一時停止（pause）機能（ホットキー or CLIフラグ or UI）
- [x] 除外判定のログ（理由）を必要最小限で残す方針を確定し実装

### 3.3 常駐・起動体験

- [x] メニューバーUI（`rumps`）を実装（状態表示/停止/一時停止/手動日報生成）
- [x] 自動起動（launchd）用のテンプレートを整備（権限注意を明記）

### 3.4 品質・配布

- [x] `ruff` / `pytest` 実行手順を整備（CIがあるならCIも追加）
- [x] バージョニング方針（alpha/beta）を決める
- [x] 配布手順（zip/Installer/簡易アプリ化）を決める

**Done（受け入れ条件）**
- [x] `active_window` で背面ウィンドウ混入リスクが実用上許容できる（ウィンドウID指定により前面ウィンドウのみキャプチャ）
- [x] 一時停止/再開が迷わず操作できる（メニューバーUIから操作可能）

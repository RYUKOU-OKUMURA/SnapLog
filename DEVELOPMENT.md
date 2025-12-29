# SnapLog 開発ガイド

## 開発環境セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 開発用依存関係のインストール

```bash
pip install pytest pytest-cov ruff
```

## コード品質チェック

### Ruff（リント・フォーマット）

```bash
# リントチェック
ruff check src/ tests/

# 自動修正
ruff check --fix src/ tests/

# フォーマットチェック
ruff format --check src/ tests/

# フォーマット適用
ruff format src/ tests/
```

### テスト実行

```bash
# すべてのテストを実行
pytest

# カバレッジ付きで実行
pytest --cov=src --cov-report=html

# 特定のテストファイルを実行
pytest tests/test_config.py

# 詳細出力
pytest -v
```

## バージョニング方針

### バージョン形式

`MAJOR.MINOR.PATCH`（セマンティックバージョニング）

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある新機能追加
- **PATCH**: バグ修正

### 現在のバージョン

- **Phase 1**: 0.1.0（MVP）
- **Phase 2**: 0.2.0（日報生成）
- **Phase 3**: 0.3.0（改善機能）

### バージョン管理

バージョンは `src/__init__.py` に定義します：

```python
__version__ = "0.3.0"
```

## 配布手順

### 1. 配布用パッケージの作成

```bash
# プロジェクトルートで実行
python setup.py sdist bdist_wheel
```

### 2. 簡易配布（zip形式）

```bash
# 配布用ディレクトリを作成
mkdir -p dist/snaplog-$(date +%Y%m%d)

# 必要なファイルをコピー
cp -r src/ dist/snaplog-$(date +%Y%m%d)/
cp -r config/ dist/snaplog-$(date +%Y%m%d)/
cp -r scripts/ dist/snaplog-$(date +%Y%m%d)/
cp requirements.txt dist/snaplog-$(date +%Y%m%d)/
cp README.md dist/snaplog-$(date +%Y%m%d)/

# zipファイルを作成
cd dist
zip -r snaplog-$(date +%Y%m%d).zip snaplog-$(date +%Y%m%d)
```

### 3. macOSアプリ化（オプション）

PyInstallerを使用してアプリバンドルを作成：

```bash
pip install pyinstaller

# メニューバーUI付きアプリを作成
pyinstaller --onefile --windowed --name=SnapLog \
  --icon=icon.icns \
  --add-data "config:config" \
  src/main.py
```

### 4. インストーラー作成（オプション）

`create-dmg` を使用：

```bash
npm install -g create-dmg

create-dmg SnapLog.app dist/
```

## CI/CD（将来の拡張）

GitHub Actionsの例：

```yaml
name: Test and Lint

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov ruff
      - run: ruff check src/ tests/
      - run: pytest --cov=src
```

## コーディング規約

- PEP 8に準拠
- 型ヒントを使用（可能な限り）
- docstringはGoogle形式
- 関数・クラスには適切なdocstringを記述

## コミットメッセージ規約

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント変更
- `style:` コードスタイル変更
- `refactor:` リファクタリング
- `test:` テスト追加・変更
- `chore:` その他の変更

例：
```
feat: active_windowモードを実装
fix: メニューバーUIの状態表示を修正
docs: 開発ガイドを追加
```


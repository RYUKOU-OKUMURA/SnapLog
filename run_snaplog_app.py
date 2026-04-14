#!/usr/bin/env python3
"""
SnapLog.app 用エントリーポイント
メニューバーモードで自動起動
"""
import os
from pathlib import Path
import shutil
import sys


APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "SnapLog"


def _resolve_resources_dir() -> Path:
    """バンドル内 Resources ディレクトリを返す。"""
    bundle_dir = Path(sys.executable).resolve().parent
    return (bundle_dir / ".." / "Resources").resolve()


def ensure_user_config(resources_dir: Path) -> Path:
    """ユーザー設定ファイルを Application Support に配置する。"""
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

    user_config_path = APP_SUPPORT_DIR / "settings.yaml"
    if user_config_path.exists():
        return user_config_path

    bundle_candidates = [
        resources_dir / "config" / "settings.yaml",
        resources_dir / "config" / "settings.yaml.example",
    ]
    source_path = next((path for path in bundle_candidates if path.exists()), None)
    if source_path is None:
        raise FileNotFoundError(
            f"バンドル内に設定テンプレートが見つかりません: {resources_dir / 'config'}"
        )

    shutil.copy2(source_path, user_config_path)
    return user_config_path


def setup_bundle_environment():
    """
    py2app バンドル環境用のセットアップ
    バンドル内のリソースパスを設定
    """
    if getattr(sys, 'frozen', False):
        # py2app でバンドルされた場合
        resources_dir = _resolve_resources_dir()
        user_config_path = ensure_user_config(resources_dir)

        # 設定ファイルのパスをユーザー領域に設定
        os.environ['SNAPLOG_CONFIG'] = str(user_config_path)
        os.environ['SNAPLOG_APP_SUPPORT_DIR'] = str(APP_SUPPORT_DIR)


def main():
    """メイン関数"""
    # バンドル環境のセットアップ
    setup_bundle_environment()

    # メニューバーモードで起動
    sys.argv.append('--menu-bar')

    from src.main import main as snaplog_main
    snaplog_main()


if __name__ == "__main__":
    main()

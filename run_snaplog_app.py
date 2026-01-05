#!/usr/bin/env python3
"""
SnapLog.app 用エントリーポイント
メニューバーモードで自動起動
"""
import sys
import os


def setup_bundle_environment():
    """
    py2app バンドル環境用のセットアップ
    バンドル内のリソースパスを設定
    """
    if getattr(sys, 'frozen', False):
        # py2app でバンドルされた場合
        bundle_dir = os.path.dirname(sys.executable)
        resources_dir = os.path.abspath(os.path.join(bundle_dir, '..', 'Resources'))

        # 設定ファイルのパスをバンドル内に設定
        config_path = os.path.join(resources_dir, 'config', 'settings.yaml')
        if os.path.exists(config_path):
            os.environ['SNAPLOG_CONFIG'] = config_path


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

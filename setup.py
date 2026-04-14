"""
py2app setup script for SnapLog
macOS メニューバーアプリとしてパッケージング
"""
from pathlib import Path

from setuptools import setup

from src import __version__

APP = ['run_snaplog_app.py']

config_files = []
for candidate in ['config/settings.yaml', 'config/settings.yaml.example']:
    if Path(candidate).exists():
        config_files.append(candidate)

DATA_FILES = []
if config_files:
    DATA_FILES.append(('config', config_files))

OPTIONS = {
    'argv_emulation': False,  # rumps と競合するため無効化
    'plist': {
        'CFBundleName': 'SnapLog',
        'CFBundleDisplayName': 'SnapLog',
        'CFBundleIdentifier': 'com.user.snaplog',
        'CFBundleVersion': __version__,
        'CFBundleShortVersionString': __version__,
        'LSUIElement': True,  # Dock に表示しない（メニューバーアプリ用）
        'NSHighResolutionCapable': True,
        'NSScreenCaptureUsageDescription':
            'SnapLog は画面をキャプチャして作業ログを記録します。',
        'NSAppleEventsUsageDescription':
            'SnapLog はアクティブウィンドウの情報を取得するためにアクセシビリティ機能を使用します。',
    },
    'packages': [
        'src',
        'rumps',
        'yaml',
        'requests',
    ],
    'includes': [
        'Foundation',
        'Quartz',
        'Vision',
        'objc',
        'PyObjCTools',
    ],
    'iconfile': 'resources/SnapLog.icns',
}

setup(
    name='SnapLog',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

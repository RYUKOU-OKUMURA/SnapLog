"""
py2app setup script for SnapLog
macOS メニューバーアプリとしてパッケージング
"""
from setuptools import setup

APP = ['run_snaplog_app.py']

DATA_FILES = [
    ('config', ['config/settings.yaml']),
]

OPTIONS = {
    'argv_emulation': False,  # rumps と競合するため無効化
    'plist': {
        'CFBundleName': 'SnapLog',
        'CFBundleDisplayName': 'SnapLog',
        'CFBundleIdentifier': 'com.user.snaplog',
        'CFBundleVersion': '0.3.0',
        'CFBundleShortVersionString': '0.3.0',
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

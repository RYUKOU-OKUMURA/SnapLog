"""メニューバーUIモジュール（rumps）"""
import logging
import subprocess
import threading
from pathlib import Path

try:
    import rumps
    RUMPS_AVAILABLE = True
except ImportError:
    rumps = None
    RUMPS_AVAILABLE = False

from . import config
from . import main as main_module
from . import report as report_module

logger = logging.getLogger("snaplog.menu_bar")


class SnapLogMenuBarApp(rumps.App):
    """SnapLogメニューバーアプリケーション"""
    
    def __init__(self):
        super(SnapLogMenuBarApp, self).__init__("SnapLog", quit_button=None)
        
        # 設定読み込み
        try:
            self.cfg = config.load_config()
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            self.cfg = config.Config()
            self.cfg.expand_paths()
        
        # メニュー項目を構築
        self.build_menu()
        
        # 状態更新用のタイマー
        self.update_timer = rumps.Timer(self.update_status, 5)  # 5秒ごとに更新
        self.update_timer.start()
    
    def build_menu(self):
        """メニュー項目を構築"""
        self.menu.clear()
        
        # 状態表示
        status = "一時停止中" if main_module.paused else "実行中"
        self.menu.add(rumps.MenuItem(f"状態: {status}", callback=None))
        self.menu.add(rumps.separator)
        
        # 一時停止/再開
        pause_text = "再開" if main_module.paused else "一時停止"
        self.menu.add(rumps.MenuItem(pause_text, callback=self.toggle_pause))
        
        # 日報生成
        self.menu.add(rumps.MenuItem("今日の日報を生成", callback=self.generate_today_report))
        self.menu.add(rumps.separator)
        
        # ログフォルダを開く
        self.menu.add(rumps.MenuItem("ログフォルダを開く", callback=self.open_logs_folder))
        
        # レポートフォルダを開く
        self.menu.add(rumps.MenuItem("レポートフォルダを開く", callback=self.open_reports_folder))
        
        self.menu.add(rumps.separator)
        
        # 終了
        self.menu.add(rumps.MenuItem("終了", callback=self.quit_app))
    
    def update_status(self, _):
        """状態を更新"""
        self.build_menu()
    
    @rumps.clicked("一時停止")
    @rumps.clicked("再開")
    def toggle_pause(self, _):
        """一時停止/再開を切り替え"""
        main_module.toggle_pause()
        self.build_menu()
        
        if main_module.paused:
            rumps.notification("SnapLog", "一時停止", "キャプチャを一時停止しました")
        else:
            rumps.notification("SnapLog", "再開", "キャプチャを再開しました")
    
    @rumps.clicked("今日の日報を生成")
    def generate_today_report(self, _):
        """今日の日報を生成"""
        def _generate():
            try:
                rumps.notification("SnapLog", "日報生成開始", "日報を生成しています...")
                from datetime import datetime
                target_date = datetime.now().strftime("%Y-%m-%d")
                report_path = report_module.generate_report_for_date(target_date, self.cfg)
                if report_path:
                    rumps.notification("SnapLog", "日報生成完了", f"日報を生成しました: {report_path}")
                else:
                    rumps.notification("SnapLog", "日報生成失敗", "日報の生成に失敗しました")
            except Exception as e:
                logger.error(f"日報生成エラー: {e}")
                rumps.notification("SnapLog", "エラー", f"日報生成中にエラーが発生しました: {e}")
        
        # 別スレッドで実行（UIをブロックしない）
        thread = threading.Thread(target=_generate)
        thread.daemon = True
        thread.start()
    
    @rumps.clicked("ログフォルダを開く")
    def open_logs_folder(self, _):
        """ログフォルダを開く"""
        log_dir = Path(self.cfg.storage.base_dir) / self.cfg.storage.log_subdir
        log_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(log_dir)])
    
    @rumps.clicked("レポートフォルダを開く")
    def open_reports_folder(self, _):
        """レポートフォルダを開く"""
        report_dir = Path(self.cfg.storage.base_dir) / self.cfg.storage.report_subdir
        report_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(report_dir)])
    
    @rumps.clicked("終了")
    def quit_app(self, _):
        """アプリケーションを終了"""
        main_module.running = False
        rumps.quit_application()


def run_menu_bar():
    """メニューバーUIを起動"""
    if not RUMPS_AVAILABLE:
        logger.error("rumpsライブラリがインストールされていません。pip install rumps を実行してください。")
        import sys
        sys.exit(1)
    
    app = SnapLogMenuBarApp()
    app.run()


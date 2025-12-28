"""ウィンドウ情報取得モジュール"""
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("snaplog.window_info")


@dataclass
class WindowInfo:
    """ウィンドウ情報"""
    app_name: str
    window_title: str


def get_active_app_name() -> str:
    """
    アクティブなアプリケーション名を取得
    
    Returns:
        str: アプリケーション名（取得失敗時は空文字列）
    """
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
    end tell
    return frontApp
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "not allowed assistive access" in error_msg.lower() or "access for assistive devices" in error_msg.lower():
                logger.error(
                    "アクセシビリティ権限が必要です。"
                    "システム設定 > プライバシーとセキュリティ > アクセシビリティ で"
                    "Terminalまたは実行アプリを許可してください。"
                )
            else:
                logger.warning(f"アプリ名取得失敗: {error_msg}")
            return ""
        
        app_name = result.stdout.strip()
        return app_name if app_name else ""
        
    except subprocess.TimeoutExpired:
        logger.error("アプリ名取得がタイムアウトしました")
        return ""
    except Exception as e:
        logger.error(f"アプリ名取得中にエラーが発生しました: {e}")
        return ""


def get_window_title() -> str:
    """
    アクティブウィンドウのタイトルを取得
    
    Returns:
        str: ウィンドウタイトル（取得失敗時は空文字列）
    """
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
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "not allowed assistive access" in error_msg.lower() or "access for assistive devices" in error_msg.lower():
                logger.error(
                    "アクセシビリティ権限が必要です。"
                    "システム設定 > プライバシーとセキュリティ > アクセシビリティ で"
                    "Terminalまたは実行アプリを許可してください。"
                )
            else:
                logger.debug(f"ウィンドウタイトル取得失敗（無視可能）: {error_msg}")
            return ""
        
        window_title = result.stdout.strip()
        return window_title if window_title else ""
        
    except subprocess.TimeoutExpired:
        logger.warning("ウィンドウタイトル取得がタイムアウトしました（無視可能）")
        return ""
    except Exception as e:
        logger.debug(f"ウィンドウタイトル取得中にエラーが発生しました（無視可能）: {e}")
        return ""


def get_active_window() -> WindowInfo:
    """
    アクティブウィンドウの情報を取得
    
    Returns:
        WindowInfo: ウィンドウ情報（app_name, window_title）
    """
    app_name = get_active_app_name()
    window_title = get_window_title()
    
    return WindowInfo(
        app_name=app_name,
        window_title=window_title
    )


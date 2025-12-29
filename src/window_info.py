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
    window_id: Optional[int] = None  # ウィンドウID（active_windowモード用）
    window_bounds: Optional[dict] = None  # ウィンドウの座標（active_windowモード用）


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


def get_window_id() -> Optional[int]:
    """
    アクティブウィンドウのIDを取得
    
    Returns:
        Optional[int]: ウィンドウID（取得失敗時はNone）
    """
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        try
            set windowId to id of front window of frontApp
        on error
            set windowId to 0
        end try
    end tell
    return windowId
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.debug("ウィンドウID取得失敗（無視可能）")
            return None
        
        window_id_str = result.stdout.strip()
        if window_id_str and window_id_str.isdigit():
            return int(window_id_str)
        return None
        
    except Exception as e:
        logger.debug(f"ウィンドウID取得中にエラーが発生しました（無視可能）: {e}")
        return None


def get_window_bounds() -> Optional[dict]:
    """
    アクティブウィンドウの座標とサイズを取得
    
    Returns:
        Optional[dict]: {"x": int, "y": int, "width": int, "height": int} または None
    """
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        try
            set frontWindow to front window of frontApp
            set windowBounds to bounds of frontWindow
            return windowBounds
        on error
            return ""
        end try
    end tell
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.debug("ウィンドウ座標取得失敗（無視可能）")
            return None
        
        bounds_str = result.stdout.strip()
        if not bounds_str:
            return None
        
        # AppleScriptのboundsは "x1, y1, x2, y2" 形式
        try:
            parts = [int(x.strip()) for x in bounds_str.split(",")]
            if len(parts) == 4:
                x1, y1, x2, y2 = parts
                return {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
        except ValueError:
            logger.debug(f"ウィンドウ座標のパース失敗: {bounds_str}")
            return None
        
        return None
        
    except Exception as e:
        logger.debug(f"ウィンドウ座標取得中にエラーが発生しました（無視可能）: {e}")
        return None


def get_active_window(include_bounds: bool = False) -> WindowInfo:
    """
    アクティブウィンドウの情報を取得
    
    Args:
        include_bounds: Trueの場合、ウィンドウIDと座標も取得（active_windowモード用）
    
    Returns:
        WindowInfo: ウィンドウ情報（app_name, window_title, window_id, window_bounds）
    """
    app_name = get_active_app_name()
    window_title = get_window_title()
    
    window_id = None
    window_bounds = None
    
    if include_bounds:
        window_id = get_window_id()
        window_bounds = get_window_bounds()
    
    return WindowInfo(
        app_name=app_name,
        window_title=window_title,
        window_id=window_id,
        window_bounds=window_bounds
    )



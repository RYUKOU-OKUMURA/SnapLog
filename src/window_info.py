"""ウィンドウ情報取得モジュール"""
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

import Quartz

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


def get_frontmost_window_via_quartz() -> Optional[dict]:
    """
    Quartz APIを使用して最前面のウィンドウ情報を取得

    Returns:
        Optional[dict]: {"window_id": int, "app_name": str, "window_title": str, "bounds": dict} または None
    """
    try:
        # 画面上のウィンドウリストを取得
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )

        if not window_list:
            logger.debug("ウィンドウリストの取得に失敗")
            return None

        # レイヤー0（通常のウィンドウ）で最前面のものを探す
        for window in window_list:
            layer = window.get(Quartz.kCGWindowLayer, 999)

            # レイヤー0は通常のアプリウィンドウ
            if layer == 0:
                window_id = window.get(Quartz.kCGWindowNumber)
                app_name = window.get(Quartz.kCGWindowOwnerName, "")
                window_title = window.get(Quartz.kCGWindowName, "")
                bounds_dict = window.get(Quartz.kCGWindowBounds, {})

                # ウィンドウIDが有効でない場合はスキップ
                if not window_id:
                    continue

                # 除外するシステムウィンドウ
                if app_name in ["Window Server", "Dock", "SystemUIServer", "Control Center"]:
                    continue

                bounds = None
                if bounds_dict:
                    bounds = {
                        "x": int(bounds_dict.get("X", 0)),
                        "y": int(bounds_dict.get("Y", 0)),
                        "width": int(bounds_dict.get("Width", 0)),
                        "height": int(bounds_dict.get("Height", 0)),
                    }

                return {
                    "window_id": window_id,
                    "app_name": app_name,
                    "window_title": window_title,
                    "bounds": bounds,
                }

        logger.debug("有効な最前面ウィンドウが見つかりません")
        return None

    except Exception as e:
        logger.debug(f"Quartz APIでのウィンドウ情報取得に失敗: {e}")
        return None


def get_window_id() -> Optional[int]:
    """
    アクティブウィンドウのIDを取得（Quartz API使用）

    Returns:
        Optional[int]: ウィンドウID（取得失敗時はNone）
    """
    window_info = get_frontmost_window_via_quartz()
    if window_info:
        return window_info.get("window_id")
    return None


def get_window_bounds() -> Optional[dict]:
    """
    アクティブウィンドウの座標とサイズを取得（Quartz API使用）

    Returns:
        Optional[dict]: {"x": int, "y": int, "width": int, "height": int} または None
    """
    window_info = get_frontmost_window_via_quartz()
    if window_info:
        return window_info.get("bounds")
    return None


def get_active_window(include_bounds: bool = False) -> WindowInfo:
    """
    アクティブウィンドウの情報を取得

    Args:
        include_bounds: Trueの場合、ウィンドウIDと座標も取得（active_windowモード用）

    Returns:
        WindowInfo: ウィンドウ情報（app_name, window_title, window_id, window_bounds）
    """
    window_id = None
    window_bounds = None
    quartz_app_name = ""
    quartz_title = ""

    # Quartz APIで情報を取得（ウィンドウID取得に信頼性が高い）
    if include_bounds:
        quartz_info = get_frontmost_window_via_quartz()
        if quartz_info:
            window_id = quartz_info.get("window_id")
            window_bounds = quartz_info.get("bounds")
            quartz_app_name = quartz_info.get("app_name", "")
            quartz_title = quartz_info.get("window_title", "")

    # AppleScriptでも情報を取得（ウィンドウタイトルが詳細に取れることがある）
    applescript_app_name = get_active_app_name()
    applescript_title = get_window_title()

    # アプリ名: AppleScript優先（より正確）、なければQuartz
    app_name = applescript_app_name if applescript_app_name else quartz_app_name

    # タイトル: AppleScript優先（より詳細）、なければQuartz
    window_title = applescript_title if applescript_title else quartz_title

    return WindowInfo(
        app_name=app_name,
        window_title=window_title,
        window_id=window_id,
        window_bounds=window_bounds
    )



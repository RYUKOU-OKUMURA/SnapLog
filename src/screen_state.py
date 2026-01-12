"""画面状態の取得（自動一時停止用）"""
import logging

import Quartz

logger = logging.getLogger("snaplog.screen_state")


def _get_session_dict() -> dict:
    try:
        session = Quartz.CGSessionCopyCurrentDictionary()
        return session or {}
    except Exception as e:
        logger.debug(f"セッション情報の取得に失敗しました: {e}")
        return {}


def is_screen_locked() -> bool:
    """画面ロック中かどうか"""
    session = _get_session_dict()
    if not session:
        return False

    if hasattr(Quartz, "kCGSessionScreenIsLocked"):
        return bool(session.get(Quartz.kCGSessionScreenIsLocked, 0))
    return bool(session.get("CGSSessionScreenIsLocked", 0))


def is_display_asleep() -> bool:
    """ディスプレイがスリープ中かどうか"""
    if not hasattr(Quartz, "CGDisplayIsAsleep"):
        return False
    try:
        display_id = Quartz.CGMainDisplayID()
        return bool(Quartz.CGDisplayIsAsleep(display_id))
    except Exception as e:
        logger.debug(f"ディスプレイ状態の取得に失敗しました: {e}")
        return False

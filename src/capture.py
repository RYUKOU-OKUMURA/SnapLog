"""キャプチャモジュール"""
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("snaplog.capture")


def generate_temp_filename(temp_dir: str, suffix: str = ".png") -> str:
    """
    一時ファイル名を生成（衝突回避）
    
    Args:
        temp_dir: 一時ディレクトリのパス
        suffix: ファイル拡張子
        
    Returns:
        str: 一時ファイルのフルパス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # tempfile.mkstempを使用して衝突しないファイル名を生成
    fd, filepath = tempfile.mkstemp(
        prefix=f"snaplog_{timestamp}_",
        suffix=suffix,
        dir=temp_dir
    )
    os.close(fd)  # ファイルディスクリプタを閉じる（ファイルは残す）
    return filepath


def take_screenshot(
    output_path: Optional[str] = None,
    temp_dir: str = "/tmp",
    mode: str = "fullscreen",
    window_id: Optional[int] = None
) -> Optional[str]:
    """
    スクリーンショットを撮影
    
    Args:
        output_path: 出力先パス（Noneの場合は自動生成）
        temp_dir: 一時ディレクトリ（output_pathがNoneの場合に使用）
        mode: キャプチャモード（"fullscreen" または "active_window"）
        window_id: ウィンドウID（active_windowモードの場合に必要）
        
    Returns:
        Optional[str]: 保存された画像のパス（失敗時はNone）
    """
    if output_path is None:
        output_path = generate_temp_filename(temp_dir)
    
    try:
        # キャプチャコマンドを構築
        cmd = ["screencapture", "-x"]  # -x: 撮影音無効化
        
        if mode == "active_window" and window_id:
            # アクティブウィンドウのみをキャプチャ（-l: ウィンドウID指定）
            cmd.extend(["-l", str(window_id)])
        # fullscreenモードの場合は追加オプションなし
        
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "不明なエラー"
            logger.error(f"スクリーンショット撮影失敗: {error_msg}")
            
            # 権限エラーの可能性をチェック
            if "not allowed" in error_msg.lower() or "permission" in error_msg.lower():
                logger.error(
                    "画面収録権限が必要です。"
                    "システム設定 > プライバシーとセキュリティ > 画面収録 で"
                    "Terminalまたは実行アプリを許可してください。"
                )
            
            # ファイルが作成されていても削除
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            
            return None
        
        # ファイルが存在するか確認
        if not os.path.exists(output_path):
            logger.error(f"スクリーンショットファイルが作成されませんでした: {output_path}")
            return None
        
        logger.debug(f"スクリーンショット撮影成功: {output_path}")
        return output_path
        
    except subprocess.TimeoutExpired:
        logger.error("スクリーンショット撮影がタイムアウトしました")
        # タイムアウト時もファイルが作成されている可能性があるので削除
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return None
    except Exception as e:
        logger.error(f"スクリーンショット撮影中にエラーが発生しました: {e}")
        # エラー時もファイルが作成されている可能性があるので削除
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return None


def delete_image(image_path: str) -> bool:
    """
    画像ファイルを削除
    
    Args:
        image_path: 削除する画像ファイルのパス
        
    Returns:
        bool: 削除成功時True
    """
    if not image_path:
        return False
    
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.debug(f"画像ファイルを削除しました: {image_path}")
            return True
        else:
            logger.debug(f"画像ファイルが存在しません（既に削除済み）: {image_path}")
            return True  # 既に存在しない場合は成功とみなす
    except Exception as e:
        logger.warning(f"画像ファイル削除失敗: {image_path}, エラー: {e}")
        return False



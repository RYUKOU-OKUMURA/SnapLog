"""ストレージモジュール"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .window_info import WindowInfo

logger = logging.getLogger("snaplog.storage")


def cleanup_old_files(
    base_dir: str,
    log_subdir: str = "logs",
    report_subdir: str = "reports",
    retention_days: int = 14
) -> int:
    """
    リテンション期間を超えた古いファイルを削除
    
    Args:
        base_dir: ベースディレクトリ
        log_subdir: ログサブディレクトリ名
        report_subdir: レポートサブディレクトリ名
        retention_days: 保持日数
        
    Returns:
        int: 削除したファイル数
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        logger.debug(f"ベースディレクトリが存在しません: {base_dir}")
        return 0
    
    # 削除対象の日付を計算
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_count = 0
    
    # ログディレクトリとレポートディレクトリを処理
    for subdir_name in [log_subdir, report_subdir]:
        subdir_path = base_path / subdir_name
        if not subdir_path.exists():
            continue
        
        # ディレクトリ内のファイルを走査
        for file_path in subdir_path.iterdir():
            if not file_path.is_file():
                continue
            
            try:
                # ファイルの更新日時を取得
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # リテンション期間を超えている場合は削除
                if mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"古いファイルを削除: {file_path}")
                    
            except Exception as e:
                logger.warning(f"ファイル削除中にエラーが発生しました: {file_path}, エラー: {e}")
                continue
    
    if deleted_count > 0:
        logger.info(f"{deleted_count}個の古いファイルを削除しました（リテンション期間: {retention_days}日）")
    else:
        logger.debug("削除対象の古いファイルはありませんでした")
    
    return deleted_count


def ensure_directories(base_dir: str, log_subdir: str = "logs", report_subdir: str = "reports") -> None:
    """
    必要なディレクトリが存在することを確認し、存在しない場合は作成
    
    Args:
        base_dir: ベースディレクトリ
        log_subdir: ログサブディレクトリ名
        report_subdir: レポートサブディレクトリ名
    """
    base_path = Path(base_dir)
    
    # ベースディレクトリを作成
    base_path.mkdir(parents=True, exist_ok=True)
    
    # サブディレクトリを作成
    (base_path / log_subdir).mkdir(parents=True, exist_ok=True)
    (base_path / report_subdir).mkdir(parents=True, exist_ok=True)
    
    logger.debug(f"ディレクトリを確認/作成しました: {base_dir}")


def save_log(
    window_info: WindowInfo,
    ocr_text: str,
    base_dir: str,
    log_subdir: str = "logs"
) -> None:
    """
    ログをJSONLファイルに保存
    
    Args:
        window_info: ウィンドウ情報
        ocr_text: OCRで抽出されたテキスト
        base_dir: ベースディレクトリ
        log_subdir: ログサブディレクトリ名
    """
    try:
        # ディレクトリを確保
        ensure_directories(base_dir, log_subdir)
        
        # タイムスタンプ生成（ISO 8601形式、タイムゾーン付き）
        timestamp = datetime.now().astimezone().isoformat()
        
        # ログエントリ構造を作成
        log_entry = {
            "timestamp": timestamp,
            "app_name": window_info.app_name,
            "window_title": window_info.window_title,
            "ocr_text": ocr_text,
            "ocr_length": len(ocr_text)
        }
        
        # 日付別ファイル名生成（activity_log_YYYY-MM-DD.jsonl）
        today = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"activity_log_{today}.jsonl"
        
        # ログファイルのパス
        log_dir = Path(base_dir) / log_subdir
        log_file_path = log_dir / log_filename
        
        # JSONL追記（UTF-8、LF改行）
        with open(log_file_path, "a", encoding="utf-8", newline="\n") as f:
            json_line = json.dumps(log_entry, ensure_ascii=False)
            f.write(json_line + "\n")
        
        logger.debug(f"ログを保存しました: {log_file_path}")
        
    except Exception as e:
        logger.error(f"ログ保存中にエラーが発生しました: {e}")
        raise



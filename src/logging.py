"""ロギングモジュール"""
import logging
import os
from pathlib import Path
from typing import Optional

from .config import Config, LoggingConfig


def setup_logging(config: Optional[Config] = None, log_config: Optional[LoggingConfig] = None) -> logging.Logger:
    """
    ロガーを初期化する
    
    Args:
        config: 全体設定オブジェクト（省略時はlog_configを使用）
        log_config: ロギング設定（省略時はconfigから取得、またはデフォルト値）
        
    Returns:
        logging.Logger: 設定済みロガー
    """
    if config is not None:
        log_config = config.logging
    elif log_config is None:
        log_config = LoggingConfig()
    
    # ログレベルを設定
    log_level = getattr(logging, log_config.level.upper(), logging.INFO)
    
    # ロガーを作成
    logger = logging.getLogger("snaplog")
    logger.setLevel(log_level)
    
    # 既存のハンドラをクリア（重複を防ぐ）
    logger.handlers.clear()
    
    # フォーマットを設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 標準出力ハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラ
    log_file_path = os.path.expanduser(log_config.file)
    log_file_dir = Path(log_file_path).parent
    
    # ログディレクトリが存在しない場合は作成
    if log_file_dir and not log_file_dir.exists():
        log_file_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger














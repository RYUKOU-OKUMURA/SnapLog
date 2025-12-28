"""設定管理モジュール"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class CaptureConfig:
    """キャプチャ設定"""
    interval: int = 60
    mode: str = "fullscreen"
    temp_dir: str = "/tmp"


@dataclass
class StorageConfig:
    """ストレージ設定"""
    base_dir: str = "~/Documents/SnapLog"
    log_subdir: str = "logs"
    report_subdir: str = "reports"
    retention_days: int = 14
    cleanup_on_start: bool = True


@dataclass
class FilterConfig:
    """フィルタ設定"""
    exclude_apps: List[str] = field(default_factory=list)
    exclude_title_keywords: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class LLMConfig:
    """LLM設定（Phase 2用）"""
    endpoint: str = "http://localhost:1234/v1/chat/completions"
    model: str = "llama3.2"
    max_tokens: int = 2000


@dataclass
class ReportConfig:
    """日報生成設定（Phase 2用）"""
    group_gap_minutes: int = 10
    chunk_chars: int = 12000


@dataclass
class LoggingConfig:
    """ロギング設定"""
    level: str = "INFO"
    file: str = "~/Documents/SnapLog/app.log"


@dataclass
class Config:
    """全体設定"""
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def expand_paths(self) -> None:
        """パス内の`~`を展開"""
        self.storage.base_dir = os.path.expanduser(self.storage.base_dir)
        self.capture.temp_dir = os.path.expanduser(self.capture.temp_dir)
        self.logging.file = os.path.expanduser(self.logging.file)

    def validate(self) -> None:
        """設定値のバリデーション"""
        if self.capture.interval < 1:
            raise ValueError("capture.interval must be >= 1")
        if self.capture.mode not in ["fullscreen", "active_window"]:
            raise ValueError("capture.mode must be 'fullscreen' or 'active_window'")
        if self.storage.retention_days < 1:
            raise ValueError("storage.retention_days must be >= 1")
        if self.logging.level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ValueError("logging.level must be one of: DEBUG, INFO, WARNING, ERROR")


def load_config(config_path: Optional[str] = None) -> Config:
    """
    設定ファイルを読み込む
    
    Args:
        config_path: 設定ファイルのパス（Noneの場合はデフォルトパスを使用）
        
    Returns:
        Config: 設定オブジェクト
    """
    if config_path is None:
        # デフォルトパス: config/settings.yaml
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "settings.yaml"
    
    config_path = Path(config_path)
    
    # 設定ファイルが存在しない場合はデフォルト値を使用
    if not config_path.exists():
        config = Config()
        config.expand_paths()
        return config
    
    # YAMLファイルを読み込み
    with open(config_path, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f) or {}
    
    # 設定オブジェクトを作成
    config = Config(
        capture=CaptureConfig(**yaml_data.get("capture", {})),
        storage=StorageConfig(**yaml_data.get("storage", {})),
        filter=FilterConfig(**yaml_data.get("filter", {})),
        llm=LLMConfig(**yaml_data.get("llm", {})),
        report=ReportConfig(**yaml_data.get("report", {})),
        logging=LoggingConfig(**yaml_data.get("logging", {})),
    )
    
    # パス展開とバリデーション
    config.expand_paths()
    config.validate()
    
    return config


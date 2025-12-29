"""設定モジュールのテスト"""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import (
    Config,
    CaptureConfig,
    StorageConfig,
    FilterConfig,
    LoggingConfig,
    load_config,
)


def test_default_config():
    """デフォルト設定のテスト"""
    config = Config()
    
    assert config.capture.interval == 60
    assert config.capture.mode == "fullscreen"
    assert config.capture.temp_dir == "/tmp"
    
    assert config.storage.base_dir == "~/Documents/SnapLog"
    assert config.storage.log_subdir == "logs"
    assert config.storage.report_subdir == "reports"
    assert config.storage.retention_days == 14
    assert config.storage.cleanup_on_start is True
    
    assert config.filter.exclude_apps == []
    assert config.filter.exclude_title_keywords == []
    assert config.filter.exclude_patterns == []
    
    assert config.logging.level == "INFO"
    assert config.logging.file == "~/Documents/SnapLog/app.log"


def test_path_expansion():
    """パス展開（~）のテスト"""
    config = Config()
    config.expand_paths()
    
    # ~が展開されていることを確認
    assert not config.storage.base_dir.startswith("~")
    assert not config.capture.temp_dir.startswith("~")
    assert not config.logging.file.startswith("~")
    
    # 実際のパスが存在するか確認（存在しなくてもOK）
    assert isinstance(config.storage.base_dir, str)
    assert isinstance(config.capture.temp_dir, str)
    assert isinstance(config.logging.file, str)


def test_validation():
    """バリデーションテスト"""
    config = Config()
    
    # 正常な設定はバリデーションを通過
    config.validate()
    
    # interval < 1 の場合はエラー
    config.capture.interval = 0
    with pytest.raises(ValueError, match="capture.interval must be >= 1"):
        config.validate()
    
    # intervalを戻す
    config.capture.interval = 60
    
    # 無効なmodeの場合はエラー
    config.capture.mode = "invalid_mode"
    with pytest.raises(ValueError, match="capture.mode must be"):
        config.validate()
    
    # modeを戻す
    config.capture.mode = "fullscreen"
    
    # retention_days < 1 の場合はエラー
    config.storage.retention_days = 0
    with pytest.raises(ValueError, match="storage.retention_days must be >= 1"):
        config.validate()
    
    # retention_daysを戻す
    config.storage.retention_days = 14
    
    # 無効なlogging.levelの場合はエラー
    config.logging.level = "INVALID"
    with pytest.raises(ValueError, match="logging.level must be"):
        config.validate()


def test_load_config_no_file():
    """設定ファイルが存在しない場合のテスト"""
    # 存在しないパスを指定
    config = load_config(config_path="/nonexistent/path/settings.yaml")
    
    # デフォルト値が使用されることを確認
    assert config.capture.interval == 60
    assert config.storage.retention_days == 14


def test_load_config_with_file():
    """設定ファイル読み込みのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.yaml"
        
        # テスト用の設定ファイルを作成
        test_config = {
            "capture": {
                "interval": 30,
                "mode": "active_window",
                "temp_dir": "/tmp/test"
            },
            "storage": {
                "base_dir": "~/Test/SnapLog",
                "retention_days": 7,
                "cleanup_on_start": False
            },
            "filter": {
                "exclude_apps": ["TestApp"],
                "exclude_title_keywords": ["test"],
                "exclude_patterns": [r"\d{4}"]
            },
            "logging": {
                "level": "DEBUG",
                "file": "~/Test/app.log"
            }
        }
        
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(test_config, f)
        
        # 設定を読み込み
        config = load_config(config_path=str(config_file))
        
        # 設定が正しく読み込まれていることを確認
        assert config.capture.interval == 30
        assert config.capture.mode == "active_window"
        assert config.capture.temp_dir == "/tmp/test"
        
        assert config.storage.base_dir == os.path.expanduser("~/Test/SnapLog")
        assert config.storage.retention_days == 7
        assert config.storage.cleanup_on_start is False
        
        assert config.filter.exclude_apps == ["TestApp"]
        assert config.filter.exclude_title_keywords == ["test"]
        assert config.filter.exclude_patterns == [r"\d{4}"]
        
        assert config.logging.level == "DEBUG"
        assert config.logging.file == os.path.expanduser("~/Test/app.log")


def test_load_config_partial():
    """部分的な設定ファイルのテスト（一部の設定のみ）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.yaml"
        
        # 一部の設定のみを含むファイル
        test_config = {
            "capture": {
                "interval": 120
            }
        }
        
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(test_config, f)
        
        # 設定を読み込み
        config = load_config(config_path=str(config_file))
        
        # 指定された設定が読み込まれていることを確認
        assert config.capture.interval == 120
        
        # 指定されていない設定はデフォルト値が使用されることを確認
        assert config.capture.mode == "fullscreen"
        assert config.storage.retention_days == 14
        assert config.logging.level == "INFO"


"""日報前処理モジュールのテスト"""
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.report_preprocess import (
    load_logs_by_date,
    parse_timestamp,
    split_into_sessions,
    group_by_app_and_window,
    mask_sensitive_info,
    format_logs_for_llm,
    split_into_chunks,
    preprocess_logs,
)


def test_parse_timestamp():
    """タイムスタンプパースのテスト"""
    # ISO 8601形式（タイムゾーン付き）
    ts_str = "2025-01-15T14:32:00+09:00"
    dt = parse_timestamp(ts_str)
    assert isinstance(dt, datetime)
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 15
    
    # UTC形式（Z付き）
    ts_str = "2025-01-15T14:32:00Z"
    dt = parse_timestamp(ts_str)
    assert isinstance(dt, datetime)


def test_load_logs_by_date():
    """ログ読み込みのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"
        log_dir.mkdir()
        
        log_file = log_dir / "activity_log_2025-01-15.jsonl"
        
        # テスト用のログエントリを作成
        entries = [
            {
                "timestamp": "2025-01-15T10:00:00+09:00",
                "app_name": "Cursor",
                "window_title": "test.py",
                "ocr_text": "def test():",
                "ocr_length": 10
            },
            {
                "timestamp": "2025-01-15T10:05:00+09:00",
                "app_name": "Browser",
                "window_title": "Example",
                "ocr_text": "Hello World",
                "ocr_length": 11
            }
        ]
        
        # JSONLファイルに書き込み
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        # ログを読み込み
        logs = load_logs_by_date(tmpdir, "logs", "2025-01-15")
        
        assert len(logs) == 2
        assert logs[0]["app_name"] == "Cursor"
        assert logs[1]["app_name"] == "Browser"


def test_load_logs_by_date_not_exists():
    """存在しないログファイルのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs = load_logs_by_date(tmpdir, "logs", "2025-01-15")
        assert logs == []


def test_split_into_sessions():
    """セッション分割のテスト"""
    logs = [
        {
            "timestamp": "2025-01-15T10:00:00+09:00",
            "app_name": "App1",
            "window_title": "Window1",
            "ocr_text": "text1",
            "ocr_length": 5
        },
        {
            "timestamp": "2025-01-15T10:05:00+09:00",
            "app_name": "App1",
            "window_title": "Window1",
            "ocr_text": "text2",
            "ocr_length": 5
        },
        # 15分の空き（10分以上なので分割）
        {
            "timestamp": "2025-01-15T10:20:00+09:00",
            "app_name": "App2",
            "window_title": "Window2",
            "ocr_text": "text3",
            "ocr_length": 5
        }
    ]
    
    sessions = split_into_sessions(logs, gap_minutes=10)
    
    assert len(sessions) == 2
    assert len(sessions[0]) == 2
    assert len(sessions[1]) == 1


def test_split_into_sessions_no_gap():
    """空きがない場合のセッション分割テスト"""
    logs = [
        {
            "timestamp": "2025-01-15T10:00:00+09:00",
            "app_name": "App1",
            "window_title": "Window1",
            "ocr_text": "text1",
            "ocr_length": 5
        },
        {
            "timestamp": "2025-01-15T10:05:00+09:00",
            "app_name": "App1",
            "window_title": "Window1",
            "ocr_text": "text2",
            "ocr_length": 5
        }
    ]
    
    sessions = split_into_sessions(logs, gap_minutes=10)
    
    assert len(sessions) == 1
    assert len(sessions[0]) == 2


def test_group_by_app_and_window():
    """アプリ・ウィンドウでのグルーピングテスト"""
    logs = [
        {
            "timestamp": "2025-01-15T10:00:00+09:00",
            "app_name": "Cursor",
            "window_title": "test.py",
            "ocr_text": "def test():",
            "ocr_length": 10
        },
        {
            "timestamp": "2025-01-15T10:05:00+09:00",
            "app_name": "Cursor",
            "window_title": "test.py",
            "ocr_text": "print('hello')",
            "ocr_length": 15
        },
        {
            "timestamp": "2025-01-15T10:10:00+09:00",
            "app_name": "Browser",
            "window_title": "Example",
            "ocr_text": "Hello World",
            "ocr_length": 11
        }
    ]
    
    grouped = group_by_app_and_window(logs)
    
    assert len(grouped) == 2
    assert grouped[0]["app_name"] == "Cursor"
    assert grouped[0]["window_title"] == "test.py"
    assert len(grouped[0]["entries"]) == 2
    assert grouped[0]["total_chars"] == 25  # 10 + 15
    
    assert grouped[1]["app_name"] == "Browser"
    assert grouped[1]["window_title"] == "Example"
    assert len(grouped[1]["entries"]) == 1
    assert grouped[1]["total_chars"] == 11


def test_mask_sensitive_info():
    """個人情報マスキングのテスト"""
    text = "メールアドレスは test@example.com です。URLは https://example.com です。"
    masked = mask_sensitive_info(text)
    
    assert "[EMAIL]" in masked
    assert "[URL]" in masked
    assert "test@example.com" not in masked
    assert "https://example.com" not in masked


def test_format_logs_for_llm():
    """LLM入力用テキスト整形のテスト"""
    grouped_logs = [
        {
            "app_name": "Cursor",
            "window_title": "test.py",
            "start_time": "2025-01-15T10:00:00+09:00",
            "end_time": "2025-01-15T10:05:00+09:00",
            "entries": [
                {
                    "timestamp": "2025-01-15T10:00:00+09:00",
                    "ocr_text": "def test():"
                }
            ],
            "total_chars": 10
        }
    ]
    
    formatted = format_logs_for_llm(grouped_logs, mask_sensitive=False)
    
    assert "【Cursor】" in formatted
    assert "test.py" in formatted
    assert "def test():" in formatted


def test_split_into_chunks():
    """チャンク分割のテスト"""
    # 短いテキスト（分割不要）
    short_text = "短いテキスト"
    chunks = split_into_chunks(short_text, max_chars=100)
    assert len(chunks) == 1
    assert chunks[0] == short_text
    
    # 長いテキスト（分割必要）
    long_text = "a" * 15000  # 15000文字
    chunks = split_into_chunks(long_text, max_chars=5000)
    assert len(chunks) > 1
    # 各チャンクがmax_chars以下であることを確認
    for chunk in chunks:
        assert len(chunk) <= 5000


def test_preprocess_logs():
    """前処理統合テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"
        log_dir.mkdir()
        
        log_file = log_dir / "activity_log_2025-01-15.jsonl"
        
        # テスト用のログエントリを作成
        entries = [
            {
                "timestamp": "2025-01-15T10:00:00+09:00",
                "app_name": "Cursor",
                "window_title": "test.py",
                "ocr_text": "def test():",
                "ocr_length": 10
            },
            {
                "timestamp": "2025-01-15T10:05:00+09:00",
                "app_name": "Browser",
                "window_title": "Example",
                "ocr_text": "Hello World",
                "ocr_length": 11
            }
        ]
        
        # JSONLファイルに書き込み
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        # 前処理実行
        chunks = preprocess_logs(
            base_dir=tmpdir,
            log_subdir="logs",
            target_date="2025-01-15",
            group_gap_minutes=10,
            chunk_chars=1000,
            mask_sensitive=False
        )
        
        assert len(chunks) > 0
        assert isinstance(chunks[0], str)


def test_preprocess_logs_empty():
    """ログが空の場合のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        chunks = preprocess_logs(
            base_dir=tmpdir,
            log_subdir="logs",
            target_date="2025-01-15",
            group_gap_minutes=10,
            chunk_chars=1000,
            mask_sensitive=False
        )
        
        assert chunks == []


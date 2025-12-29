"""ストレージモジュールのテスト"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.storage import (
    save_log,
    cleanup_old_files,
    ensure_directories,
)
from src.window_info import WindowInfo


def test_save_log():
    """JSONL追記のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        
        window = WindowInfo(
            app_name="Cursor",
            window_title="main.py - TestProject"
        )
        ocr_text = "def test_function(): pass"
        
        # ログを保存
        save_log(window, ocr_text, base_dir, log_subdir)
        
        # ファイルが作成されていることを確認
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(base_dir) / log_subdir / f"activity_log_{today}.jsonl"
        assert log_file.exists()
        
        # ファイルの内容を確認
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            log_entry = json.loads(lines[0])
            assert log_entry["app_name"] == "Cursor"
            assert log_entry["window_title"] == "main.py - TestProject"
            assert log_entry["ocr_text"] == "def test_function(): pass"
            assert log_entry["ocr_length"] == len(ocr_text)
            assert "timestamp" in log_entry
            # タイムスタンプがISO 8601形式であることを確認
            assert "T" in log_entry["timestamp"]
        
        # 複数回追記できることを確認
        window2 = WindowInfo(app_name="Browser", window_title="Example")
        ocr_text2 = "Hello World"
        save_log(window2, ocr_text2, base_dir, log_subdir)
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            log_entry2 = json.loads(lines[1])
            assert log_entry2["app_name"] == "Browser"
            assert log_entry2["ocr_text"] == "Hello World"


def test_save_log_utf8():
    """UTF-8文字（日本語）の保存テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        
        window = WindowInfo(
            app_name="ブラウザ",
            window_title="テスト - 日本語"
        )
        ocr_text = "これは日本語のテキストです。"
        
        save_log(window, ocr_text, base_dir, log_subdir)
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(base_dir) / log_subdir / f"activity_log_{today}.jsonl"
        
        with open(log_file, "r", encoding="utf-8") as f:
            log_entry = json.loads(f.readline())
            assert log_entry["app_name"] == "ブラウザ"
            assert log_entry["window_title"] == "テスト - 日本語"
            assert log_entry["ocr_text"] == "これは日本語のテキストです。"


def test_save_log_lf_newline():
    """LF改行コードのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        
        window = WindowInfo(app_name="Test", window_title="Test")
        ocr_text = "test"
        
        save_log(window, ocr_text, base_dir, log_subdir)
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(base_dir) / log_subdir / f"activity_log_{today}.jsonl"
        
        # ファイルをバイナリモードで読み込んで改行コードを確認
        with open(log_file, "rb") as f:
            content = f.read()
            # LF（\n）が使用されていることを確認（CRLF（\r\n）ではない）
            assert b"\r\n" not in content
            assert b"\n" in content


def test_save_log_date_format():
    """日付別ファイル名のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        
        window = WindowInfo(app_name="Test", window_title="Test")
        ocr_text = "test"
        
        save_log(window, ocr_text, base_dir, log_subdir)
        
        # ファイル名が正しい形式であることを確認
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(base_dir) / log_subdir / f"activity_log_{today}.jsonl"
        assert log_file.exists()
        
        # ファイル名の形式を確認
        assert log_file.name.startswith("activity_log_")
        assert log_file.name.endswith(".jsonl")
        assert today in log_file.name


def test_ensure_directories():
    """ディレクトリ作成のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        report_subdir = "reports"
        
        # ディレクトリが存在しないことを確認
        log_dir = Path(base_dir) / log_subdir
        report_dir = Path(base_dir) / report_subdir
        assert not log_dir.exists()
        assert not report_dir.exists()
        
        # ディレクトリを作成
        ensure_directories(base_dir, log_subdir, report_subdir)
        
        # ディレクトリが作成されていることを確認
        assert log_dir.exists()
        assert log_dir.is_dir()
        assert report_dir.exists()
        assert report_dir.is_dir()
        
        # 既に存在するディレクトリでもエラーにならないことを確認
        ensure_directories(base_dir, log_subdir, report_subdir)


def test_cleanup_old_files():
    """リテンション削除のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        report_subdir = "reports"
        retention_days = 7
        
        # ディレクトリを作成
        log_dir = Path(base_dir) / log_subdir
        report_dir = Path(base_dir) / report_subdir
        log_dir.mkdir(parents=True)
        report_dir.mkdir(parents=True)
        
        # 古いファイルを作成（15日前）
        old_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        old_log_file = log_dir / f"activity_log_{old_date}.jsonl"
        old_report_file = report_dir / f"report_{old_date}.md"
        
        old_log_file.write_text("old log")
        old_report_file.write_text("old report")
        
        # ファイルの更新日時を15日前に設定
        old_timestamp = (datetime.now() - timedelta(days=15)).timestamp()
        os.utime(old_log_file, (old_timestamp, old_timestamp))
        os.utime(old_report_file, (old_timestamp, old_timestamp))
        
        # 新しいファイルを作成（3日前）
        new_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        new_log_file = log_dir / f"activity_log_{new_date}.jsonl"
        new_report_file = report_dir / f"report_{new_date}.md"
        
        new_log_file.write_text("new log")
        new_report_file.write_text("new report")
        
        new_timestamp = (datetime.now() - timedelta(days=3)).timestamp()
        os.utime(new_log_file, (new_timestamp, new_timestamp))
        os.utime(new_report_file, (new_timestamp, new_timestamp))
        
        # クリーンアップを実行
        deleted_count = cleanup_old_files(
            base_dir=base_dir,
            log_subdir=log_subdir,
            report_subdir=report_subdir,
            retention_days=retention_days
        )
        
        # 古いファイルが削除されていることを確認
        assert not old_log_file.exists()
        assert not old_report_file.exists()
        
        # 新しいファイルが残っていることを確認
        assert new_log_file.exists()
        assert new_report_file.exists()
        
        # 削除されたファイル数が正しいことを確認
        assert deleted_count == 2


def test_cleanup_old_files_nonexistent_dir():
    """存在しないディレクトリでのクリーンアップテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "nonexistent"
        
        # ディレクトリが存在しない場合でもエラーにならないことを確認
        deleted_count = cleanup_old_files(
            base_dir=str(base_dir),
            log_subdir="logs",
            report_subdir="reports",
            retention_days=7
        )
        
        assert deleted_count == 0


def test_save_log_creates_directories():
    """save_logがディレクトリを自動作成するテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = tmpdir
        log_subdir = "logs"
        
        # ディレクトリが存在しないことを確認
        log_dir = Path(base_dir) / log_subdir
        assert not log_dir.exists()
        
        # save_logを呼び出すとディレクトリが作成される
        window = WindowInfo(app_name="Test", window_title="Test")
        ocr_text = "test"
        save_log(window, ocr_text, base_dir, log_subdir)
        
        # ディレクトリが作成されていることを確認
        assert log_dir.exists()
        assert log_dir.is_dir()


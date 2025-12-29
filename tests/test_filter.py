"""フィルタモジュールのテスト"""
import pytest

from src.config import Config, FilterConfig
from src.filter import should_exclude_pre_capture, should_exclude_post_capture
from src.window_info import WindowInfo


def test_exclude_by_app_name():
    """アプリ名による除外判定のテスト"""
    config = Config()
    config.filter.exclude_apps = ["1Password", "Keychain Access"]
    
    # 除外対象のアプリ名
    window = WindowInfo(app_name="1Password", window_title="Password Manager")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is True
    assert "1Password" in reason
    
    # 除外対象外のアプリ名
    window = WindowInfo(app_name="Cursor", window_title="main.py")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is False
    assert reason is None


def test_exclude_by_window_title():
    """ウィンドウタイトルによる除外判定のテスト"""
    config = Config()
    config.filter.exclude_title_keywords = ["銀行", "クレジットカード", "Password"]
    
    # 除外対象のタイトル（部分一致）
    window = WindowInfo(app_name="Browser", window_title="銀行ログイン")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is True
    assert "銀行" in reason
    
    # 除外対象外のタイトル
    window = WindowInfo(app_name="Browser", window_title="ニュースサイト")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is False
    assert reason is None


def test_exclude_by_app_name_and_title():
    """アプリ名とタイトルの両方で除外判定のテスト"""
    config = Config()
    config.filter.exclude_apps = ["1Password"]
    config.filter.exclude_title_keywords = ["銀行"]
    
    # アプリ名で除外
    window = WindowInfo(app_name="1Password", window_title="Any Title")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is True
    
    # タイトルで除外
    window = WindowInfo(app_name="Browser", window_title="銀行サイト")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is True
    
    # どちらでも除外されない
    window = WindowInfo(app_name="Browser", window_title="ニュース")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is False


def test_exclude_by_ocr_pattern():
    """OCR結果による除外判定（正規表現）のテスト"""
    config = Config()
    config.filter.exclude_patterns = [
        r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',  # クレカ番号
        r'\d{2,4}-\d{2,4}-\d{4}'  # 電話番号
    ]
    
    # クレカ番号が含まれるテキスト
    ocr_text = "カード番号: 1234 5678 9012 3456"
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    assert should_exclude is True
    assert "パターン" in reason
    
    # 電話番号が含まれるテキスト
    ocr_text = "電話番号: 03-1234-5678"
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    assert should_exclude is True
    
    # 除外パターンが含まれないテキスト
    ocr_text = "これは通常のテキストです。"
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    assert should_exclude is False
    assert reason is None


def test_exclude_empty_ocr_text():
    """空のOCR結果のテスト"""
    config = Config()
    config.filter.exclude_patterns = [r'\d{4}']
    
    # 空文字列
    ocr_text = ""
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    assert should_exclude is False
    
    # None（実際にはstr型なので空文字列として扱う）
    ocr_text = ""
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    assert should_exclude is False


def test_invalid_regex_pattern():
    """無効な正規表現パターンのエラーハンドリングテスト"""
    config = Config()
    config.filter.exclude_patterns = [
        r'\d{4}',  # 有効なパターン
        r'[invalid',  # 無効なパターン（開き括弧が閉じられていない）
        r'\d{3}'  # 有効なパターン
    ]
    
    # 無効なパターンはスキップされ、有効なパターンでマッチングが行われる
    ocr_text = "1234"
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    # 有効なパターンでマッチするので除外される
    assert should_exclude is True
    
    # 無効なパターンだけの場合
    config.filter.exclude_patterns = [r'[invalid']
    ocr_text = "any text"
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    # 無効なパターンはスキップされるので除外されない
    assert should_exclude is False


def test_no_exclude_config():
    """除外設定が空の場合のテスト"""
    config = Config()
    # デフォルトでは除外リストは空
    
    window = WindowInfo(app_name="AnyApp", window_title="AnyTitle")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is False
    
    ocr_text = "any text"
    should_exclude, reason = should_exclude_post_capture(ocr_text, config)
    assert should_exclude is False


def test_empty_app_name():
    """空のアプリ名のテスト"""
    config = Config()
    config.filter.exclude_apps = ["1Password"]
    
    # 空のアプリ名
    window = WindowInfo(app_name="", window_title="Some Title")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is False


def test_empty_window_title():
    """空のウィンドウタイトルのテスト"""
    config = Config()
    config.filter.exclude_title_keywords = ["銀行"]
    
    # 空のタイトル
    window = WindowInfo(app_name="Browser", window_title="")
    should_exclude, reason = should_exclude_pre_capture(window, config)
    assert should_exclude is False


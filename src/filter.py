"""フィルタモジュール（除外判定）"""
import logging
import re
from typing import Optional, Tuple

from .config import Config
from .window_info import WindowInfo

logger = logging.getLogger("snaplog.filter")

# 正規表現パターンのキャッシュ（モジュールレベル）
_compiled_patterns_cache: dict[str, re.Pattern] = {}


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    """
    正規表現パターンをコンパイル（キャッシュ付き）
    
    Args:
        patterns: 正規表現パターンのリスト
        
    Returns:
        list[re.Pattern]: コンパイル済みパターンのリスト（無効なパターンは除外）
    """
    compiled = []
    
    for pattern_str in patterns:
        # キャッシュをチェック
        if pattern_str in _compiled_patterns_cache:
            compiled.append(_compiled_patterns_cache[pattern_str])
            continue
        
        # パターンをコンパイル
        try:
            pattern = re.compile(pattern_str)
            _compiled_patterns_cache[pattern_str] = pattern
            compiled.append(pattern)
        except re.error as e:
            logger.warning(f"無効な正規表現パターンをスキップしました: {pattern_str}, エラー: {e}")
            continue
    
    return compiled


def should_exclude_pre_capture(window_info: WindowInfo, config: Config) -> Tuple[bool, Optional[str]]:
    """
    キャプチャ前の除外判定（アプリ名・ウィンドウタイトル）
    
    Args:
        window_info: ウィンドウ情報
        config: 設定オブジェクト
        
    Returns:
        Tuple[bool, Optional[str]]: (除外するかどうか, 除外理由)
    """
    # 許可リスト（allowlist）チェック: リストが空でない場合、リストに含まれるアプリのみ記録
    if config.filter.allow_apps:
        if not window_info.app_name or window_info.app_name not in config.filter.allow_apps:
            reason = f"アプリ名が許可リストに含まれていない: {window_info.app_name}"
            if config.filter.log_exclusion_reason:
                logger.debug(reason)
            return True, reason
    
    # アプリ名の完全一致チェック（除外リスト）
    if window_info.app_name and config.filter.exclude_apps:
        for exclude_app in config.filter.exclude_apps:
            if window_info.app_name == exclude_app:
                reason = f"アプリ名が除外リストに一致: {exclude_app}"
                if config.filter.log_exclusion_reason:
                    logger.debug(reason)
                return True, reason
    
    # ウィンドウタイトルの部分一致チェック
    if window_info.window_title and config.filter.exclude_title_keywords:
        for keyword in config.filter.exclude_title_keywords:
            if keyword in window_info.window_title:
                reason = f"ウィンドウタイトルに除外キーワードが含まれる: {keyword}"
                if config.filter.log_exclusion_reason:
                    logger.debug(reason)
                return True, reason
    
    return False, None


def should_exclude_post_capture(ocr_text: str, config: Config) -> Tuple[bool, Optional[str]]:
    """
    キャプチャ後の除外判定（OCR結果の正規表現）
    
    Args:
        ocr_text: OCRで抽出されたテキスト
        config: 設定オブジェクト
        
    Returns:
        Tuple[bool, Optional[str]]: (除外するかどうか, 除外理由)
    """
    if not ocr_text or not config.filter.exclude_patterns:
        return False, None
    
    # 正規表現パターンをコンパイル
    compiled_patterns = _compile_patterns(config.filter.exclude_patterns)
    
    if not compiled_patterns:
        return False, None
    
    # OCR結果に対して各パターンをチェック
    for pattern in compiled_patterns:
        try:
            if pattern.search(ocr_text):
                reason = f"OCR結果に除外パターンが一致: {pattern.pattern}"
                if config.filter.log_exclusion_reason:
                    logger.debug(reason)
                return True, reason
        except Exception as e:
            logger.warning(f"正規表現マッチング中にエラーが発生しました: {pattern.pattern}, エラー: {e}")
            continue
    
    return False, None


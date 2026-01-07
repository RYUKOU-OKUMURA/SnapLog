"""フィルタモジュール（除外判定・重複排除・UIノイズ除去）"""
import logging
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple

from .config import Config
from .window_info import WindowInfo

logger = logging.getLogger("snaplog.filter")

# 正規表現パターンのキャッシュ（モジュールレベル）
_compiled_patterns_cache: dict[str, re.Pattern] = {}

# 前回のOCRテキストを保持（重複排除用）
_last_ocr_text: Optional[str] = None
_last_app_name: Optional[str] = None


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


def calculate_similarity(text1: str, text2: str) -> float:
    """
    2つのテキストの類似度を計算（0.0〜1.0）

    Args:
        text1: テキスト1
        text2: テキスト2

    Returns:
        float: 類似度（0.0〜1.0）
    """
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1, text2).ratio()


def is_duplicate(
    ocr_text: str,
    app_name: str,
    config: Config
) -> Tuple[bool, Optional[str]]:
    """
    重複判定（前回のOCRテキストとの類似度チェック）

    Args:
        ocr_text: 現在のOCRテキスト
        app_name: 現在のアプリ名
        config: 設定オブジェクト

    Returns:
        Tuple[bool, Optional[str]]: (重複かどうか, 理由)
    """
    global _last_ocr_text, _last_app_name

    threshold = config.filter.similarity_threshold

    # 前回と同じアプリで、類似度が閾値以上なら重複
    if _last_ocr_text and _last_app_name == app_name:
        similarity = calculate_similarity(ocr_text, _last_ocr_text)
        if similarity >= threshold:
            reason = f"重複検出: 類似度 {similarity:.2%} >= {threshold:.0%}"
            if config.filter.log_exclusion_reason:
                logger.debug(reason)
            return True, reason

    # 重複でない場合は現在の状態を保存
    _last_ocr_text = ocr_text
    _last_app_name = app_name

    return False, None


def remove_ui_noise(ocr_text: str, config: Config) -> str:
    """
    OCRテキストからUIノイズを除去

    Args:
        ocr_text: 元のOCRテキスト
        config: 設定オブジェクト

    Returns:
        str: ノイズ除去後のテキスト
    """
    if not ocr_text or not config.filter.ui_noise_patterns:
        return ocr_text

    # パターンをコンパイル
    compiled_patterns = _compile_patterns(config.filter.ui_noise_patterns)

    # 行ごとに処理
    lines = ocr_text.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # パターンにマッチする行はスキップ
        should_remove = False
        for pattern in compiled_patterns:
            if pattern.match(stripped):
                should_remove = True
                break

        if not should_remove:
            cleaned_lines.append(stripped)

    return '\n'.join(cleaned_lines)


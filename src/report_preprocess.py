"""日報生成前処理モジュール"""
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("snaplog.report_preprocess")


def load_logs_by_date(
    base_dir: str,
    log_subdir: str,
    target_date: str
) -> List[Dict]:
    """
    指定日のログを読み込む
    
    Args:
        base_dir: ベースディレクトリ
        log_subdir: ログサブディレクトリ名
        target_date: 対象日（YYYY-MM-DD形式）
        
    Returns:
        List[Dict]: ログエントリのリスト
    """
    log_dir = Path(base_dir) / log_subdir
    log_file = log_dir / f"activity_log_{target_date}.jsonl"
    
    if not log_file.exists():
        logger.warning(f"ログファイルが存在しません: {log_file}")
        return []
    
    logs = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    logs.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"ログファイルの{line_num}行目をパースできませんでした: {e}")
                    continue
    except Exception as e:
        logger.error(f"ログファイル読み込み中にエラーが発生しました: {log_file}, エラー: {e}")
        raise
    
    logger.info(f"{target_date}のログを{len(logs)}件読み込みました")
    return logs


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    タイムスタンプ文字列をdatetimeオブジェクトに変換
    
    Args:
        timestamp_str: ISO 8601形式のタイムスタンプ
        
    Returns:
        datetime: datetimeオブジェクト
    """
    try:
        # ISO 8601形式をパース（タイムゾーン付き）
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception as e:
        logger.warning(f"タイムスタンプのパースに失敗しました: {timestamp_str}, エラー: {e}")
        # フォールバック: 現在時刻
        return datetime.now()


def split_into_sessions(
    logs: List[Dict],
    gap_minutes: int = 10
) -> List[List[Dict]]:
    """
    ログをセッションに分割（指定時間以上の空きで分割）
    
    Args:
        logs: ログエントリのリスト（タイムスタンプでソート済み）
        gap_minutes: セッション分割の閾値（分）
        
    Returns:
        List[List[Dict]]: セッションごとに分割されたログのリスト
    """
    if not logs:
        return []
    
    # タイムスタンプでソート
    sorted_logs = sorted(logs, key=lambda x: parse_timestamp(x.get("timestamp", "")))
    
    sessions = []
    current_session = [sorted_logs[0]]
    
    for i in range(1, len(sorted_logs)):
        prev_time = parse_timestamp(sorted_logs[i - 1]["timestamp"])
        curr_time = parse_timestamp(sorted_logs[i]["timestamp"])
        
        gap = curr_time - prev_time
        
        if gap >= timedelta(minutes=gap_minutes):
            # セッション分割
            sessions.append(current_session)
            current_session = [sorted_logs[i]]
        else:
            current_session.append(sorted_logs[i])
    
    # 最後のセッションを追加
    if current_session:
        sessions.append(current_session)
    
    logger.info(f"ログを{len(sessions)}セッションに分割しました（閾値: {gap_minutes}分）")
    return sessions


def group_by_app_and_window(logs: List[Dict]) -> List[Dict]:
    """
    アプリ名とウィンドウタイトルでログをグルーピング
    
    Args:
        logs: ログエントリのリスト
        
    Returns:
        List[Dict]: グルーピングされたログ（各グループに`group_key`, `entries`, `total_chars`を含む）
    """
    groups = {}
    
    for entry in logs:
        app_name = entry.get("app_name", "Unknown")
        window_title = entry.get("window_title", "")
        ocr_text = entry.get("ocr_text", "")
        
        # グループキー生成
        group_key = f"{app_name}::{window_title}"
        
        if group_key not in groups:
            groups[group_key] = {
                "app_name": app_name,
                "window_title": window_title,
                "entries": [],
                "total_chars": 0,
                "start_time": entry.get("timestamp", ""),
                "end_time": entry.get("timestamp", "")
            }
        
        groups[group_key]["entries"].append(entry)
        groups[group_key]["total_chars"] += len(ocr_text)
        
        # 開始時刻・終了時刻を更新
        entry_time = entry.get("timestamp", "")
        if entry_time < groups[group_key]["start_time"]:
            groups[group_key]["start_time"] = entry_time
        if entry_time > groups[group_key]["end_time"]:
            groups[group_key]["end_time"] = entry_time
    
    # リストに変換して返す
    grouped_list = list(groups.values())
    
    # 開始時刻でソート
    grouped_list.sort(key=lambda x: x["start_time"])
    
    logger.info(f"ログを{len(grouped_list)}グループに分類しました")
    return grouped_list


def mask_sensitive_info(text: str) -> str:
    """
    個人情報っぽいパターンをマスキング（任意の追加マスキング）
    
    Args:
        text: テキスト
        
    Returns:
        str: マスキング後のテキスト
    """
    # メールアドレス
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # URL
    text = re.sub(r'https?://[^\s]+', '[URL]', text)
    
    # クレジットカード番号（既にフィルタで除外されているはずだが念のため）
    text = re.sub(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', '[CARD]', text)
    
    return text


def format_logs_for_llm(
    grouped_logs: List[Dict],
    mask_sensitive: bool = False
) -> str:
    """
    グルーピングされたログをLLM入力用のテキストに整形
    
    Args:
        grouped_logs: グルーピングされたログ
        mask_sensitive: 個人情報をマスキングするか
        
    Returns:
        str: LLM入力用のテキスト
    """
    lines = []
    
    for group in grouped_logs:
        app_name = group["app_name"]
        window_title = group["window_title"]
        start_time = group["start_time"]
        end_time = group["end_time"]
        entries = group["entries"]
        total_chars = group["total_chars"]
        
        # グループヘッダー
        lines.append(f"【{app_name}】")
        if window_title:
            lines.append(f"ウィンドウ: {window_title}")
        lines.append(f"時間: {start_time} ～ {end_time}")
        lines.append(f"エントリ数: {len(entries)}, 総文字数: {total_chars}")
        lines.append("")
        
        # OCRテキストを結合
        ocr_texts = []
        for entry in entries:
            ocr_text = entry.get("ocr_text", "")
            if ocr_text:
                if mask_sensitive:
                    ocr_text = mask_sensitive_info(ocr_text)
                ocr_texts.append(ocr_text)
        
        if ocr_texts:
            combined_text = "\n".join(ocr_texts)
            lines.append(combined_text)
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def split_into_chunks(
    text: str,
    max_chars: int = 12000
) -> List[str]:
    """
    テキストを指定文字数以下に分割（LLM投入上限対策）
    
    Args:
        text: 分割するテキスト
        max_chars: 最大文字数
        
    Returns:
        List[str]: 分割されたテキストのリスト
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_length = 0
    
    for line in lines:
        line_length = len(line) + 1  # +1 for newline
        
        if current_length + line_length > max_chars and current_chunk:
            # 現在のチャンクを保存
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length
    
    # 最後のチャンクを追加
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    logger.info(f"テキストを{len(chunks)}チャンクに分割しました（最大文字数: {max_chars}）")
    return chunks


def preprocess_logs(
    base_dir: str,
    log_subdir: str,
    target_date: str,
    group_gap_minutes: int = 10,
    chunk_chars: int = 12000,
    mask_sensitive: bool = False
) -> List[str]:
    """
    ログを前処理してLLM投入用のチャンクに分割
    
    Args:
        base_dir: ベースディレクトリ
        log_subdir: ログサブディレクトリ名
        target_date: 対象日（YYYY-MM-DD形式）
        group_gap_minutes: セッション分割の閾値（分）
        chunk_chars: LLM投入用の最大文字数
        mask_sensitive: 個人情報をマスキングするか
        
    Returns:
        List[str]: LLM投入用のチャンクリスト
    """
    # 1. ログ読み込み
    logs = load_logs_by_date(base_dir, log_subdir, target_date)
    
    if not logs:
        logger.warning(f"{target_date}のログがありません")
        return []
    
    # 2. セッション分割
    sessions = split_into_sessions(logs, group_gap_minutes)
    
    # 3. 各セッションをグルーピング
    all_chunks = []
    
    for session_idx, session in enumerate(sessions):
        grouped = group_by_app_and_window(session)
        
        # 4. LLM入力用テキストに整形
        formatted_text = format_logs_for_llm(grouped, mask_sensitive)
        
        # 5. チャンク分割
        chunks = split_into_chunks(formatted_text, chunk_chars)
        
        # セッション番号を付与（複数セッションがある場合）
        if len(sessions) > 1:
            for i, chunk in enumerate(chunks):
                header = f"【セッション {session_idx + 1}/{len(sessions)}】\n\n"
                chunks[i] = header + chunk
        
        all_chunks.extend(chunks)
    
    logger.info(f"前処理完了: {len(all_chunks)}チャンクを生成しました")
    return all_chunks


"""日報生成モジュール"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from . import config
    from . import llm_client
    from . import report_preprocess
    from . import storage
except ImportError:
    # 直接実行時用のフォールバック
    import config
    import llm_client
    import report_preprocess
    import storage

logger = logging.getLogger("snaplog.report")


def generate_report_header(date: str) -> str:
    """
    日報のヘッダーを生成
    
    Args:
        date: 対象日（YYYY-MM-DD形式）
        
    Returns:
        str: Markdown形式のヘッダー
    """
    header = f"# {date} 日報"
    return header


def combine_reports(reports: list[str], date: str) -> str:
    """
    複数の日報チャンクを結合
    
    Args:
        reports: 日報チャンクのリスト
        date: 対象日
        
    Returns:
        str: 結合された日報
    """
    header = generate_report_header(date)
    
    combined = [header]
    
    for i, report in enumerate(reports):
        if i > 0:
            combined.append("\n---\n")
            combined.append(f"## 続き（{i + 1}/{len(reports)}）\n")
        combined.append(report)
    
    return "\n".join(combined)


def build_report_filename(date: str, timestamp: Optional[str] = None) -> str:
    """
    日報ファイル名を生成

    Args:
        date: 対象日（YYYY-MM-DD形式）
        timestamp: 追加の時刻サフィックス

    Returns:
        str: ファイル名
    """
    if timestamp:
        safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
        return f"report_{date}_{safe_timestamp}.md"
    return f"report_{date}.md"


def save_report(
    report_content: str,
    base_dir: str,
    report_subdir: str,
    date: str,
    timestamp: Optional[str] = None
) -> Path:
    """
    日報をファイルに保存
    
    Args:
        report_content: 日報の内容（Markdown）
        base_dir: ベースディレクトリ
        report_subdir: レポートサブディレクトリ名
        date: 対象日（YYYY-MM-DD形式）
        
    Returns:
        Path: 保存先ファイルパス
    """
    # ディレクトリを確保
    storage.ensure_directories(base_dir, report_subdir=report_subdir)
    
    # ファイルパス生成
    report_dir = Path(base_dir) / report_subdir
    report_file = report_dir / build_report_filename(date, timestamp)
    
    # ファイルに保存
    try:
        with open(report_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(report_content)
        
        logger.info(f"日報を保存しました: {report_file}")
        return report_file
        
    except Exception as e:
        logger.error(f"日報保存中にエラーが発生しました: {report_file}, エラー: {e}")
        raise


def generate_report_for_date(
    target_date: str,
    cfg: config.Config
) -> Path:
    """
    指定日の日報を生成
    
    Args:
        target_date: 対象日（YYYY-MM-DD形式）
        cfg: 設定オブジェクト
        
    Returns:
        Path: 生成された日報ファイルのパス
        
    Raises:
        Exception: 日報生成に失敗した場合
    """
    logger.info(f"{target_date}の日報を生成します...")
    
    # 1. ログ前処理（セッション分割・グルーピング・チャンク分割）
    try:
        chunks = report_preprocess.preprocess_logs(
            base_dir=cfg.storage.base_dir,
            log_subdir=cfg.storage.log_subdir,
            target_date=target_date,
            group_gap_minutes=cfg.report.group_gap_minutes,
            chunk_chars=cfg.report.chunk_chars,
            mask_sensitive=False
        )
    except Exception as e:
        logger.error(f"ログ前処理中にエラーが発生しました: {e}")
        raise
    
    if not chunks:
        raise ValueError(f"{target_date}のログがありません")
    
    # 2. LLMクライアント作成
    try:
        client = llm_client.create_llm_client(cfg)
    except Exception as e:
        logger.error(f"LLMクライアント作成中にエラーが発生しました: {e}")
        raise
    
    # 3. 各チャンクから日報を生成
    report_chunks = []
    
    for i, chunk in enumerate(chunks):
        logger.info(f"チャンク {i + 1}/{len(chunks)} を処理中...")
        
        try:
            # LLMで日報生成
            if len(chunks) > 1:
                # 複数チャンクがある場合は、チャンク番号を追加
                chunk_with_header = f"【チャンク {i + 1}/{len(chunks)}】\n\n{chunk}"
                report_chunk = client.generate_report(chunk_with_header, target_date)
            else:
                report_chunk = client.generate_report(chunk, target_date)
            
            report_chunks.append(report_chunk)
            
        except llm_client.LLMClientError as e:
            logger.error(f"LLM日報生成に失敗しました（チャンク {i + 1}/{len(chunks)}）: {e}")
            # LLMエラーは致命的なので、エラーメッセージを追加して終了
            error_msg = f"\n\n## エラー\n\n日報生成中にエラーが発生しました: {e}\n"
            if report_chunks:
                # 既に生成されたチャンクがある場合は結合
                report_chunks.append(error_msg)
            else:
                # 全く生成できなかった場合
                raise
    
    # 4. 日報を結合
    if len(report_chunks) > 1:
        combined_report = combine_reports(report_chunks, target_date)
    else:
        header = generate_report_header(target_date)
        combined_report = header + "\n" + report_chunks[0] if report_chunks else ""
    
    # 5. ファイルに保存
    timestamp = None
    if cfg.report.add_timestamp:
        timestamp = datetime.now().strftime(cfg.report.timestamp_format)

    report_path = save_report(
        report_content=combined_report,
        base_dir=cfg.storage.base_dir,
        report_subdir=cfg.storage.report_subdir,
        date=target_date,
        timestamp=timestamp
    )
    
    logger.info(f"日報生成が完了しました: {report_path}")
    return report_path


def main():
    """メイン関数（CLIエントリーポイント）"""
    parser = argparse.ArgumentParser(description="SnapLog 日報生成")
    parser.add_argument(
        "--date",
        type=str,
        help="対象日（YYYY-MM-DD形式、省略時は今日）",
        default=None
    )
    parser.add_argument(
        "--config",
        type=str,
        help="設定ファイルのパス",
        default=None
    )
    
    args = parser.parse_args()
    
    # 設定読み込み
    try:
        cfg = config.load_config(args.config)
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}", file=sys.stderr)
        sys.exit(1)
    
    # ロギング初期化
    try:
        from . import logging as logging_module
    except ImportError:
        import logging as logging_module
    logging_module.setup_logging(cfg)
    
    # 対象日を決定
    if args.date:
        target_date = args.date
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    # 日付形式の検証
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"無効な日付形式です: {target_date}（YYYY-MM-DD形式で指定してください）")
        sys.exit(1)
    
    # 日報生成
    try:
        report_path = generate_report_for_date(target_date, cfg)
        print(f"日報を生成しました: {report_path}")
        sys.exit(0)
    except ValueError as e:
        logger.error(f"日報生成エラー: {e}")
        sys.exit(1)
    except llm_client.LLMClientError as e:
        logger.error(f"LLMエラー: {e}")
        print(f"\nエラー: {e}", file=sys.stderr)
        print("\nLLMサーバーが起動しているか確認してください:", file=sys.stderr)
        print(f"  エンドポイント: {cfg.llm.endpoint}", file=sys.stderr)
        print(f"  モデル: {cfg.llm.model}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

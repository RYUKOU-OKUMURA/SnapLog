"""SnapLog メインエントリーポイント"""
import argparse
import signal
import sys
import time
import logging
import threading

from . import config
from . import capture
from . import ocr
from . import filter as filter_module
from . import storage
from . import window_info
from . import logging as logging_module

logger = logging.getLogger("snaplog.main")

# グローバル変数: 実行フラグ（SIGINTでFalseになる）
running = True
# グローバル変数: 一時停止フラグ（pause機能用）
paused = False


def toggle_pause():
    """一時停止/再開を切り替え"""
    global paused
    paused = not paused
    logger.info(f"一時停止状態: {'一時停止中' if paused else '実行中'}")
    return paused


def set_pause(state: bool):
    """一時停止状態を設定"""
    global paused
    paused = state
    logger.info(f"一時停止状態: {'一時停止中' if paused else '実行中'}")


def signal_handler(signum, frame):
    """
    SIGINT（Ctrl+C）ハンドラ
    
    Args:
        signum: シグナル番号
        frame: スタックフレーム
    """
    global running
    logger.info("終了シグナルを受信しました。安全に終了します...")
    running = False


def run_main_loop(cfg: config.Config):
    """メインループを実行"""
    global running
    
    # 起動時クリーンアップ
    if cfg.storage.cleanup_on_start:
        logger.info("起動時クリーンアップを実行します...")
        storage.cleanup_old_files(
            base_dir=cfg.storage.base_dir,
            log_subdir=cfg.storage.log_subdir,
            report_subdir=cfg.storage.report_subdir,
            retention_days=cfg.storage.retention_days
        )
    
    # ディレクトリ確保
    storage.ensure_directories(
        base_dir=cfg.storage.base_dir,
        log_subdir=cfg.storage.log_subdir,
        report_subdir=cfg.storage.report_subdir
    )
    
    # シグナルハンドラ登録（SIGINT）- メインスレッドでのみ有効
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, signal_handler)
    
    logger.info(f"キャプチャ間隔: {cfg.capture.interval}秒")
    logger.info(f"キャプチャモード: {cfg.capture.mode}")
    logger.info(f"ログ保存先: {cfg.storage.base_dir}/{cfg.storage.log_subdir}")
    
    # メインループ
    while running:
        # 一時停止チェック
        if paused:
            time.sleep(1)  # 1秒待機して再チェック
            continue

        skip = False
        image_path = None

        try:
            # 1. アクティブウィンドウ情報取得
            include_bounds = cfg.capture.mode == "active_window"
            window = window_info.get_active_window(include_bounds=include_bounds)
            logger.debug(f"アクティブウィンドウ: {window.app_name} - {window.window_title}")

            if cfg.capture.mode == "active_window" and not window.window_id:
                logger.warning("active_windowモードですがウィンドウIDを取得できませんでした。次ループへ")
                skip = True

            # 2. 除外判定①（アプリ名・タイトル）
            if not skip:
                should_exclude, reason = filter_module.should_exclude_pre_capture(window, cfg)
                if should_exclude:
                    if cfg.filter.log_exclusion_reason:
                        logger.debug(f"除外判定: {reason}")
                    skip = True

            # 3. スクリーンキャプチャ
            if not skip:
                image_path = capture.take_screenshot(
                    temp_dir=cfg.capture.temp_dir,
                    mode=cfg.capture.mode,
                    window_id=window.window_id if cfg.capture.mode == "active_window" else None,
                )
                if image_path is None:
                    logger.warning("スクリーンショット撮影に失敗しました。次ループへ")
                    skip = True

            # 4. OCR処理
            ocr_text = ""
            if not skip and image_path:
                ocr_text = ocr.extract_text(image_path)
                logger.debug(f"OCR結果: {len(ocr_text)}文字")

            # 5. 除外判定②（OCR結果）
            if not skip:
                should_exclude, reason = filter_module.should_exclude_post_capture(ocr_text, cfg)
                if should_exclude:
                    if cfg.filter.log_exclusion_reason:
                        logger.debug(f"除外判定: {reason}")
                    skip = True

            # 6. ログ保存
            if not skip:
                storage.save_log(
                    window_info=window,
                    ocr_text=ocr_text,
                    base_dir=cfg.storage.base_dir,
                    log_subdir=cfg.storage.log_subdir,
                )

        except KeyboardInterrupt:
            logger.info("キーボード割り込みを受信しました")
            running = False
            break
        except Exception as e:
            logger.error(f"メインループ中に予期しないエラーが発生しました: {e}", exc_info=True)
        finally:
            if image_path:
                try:
                    capture.delete_image(image_path)
                except Exception:
                    pass

        if running:
            time.sleep(cfg.capture.interval)
        
    logger.info("SnapLogを終了しました")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="SnapLog - 画面キャプチャと日報生成ツール")
    parser.add_argument(
        "--menu-bar",
        action="store_true",
        help="メニューバーUIを起動"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="設定ファイルのパス",
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        # 設定読み込み
        cfg = config.load_config(args.config)
        logger.info("設定ファイルを読み込みました")
        
        # ロギング初期化
        logging_module.setup_logging(cfg)
        logger.info("SnapLogを起動しました")
        
        # メニューバーUIモード
        if args.menu_bar:
            try:
                from . import menu_bar
                # メインループを別スレッドで実行
                main_thread = threading.Thread(target=run_main_loop, args=(cfg,), daemon=True)
                main_thread.start()
                # メニューバーUIをメインスレッドで実行
                menu_bar.run_menu_bar()
            except ImportError:
                logger.error("メニューバーUIにはrumpsライブラリが必要です。pip install rumps を実行してください。")
                sys.exit(1)
        else:
            # 通常モード（メインループのみ）
            run_main_loop(cfg)
        
    except Exception as e:
        logger.error(f"起動中にエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

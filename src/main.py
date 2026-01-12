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
from . import screen_state
from . import logging as logging_module

logger = logging.getLogger("snaplog.main")

# グローバル変数: 実行フラグ（SIGINTでFalseになる）
running = True
# グローバル変数: 手動一時停止フラグ
manual_paused = False
# グローバル変数: 自動一時停止フラグ
auto_paused = False
# グローバル変数: 自動再開の待機終了時刻
resume_block_until = None
# グローバル変数: 自動一時停止の理由
auto_pause_reason = ""


def toggle_pause():
    """一時停止/再開を切り替え"""
    global manual_paused
    manual_paused = not manual_paused
    logger.info(f"手動一時停止状態: {'一時停止中' if manual_paused else '実行中'}")
    return manual_paused


def set_pause(state: bool):
    """一時停止状態を設定"""
    global manual_paused
    manual_paused = state
    logger.info(f"手動一時停止状態: {'一時停止中' if manual_paused else '実行中'}")


def is_manually_paused() -> bool:
    """手動一時停止中かどうか"""
    return manual_paused


def is_resume_waiting() -> bool:
    """自動再開の待機中かどうか"""
    global resume_block_until
    if resume_block_until is None:
        return False
    if time.time() >= resume_block_until:
        resume_block_until = None
        return False
    return True


def is_effectively_paused() -> bool:
    """実効的に一時停止中かどうか"""
    return manual_paused or auto_paused or is_resume_waiting()


def get_pause_state() -> dict:
    """一時停止状態の詳細を取得"""
    return {
        "manual": manual_paused,
        "auto": auto_paused,
        "resume_waiting": is_resume_waiting(),
        "auto_reason": auto_pause_reason,
    }


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


def _get_auto_pause_reasons(cfg: config.Config) -> list:
    reasons = []
    if cfg.capture.pause_on_lock and screen_state.is_screen_locked():
        reasons.append("screen_locked")
    if cfg.capture.pause_on_display_sleep and screen_state.is_display_asleep():
        reasons.append("display_asleep")
    return reasons


def _format_auto_pause_reason(reasons: list) -> str:
    labels = {
        "screen_locked": "画面ロック中",
        "display_asleep": "ディスプレイスリープ中",
    }
    return " / ".join(labels.get(reason, reason) for reason in reasons)


def update_auto_pause_state(cfg: config.Config) -> None:
    """自動一時停止状態を更新"""
    global auto_paused, resume_block_until, auto_pause_reason

    if not cfg.capture.auto_pause:
        if auto_paused:
            auto_paused = False
            auto_pause_reason = ""
            resume_block_until = None
        return

    reasons = _get_auto_pause_reasons(cfg)
    should_pause = bool(reasons)

    if should_pause and not auto_paused:
        auto_paused = True
        auto_pause_reason = _format_auto_pause_reason(reasons)
        resume_block_until = None
        logger.info(f"自動一時停止: {auto_pause_reason}")
    elif not should_pause and auto_paused:
        auto_paused = False
        auto_pause_reason = ""
        if cfg.capture.resume_grace_sec > 0:
            resume_block_until = time.time() + cfg.capture.resume_grace_sec
            logger.info(f"自動再開: {cfg.capture.resume_grace_sec}秒待機")
        else:
            resume_block_until = None
            logger.info("自動再開")


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
        # 自動一時停止の状態更新
        update_auto_pause_state(cfg)

        # 一時停止チェック
        if is_effectively_paused():
            time.sleep(cfg.capture.paused_poll_interval)
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

            # 5. UIノイズ除去
            if not skip and ocr_text:
                original_len = len(ocr_text)
                ocr_text = filter_module.remove_ui_noise(ocr_text, cfg)
                logger.debug(f"UIノイズ除去: {original_len}文字 -> {len(ocr_text)}文字")

            # 6. 除外判定②（OCR結果）
            if not skip:
                should_exclude, reason = filter_module.should_exclude_post_capture(ocr_text, cfg)
                if should_exclude:
                    if cfg.filter.log_exclusion_reason:
                        logger.debug(f"除外判定: {reason}")
                    skip = True

            # 7. 重複判定
            if not skip:
                is_dup, reason = filter_module.is_duplicate(ocr_text, window.app_name, cfg)
                if is_dup:
                    logger.debug(f"重複スキップ: {reason}")
                    skip = True

            # 8. ログ保存
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

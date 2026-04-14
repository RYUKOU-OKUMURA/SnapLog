"""SnapLog メインエントリーポイント"""
import argparse
import fcntl
import os
import signal
import sys
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
import shutil

from . import config
from . import capture
from . import ocr
from . import filter as filter_module
from . import storage
from . import window_info
from . import screen_state
from . import logging as logging_module

logger = logging.getLogger("snaplog.main")

# デバッグ用: OCRが空になる原因の切り分け
DEBUG_OCR = os.environ.get("SNAPLOG_DEBUG_OCR") == "1"
KEEP_EMPTY_OCR_IMAGES = os.environ.get("SNAPLOG_KEEP_EMPTY_OCR_IMAGES") == "1"

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
empty_ocr_streak = 0
_instance_lock_handle = None


def _bootstrap_log(message: str, level: str = "INFO") -> None:
    """ロギング初期化前でも stderr に起動情報を残す。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        sys.stderr.write(f"{timestamp} - snaplog.bootstrap - {level} - {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def acquire_instance_lock(cfg: config.Config) -> Path:
    """複数インスタンスの同時起動を防止する。"""
    global _instance_lock_handle

    if _instance_lock_handle is not None:
        return Path(_instance_lock_handle.name)

    lock_path = Path(os.environ.get("SNAPLOG_LOCK_FILE", "/tmp/snaplog.lock"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+", encoding="utf-8")

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.seek(0)
        lock_info = handle.read().strip()
        handle.close()
        if not lock_info:
            lock_info = "lock held by another process"
        raise RuntimeError(f"別の SnapLog インスタンスが実行中です: {lock_info}")

    handle.seek(0)
    handle.truncate()
    handle.write(
        "\n".join(
            [
                f"pid={os.getpid()}",
                f"config={cfg.loaded_config_path or 'defaults'}",
                f"log_file={cfg.logging.file}",
                f"log_dir={cfg.storage.base_dir}/{cfg.storage.log_subdir}",
            ]
        )
        + "\n"
    )
    handle.flush()

    _instance_lock_handle = handle
    return lock_path


def release_instance_lock() -> None:
    """保持中のインスタンスロックを解放する。"""
    global _instance_lock_handle

    if _instance_lock_handle is None:
        return

    try:
        fcntl.flock(_instance_lock_handle.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass

    try:
        _instance_lock_handle.close()
    except Exception:
        pass

    _instance_lock_handle = None


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
    global empty_ocr_streak, running
    
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
        ocr_text = ""

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
            if not skip and image_path:
                ocr_text = ocr.extract_text(image_path)
                logger.debug(f"OCR結果: {len(ocr_text)}文字")
                if DEBUG_OCR and not ocr_text:
                    logger.warning(
                        "OCR結果が空です: app=%s title=%s",
                        window.app_name,
                        window.window_title,
                    )

            # 5. UIノイズ除去
            if not skip and ocr_text:
                original_len = len(ocr_text)
                ocr_text = filter_module.remove_ui_noise(ocr_text, cfg)
                logger.debug(f"UIノイズ除去: {original_len}文字 -> {len(ocr_text)}文字")
                if DEBUG_OCR and original_len > 0 and not ocr_text:
                    logger.warning(
                        "UIノイズ除去でOCRが空になりました: app=%s title=%s original_len=%d",
                        window.app_name,
                        window.window_title,
                        original_len,
                    )

            # 5.5 OCR空判定
            if not skip and not ocr_text.strip():
                empty_ocr_streak += 1
                logger.warning(
                    "OCR結果が空のため保存をスキップします: app=%s title=%s streak=%s",
                    window.app_name,
                    window.window_title,
                    empty_ocr_streak,
                )
                if empty_ocr_streak in (3, 10):
                    logger.warning(
                        "OCR空が連続しています。SnapLog.app の画面収録権限とアクセシビリティ権限、"
                        "および表示中の画面内容を確認してください。"
                    )
                skip = True
            elif not skip:
                empty_ocr_streak = 0

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
                if DEBUG_OCR and KEEP_EMPTY_OCR_IMAGES and not ocr_text:
                    try:
                        debug_dir = Path(cfg.storage.base_dir) / "debug"
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        debug_path = debug_dir / f"empty_ocr_{ts}.png"
                        shutil.copy2(image_path, debug_path)
                        logger.warning(f"OCR空画像を保存しました: {debug_path}")
                    except Exception as e:
                        logger.warning(f"OCR空画像の保存に失敗しました: {e}")
                try:
                    capture.delete_image(image_path)
                except Exception:
                    pass

        if running:
            time.sleep(cfg.capture.interval)

    # 終了時にセンシティブなデータをクリア（セキュリティ対策）
    filter_module.clear_sensitive_state()
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
        requested_config = args.config or os.environ.get("SNAPLOG_CONFIG")
        if requested_config:
            _bootstrap_log(f"起動開始: requested_config={requested_config}")
        else:
            _bootstrap_log("起動開始: requested_config=<default>")

        # 設定読み込み
        cfg = config.load_config(args.config)
        
        # ロギング初期化
        logging_module.setup_logging(cfg)
        lock_path = acquire_instance_lock(cfg)
        logger.info("SnapLogを起動しました")
        logger.info("設定ファイル: %s", cfg.loaded_config_path or "組み込みデフォルト")
        if cfg.config_warning:
            logger.warning(cfg.config_warning)
        logger.info("設定ソース: %s", cfg.config_source)
        logger.info("アプリログ保存先: %s", cfg.logging.file)
        logger.info("活動ログ保存先: %s/%s", cfg.storage.base_dir, cfg.storage.log_subdir)
        logger.info("インスタンスロック: %s", lock_path)

        screen_recording_permission = capture.has_screen_recording_permission()
        if screen_recording_permission is True:
            logger.info("画面収録権限: 許可済み")
        elif screen_recording_permission is False:
            logger.warning("画面収録権限: 未許可。権限要求を開始します。")
            requested_permission = capture.request_screen_recording_permission(
                open_settings_on_failure=True
            )
            if requested_permission is False:
                logger.warning(
                    "画面収録権限が有効になるまでキャプチャは失敗します。"
                    "SnapLog.app を許可した後に再起動してください。"
                )
        else:
            logger.info("画面収録権限: 事前確認不可。初回キャプチャで確認します。")
        
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
        _bootstrap_log(f"起動中にエラーが発生しました: {e}", level="ERROR")
        logger.error(f"起動中にエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)
    finally:
        release_instance_lock()


if __name__ == "__main__":
    main()

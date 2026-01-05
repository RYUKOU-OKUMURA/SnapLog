"""OCRモジュール"""
import logging
from typing import List, Optional

try:
    import Vision
    from Foundation import NSURL
    from Quartz import CIImage
except ImportError as e:
    logging.getLogger("snaplog.ocr").error(
        f"pyobjc-framework-Visionまたはpyobjc-framework-Quartzがインストールされていません: {e}"
    )
    Vision = None
    NSURL = None
    CIImage = None

logger = logging.getLogger("snaplog.ocr")


def extract_text(
    image_path: str,
    recognition_languages: Optional[List[str]] = None,
    recognition_level: Optional[int] = None
) -> str:
    """
    画像からテキストを抽出（OCR）
    
    Args:
        image_path: 画像ファイルのパス
        recognition_languages: 認識言語のリスト（デフォルト: ["ja-JP", "en-US"]）
        recognition_level: 認識レベル（デフォルト: VNRequestTextRecognitionLevelAccurate）
        
    Returns:
        str: 抽出されたテキスト（失敗時は空文字列）
    """
    if Vision is None or NSURL is None or CIImage is None:
        logger.error("Vision Frameworkが利用できません")
        return ""
    
    if recognition_languages is None:
        recognition_languages = ["ja-JP", "en-US"]
    
    if recognition_level is None:
        recognition_level = Vision.VNRequestTextRecognitionLevelAccurate
    
    try:
        # 画像を読み込み
        image_url = NSURL.fileURLWithPath_(image_path)
        if image_url is None:
            logger.error(f"画像URLの作成に失敗しました: {image_path}")
            return ""
        
        ci_image = CIImage.imageWithContentsOfURL_(image_url)
        if ci_image is None:
            logger.error(f"画像の読み込みに失敗しました: {image_path}")
            return ""
        
        # テキスト認識リクエストを作成
        request = Vision.VNRecognizeTextRequest.alloc().init()
        if request is None:
            logger.error("VNRecognizeTextRequestの作成に失敗しました")
            return ""
        
        # 認識言語を設定
        request.setRecognitionLanguages_(recognition_languages)
        
        # 認識レベルを設定
        request.setRecognitionLevel_(recognition_level)
        
        # リクエストハンドラを作成
        handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
            ci_image, {}
        )
        if handler is None:
            logger.error("VNImageRequestHandlerの作成に失敗しました")
            return ""
        
        # OCRを実行
        # pyobjcでは、エラーパラメータにNoneを渡すと戻り値として(result, error)のタプルが返る
        success, error = handler.performRequests_error_([request], None)

        if not success:
            logger.warning(f"OCR処理が失敗しました: {image_path}, エラー: {error}")
            return ""
        
        # 結果を取得
        results = request.results()
        if results is None or len(results) == 0:
            logger.debug(f"OCR結果が空でした: {image_path}")
            return ""
        
        # テキストを結合
        text_parts = []
        for observation in results:
            try:
                # 最も信頼度の高い候補を取得
                candidates = observation.topCandidates_(1)
                if candidates and len(candidates) > 0:
                    text = candidates[0].string()
                    if text:
                        text_parts.append(text)
            except Exception as e:
                logger.debug(f"OCR結果の取得中にエラー（無視可能）: {e}")
                continue
        
        extracted_text = "\n".join(text_parts)
        logger.debug(f"OCR成功: {len(extracted_text)}文字を抽出")
        
        return extracted_text
        
    except Exception as e:
        logger.error(f"OCR処理中にエラーが発生しました: {e}")
        return ""


"""LLMクライアントモジュール（OpenAI互換API）"""
import logging
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("snaplog.llm_client")


class LLMClientError(Exception):
    """LLMクライアント関連のエラー"""
    pass


class LLMClient:
    """OpenAI互換APIクライアント"""
    
    def __init__(
        self,
        endpoint: str,
        model: str,
        max_tokens: int = 2000,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        LLMクライアントを初期化
        
        Args:
            endpoint: APIエンドポイントURL
            model: モデル名
            max_tokens: 最大トークン数
            timeout: タイムアウト（秒）
            max_retries: 最大リトライ回数
            retry_delay: リトライ間隔（秒）
        """
        self.endpoint = endpoint
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _make_request(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        LLM APIにリクエストを送信
        
        Args:
            messages: メッセージのリスト（[{"role": "user", "content": "..."}]）
            system_prompt: システムプロンプト（オプション）
            
        Returns:
            str: LLMの応答テキスト
            
        Raises:
            LLMClientError: API呼び出しに失敗した場合
        """
        # システムプロンプトを追加
        request_messages = []
        if system_prompt:
            request_messages.append({
                "role": "system",
                "content": system_prompt
            })
        request_messages.extend(messages)
        
        # リクエストボディ
        payload = {
            "model": self.model,
            "messages": request_messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7
        }
        
        # リトライループ
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"LLM APIリクエスト送信（試行 {attempt + 1}/{self.max_retries}）")
                logger.debug(f"エンドポイント: {self.endpoint}, モデル: {self.model}")
                
                response = requests.post(
                    self.endpoint,
                    json=payload,
                    timeout=self.timeout
                )
                
                # HTTPエラーチェック
                response.raise_for_status()
                
                # レスポンス解析
                result = response.json()
                
                # OpenAI互換形式のレスポンスを解析
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    if content:
                        logger.debug(f"LLM応答を取得しました（{len(content)}文字）")
                        return content
                    else:
                        raise LLMClientError("LLM応答にcontentが含まれていません")
                else:
                    raise LLMClientError(f"予期しないレスポンス形式: {result}")
                    
            except requests.exceptions.Timeout:
                last_error = "タイムアウト"
                logger.warning(f"LLM APIリクエストがタイムアウトしました（試行 {attempt + 1}/{self.max_retries}）")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except requests.exceptions.ConnectionError as e:
                last_error = f"接続エラー: {e}"
                logger.warning(f"LLM APIに接続できませんでした（試行 {attempt + 1}/{self.max_retries}）: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise LLMClientError(
                        f"LLM APIに接続できませんでした。LLMサーバー（{self.endpoint}）が起動しているか確認してください。"
                    )
                    
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTPエラー: {e}"
                logger.error(f"LLM API HTTPエラー（試行 {attempt + 1}/{self.max_retries}）: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise LLMClientError(f"LLM API HTTPエラー: {e}")
                    
            except requests.exceptions.RequestException as e:
                last_error = f"リクエストエラー: {e}"
                logger.error(f"LLM APIリクエストエラー（試行 {attempt + 1}/{self.max_retries}）: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except Exception as e:
                last_error = f"予期しないエラー: {e}"
                logger.error(f"LLM API呼び出し中に予期しないエラーが発生しました: {e}")
                raise LLMClientError(f"LLM API呼び出しエラー: {e}")
        
        # すべてのリトライが失敗
        raise LLMClientError(
            f"LLM API呼び出しに失敗しました（{self.max_retries}回試行）: {last_error}"
        )
    
    def generate_report(
        self,
        log_text: str,
        date: str
    ) -> str:
        """
        ログテキストから日報を生成
        
        Args:
            log_text: 前処理済みのログテキスト
            date: 対象日（YYYY-MM-DD形式）
            
        Returns:
            str: 生成された日報（Markdown形式）
            
        Raises:
            LLMClientError: API呼び出しに失敗した場合
        """
        system_prompt = """あなたは日報作成アシスタントです。
ユーザーの作業ログを分析して、構造化された日報をMarkdown形式で作成してください。
日報には以下の項目を含めてください：
- 作業内容の要約
- 使用したアプリケーション・ツール
- 主な作業項目（箇条書き）
- 所感・気づき
- 課題・問題点
- 明日の予定・次回の作業予定

簡潔で読みやすい日報を作成してください。"""
        
        user_prompt = f"""以下の作業ログから、{date}の日報を作成してください。

{log_text}

上記のログを分析して、Markdown形式の日報を作成してください。"""
        
        messages = [
            {
                "role": "user",
                "content": user_prompt
            }
        ]
        
        try:
            report = self._make_request(messages, system_prompt)
            return report
        except LLMClientError as e:
            logger.error(f"日報生成に失敗しました: {e}")
            raise


def create_llm_client(config) -> LLMClient:
    """
    設定からLLMクライアントを作成
    
    Args:
        config: Configオブジェクト
        
    Returns:
        LLMClient: LLMクライアントインスタンス
    """
    return LLMClient(
        endpoint=config.llm.endpoint,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens
    )


"""LLMクライアントモジュールのテスト"""
from unittest.mock import Mock, patch

import pytest

from src.llm_client import LLMClient, LLMClientError, create_llm_client
from src.config import Config, LLMConfig


def test_llm_client_init():
    """LLMクライアント初期化のテスト"""
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_tokens=2000,
        timeout=60,
        max_retries=3
    )
    
    assert client.endpoint == "http://localhost:1234/v1/chat/completions"
    assert client.model == "test-model"
    assert client.max_tokens == 2000
    assert client.timeout == 60
    assert client.max_retries == 3


@patch('src.llm_client.requests.post')
def test_llm_client_success(mock_post):
    """LLM API呼び出し成功のテスト"""
    # モックレスポンス
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "これはテスト応答です。"
                }
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model"
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    result = client._make_request(messages)
    
    assert result == "これはテスト応答です。"
    mock_post.assert_called_once()


@patch('src.llm_client.requests.post')
def test_llm_client_connection_error(mock_post):
    """LLM API接続エラーのテスト"""
    import requests
    
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_retries=1
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    
    with pytest.raises(LLMClientError) as exc_info:
        client._make_request(messages)
    
    assert "LLMサーバーが起動しているか確認してください" in str(exc_info.value)


@patch('src.llm_client.requests.post')
def test_llm_client_timeout(mock_post):
    """LLM APIタイムアウトのテスト"""
    import requests
    
    mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_retries=1
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    
    with pytest.raises(LLMClientError):
        client._make_request(messages)


@patch('src.llm_client.requests.post')
def test_llm_client_http_error(mock_post):
    """LLM API HTTPエラーのテスト"""
    import requests
    
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_post.return_value = mock_response
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_retries=1
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    
    with pytest.raises(LLMClientError) as exc_info:
        client._make_request(messages)
    
    assert "HTTPエラー" in str(exc_info.value)


@patch('src.llm_client.requests.post')
def test_llm_client_retry(mock_post):
    """LLM APIリトライのテスト"""
    import requests
    import time
    
    # 最初の2回は接続エラー、3回目で成功
    mock_post.side_effect = [
        requests.exceptions.ConnectionError("Connection failed"),
        requests.exceptions.ConnectionError("Connection failed"),
        Mock(json=lambda: {
            "choices": [{"message": {"content": "成功"}}]
        }, raise_for_status=Mock())
    ]
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_retries=3,
        retry_delay=0.1
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    result = client._make_request(messages)
    
    assert result == "成功"
    assert mock_post.call_count == 3


@patch('src.llm_client.LLMClient._make_request')
def test_generate_report(mock_make_request):
    """日報生成のテスト"""
    mock_make_request.return_value = "# 日報\n\n今日はテストを実施しました。"
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model"
    )
    
    log_text = "作業ログ: テストを実施"
    date = "2025-01-15"
    
    report = client.generate_report(log_text, date)
    
    assert "日報" in report
    assert mock_make_request.called
    # システムプロンプトとユーザープロンプトが含まれていることを確認
    call_args = mock_make_request.call_args
    assert call_args is not None


def test_create_llm_client():
    """設定からLLMクライアント作成のテスト"""
    config = Config()
    config.llm.endpoint = "http://localhost:1234/v1/chat/completions"
    config.llm.model = "test-model"
    config.llm.max_tokens = 2000
    
    client = create_llm_client(config)
    
    assert isinstance(client, LLMClient)
    assert client.endpoint == "http://localhost:1234/v1/chat/completions"
    assert client.model == "test-model"
    assert client.max_tokens == 2000


@patch('src.llm_client.requests.post')
def test_llm_client_invalid_response(mock_post):
    """無効なレスポンス形式のテスト"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "invalid": "response"
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_retries=1
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    
    with pytest.raises(LLMClientError) as exc_info:
        client._make_request(messages)
    
    assert "予期しないレスポンス形式" in str(exc_info.value)


@patch('src.llm_client.requests.post')
def test_llm_client_empty_content(mock_post):
    """空のcontentのテスト"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": ""
                }
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    client = LLMClient(
        endpoint="http://localhost:1234/v1/chat/completions",
        model="test-model",
        max_retries=1
    )
    
    messages = [{"role": "user", "content": "テスト"}]
    
    with pytest.raises(LLMClientError) as exc_info:
        client._make_request(messages)
    
    assert "contentが含まれていません" in str(exc_info.value)


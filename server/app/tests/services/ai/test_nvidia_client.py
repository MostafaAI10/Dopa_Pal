import json
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError

from app.services.ai.llm.nvidia_client import NvidiaClient, NvidiaConfig, NvidiaUnavailableError


@pytest.fixture
def mock_openai():
    with patch("app.services.ai.llm.nvidia_client.OpenAI") as mock:
        yield mock


@pytest.fixture
def dummy_config():
    return NvidiaConfig(api_key="test-key")


def test_enrich_task_success(mock_openai, dummy_config):
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"refined_title": "Draft the proposal", "difficulty": "medium"})
    mock_client.chat.completions.create.return_value = mock_response

    client = NvidiaClient(config=dummy_config)
    result = client.enrich_task("write the proposal", "Write the proposal")

    assert result["refined_title"] == "Draft the proposal"
    assert result["difficulty"] == "medium"


def test_enrich_task_unreachable_raises(mock_openai, dummy_config):
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = APIError("API Error", request=MagicMock(), body=None)

    client = NvidiaClient(config=dummy_config)
    with pytest.raises(NvidiaUnavailableError):
        client.enrich_task("anything", "Anything")


def test_enrich_task_bad_json_raises(mock_openai, dummy_config):
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "not valid json"
    mock_client.chat.completions.create.return_value = mock_response

    client = NvidiaClient(config=dummy_config)
    with pytest.raises(NvidiaUnavailableError):
        client.enrich_task("anything", "Anything")


def test_enrich_task_strips_unexpected_keys(mock_openai, dummy_config):
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"refined_title": "ok", "malicious_key": "ignored", "difficulty": "low"})
    mock_client.chat.completions.create.return_value = mock_response

    client = NvidiaClient(config=dummy_config)
    result = client.enrich_task("x", "x")
    assert "malicious_key" not in result


def test_is_available_false_on_connection_error(mock_openai, dummy_config):
    mock_client = mock_openai.return_value
    mock_client.models.list.side_effect = APIError("error", request=MagicMock(), body=None)

    client = NvidiaClient(config=dummy_config)
    assert client.is_available() is False

def test_is_available_false_without_key():
    client = NvidiaClient(config=NvidiaConfig(api_key=""))
    assert client.is_available() is False

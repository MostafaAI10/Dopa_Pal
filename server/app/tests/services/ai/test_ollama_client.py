import json

import httpx
import pytest

from app.services.ai.llm.ollama_client import OllamaClient, OllamaConfig, OllamaUnavailableError


def _client_with_transport(transport: httpx.MockTransport) -> OllamaClient:
    client = OllamaClient(OllamaConfig())
    return client, transport


def test_enrich_task_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"response": json.dumps({"refined_title": "Draft the proposal", "difficulty": "medium"})}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: httpx.Client(transport=transport, **{k: v for k, v in kw.items() if k != "transport"}))

    client = OllamaClient()
    result = client.enrich_task("write the proposal", "Write the proposal")

    assert result["refined_title"] == "Draft the proposal"
    assert result["difficulty"] == "medium"


def test_enrich_task_unreachable_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: httpx.Client(transport=transport, **{k: v for k, v in kw.items() if k != "transport"}))

    client = OllamaClient()
    with pytest.raises(OllamaUnavailableError):
        client.enrich_task("anything", "Anything")


def test_enrich_task_bad_json_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "not valid json"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: httpx.Client(transport=transport, **{k: v for k, v in kw.items() if k != "transport"}))

    client = OllamaClient()
    with pytest.raises(OllamaUnavailableError):
        client.enrich_task("anything", "Anything")


def test_enrich_task_strips_unexpected_keys(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"response": json.dumps({"refined_title": "ok", "malicious_key": "ignored", "difficulty": "low"})}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: httpx.Client(transport=transport, **{k: v for k, v in kw.items() if k != "transport"}))

    client = OllamaClient()
    result = client.enrich_task("x", "x")
    assert "malicious_key" not in result


def test_is_available_false_on_connection_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: httpx.Client(transport=transport, **{k: v for k, v in kw.items() if k != "transport"}))

    client = OllamaClient()
    assert client.is_available() is False

import asyncio
import json

import httpx
import pytest

import kev_mcp as adapter


QUESTIONS = {"topic": {"type": "choice", "instructions": "Topic?", "criteria": {"a": "A", "b": "B"}}}


def mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(adapter.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def test_forwards_validated_payload_and_preserves_probabilities(monkeypatch):
    expected = {"answers": {"topic": {"choice": "a", "probabilities": {"a": 0.61, "b": 0.39}}}, "latency_ms": 123}
    def handler(request):
        assert request.url.path == "/v1/systemone"
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body["model"] == "kev-latest"
        assert body["state"] == {"text": "hello"}
        assert body["questions"] == QUESTIONS
        return httpx.Response(200, json=expected)
    mock_http(monkeypatch, handler)
    assert asyncio.run(adapter.kev_decide({"text": "hello"}, QUESTIONS)) == expected


@pytest.mark.parametrize("questions", [{}, {"bad": {"type": "invalid", "instructions": "x"}}, {str(i): QUESTIONS["topic"] for i in range(17)}])
def test_invalid_requests_rejected(questions):
    with pytest.raises(ValueError):
        asyncio.run(adapter.kev_decide("x", questions))


def test_payload_size_limit():
    with pytest.raises(ValueError, match="64 KB"):
        asyncio.run(adapter.kev_decide("x" * 64001, QUESTIONS))


def test_permutation_validates_selected_question():
    with pytest.raises(ValueError, match="existing choice"):
        asyncio.run(adapter.kev_check_permutations("x", QUESTIONS, "missing"))


@pytest.mark.parametrize("failure, message", [("timeout", "timed out"), ("connection", "unavailable"), ("validation", "HTTP 422")])
def test_useful_service_errors(monkeypatch, failure, message):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if failure == "connection":
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(422, json={"detail": "invalid"})
    mock_http(monkeypatch, handler)
    with pytest.raises(RuntimeError, match=message):
        asyncio.run(adapter.kev_models())

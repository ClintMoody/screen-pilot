from unittest.mock import patch, MagicMock

from screen_pilot.backend import detect_backend, LLMBackend


def _mock_response(data: dict, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    return mock


def test_detect_llamacpp():
    models_resp = _mock_response({
        "data": [{"id": "nemotron-cascade", "owned_by": "llamacpp"}]
    })
    with patch("requests.get", return_value=models_resp):
        result = detect_backend()
        assert result is not None
        assert result.backend == "llama.cpp"
        assert result.model == "nemotron-cascade"


def test_detect_ollama():
    def side_effect(url, **kwargs):
        if "11434" in url and "/api/tags" in url:
            return _mock_response({"models": [{"name": "llama3:latest"}]})
        raise ConnectionError()

    with patch("requests.get", side_effect=side_effect):
        result = detect_backend()
        assert result is not None
        assert result.backend == "ollama"


def test_detect_nothing():
    with patch("requests.get", side_effect=ConnectionError()):
        result = detect_backend()
        assert result is None


def test_llm_backend_chat():
    backend = LLMBackend(
        backend="llama.cpp",
        url="http://localhost:8081/v1/chat/completions",
        model="test-model",
        is_vision=False,
        is_reasoning=False,
    )
    chat_resp = _mock_response({
        "choices": [{"message": {"content": '{"action": "done"}'}}]
    })
    with patch("requests.post", return_value=chat_resp):
        result = backend.chat("Hello")
        assert "action" in result

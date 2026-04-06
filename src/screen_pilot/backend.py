"""LLM backend auto-detection for llama.cpp, Ollama, LM Studio, vLLM."""

from dataclasses import dataclass
import json
import re

import requests

PROBE_TARGETS = [
    ("llama.cpp", "http://localhost:{port}/v1/models", range(8080, 8091)),
    ("lm-studio", "http://localhost:1234/v1/models", [1234]),
    ("vllm", "http://localhost:8000/v1/models", [8000]),
    ("ollama", "http://localhost:11434/api/tags", [11434]),
]


@dataclass
class LLMBackend:
    backend: str
    url: str
    model: str
    is_vision: bool = False
    is_reasoning: bool = False

    def chat(self, prompt: str, max_tokens: int = 1024) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        resp = requests.post(self.url, json=payload, timeout=120)
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]

        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")

        text = content.strip() if content.strip() else reasoning.strip()
        json_match = re.search(r'\{[^{}]*"action"\s*:\s*"[^"]+?"[^{}]*\}', text)
        if json_match:
            return json.loads(json_match.group())

        text = text.strip().strip("```json").strip("```").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}


def _probe_openai_compatible(url: str) -> dict | None:
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            if models:
                model = models[0]
                return {
                    "model": model.get("id", "unknown"),
                    "owned_by": model.get("owned_by", ""),
                }
    except (requests.ConnectionError, requests.Timeout, ValueError, ConnectionError, OSError):
        pass
    return None


def _probe_ollama(url: str) -> dict | None:
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            if models:
                return {"model": models[0].get("name", "unknown")}
    except (requests.ConnectionError, requests.Timeout, ValueError, ConnectionError, OSError):
        pass
    return None


def detect_backend(override_url: str | None = None, override_model: str | None = None) -> "LLMBackend | None":
    if override_url:
        return LLMBackend(
            backend="manual",
            url=override_url,
            model=override_model or "unknown",
        )

    for name, url_template, ports in PROBE_TARGETS:
        for port in ports:
            url = url_template.format(port=port)

            if name == "ollama":
                result = _probe_ollama(url)
                if result:
                    return LLMBackend(
                        backend="ollama",
                        url="http://localhost:11434/v1/chat/completions",
                        model=result["model"],
                    )
            else:
                result = _probe_openai_compatible(url)
                if result:
                    backend_name = name
                    if "llamacpp" in result.get("owned_by", "").lower():
                        backend_name = "llama.cpp"
                    base_url = f"http://localhost:{port}/v1/chat/completions"
                    return LLMBackend(
                        backend=backend_name,
                        url=base_url,
                        model=result["model"],
                    )

    return None

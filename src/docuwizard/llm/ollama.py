"""Ollama HTTP client for embeddings and chat (issues #15, #20)."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


class OllamaError(Exception):
    """Raised when an Ollama request fails."""


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    chat_model: str = "gemma2"
    embed_model: str = "nomic-embed-text"
    timeout_sec: float = 600.0

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> OllamaConfig:
        llm = settings.get("llm", {})
        timeout = llm.get("ollama_timeout_sec", cls.timeout_sec)
        try:
            timeout_sec = float(timeout)
        except (TypeError, ValueError):
            timeout_sec = cls.timeout_sec
        return cls(
            base_url=str(llm.get("ollama_base_url", cls.base_url)).rstrip("/"),
            chat_model=str(llm.get("ollama_chat_model", cls.chat_model)),
            embed_model=str(llm.get("ollama_embed_model", cls.embed_model)),
            timeout_sec=max(timeout_sec, 30.0),
        )


class OllamaClient:
    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()

    def list_models(self) -> list[str]:
        """Return installed model names from Ollama."""
        data = self._request_json("GET", "/api/tags")
        models = data.get("models") or []
        names = sorted(
            {
                str(m.get("name", "")).strip()
                for m in models
                if isinstance(m, dict) and m.get("name")
            }
        )
        return [n for n in names if n]

    def ping(self) -> str:
        """Return OK message if the server responds."""
        names = self.list_models()
        return f"연결됨 ({len(names)}개 모델)"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Prefer batch /api/embed; fall back to per-prompt /api/embeddings.
        try:
            payload = {"model": self.config.embed_model, "input": texts}
            data = self._request_json("POST", "/api/embed", payload)
            embeddings = data.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                return [[float(x) for x in row] for row in embeddings]
        except OllamaError:
            pass

        vectors: list[list[float]] = []
        for text in texts:
            payload = {"model": self.config.embed_model, "prompt": text}
            data = self._request_json("POST", "/api/embeddings", payload)
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise OllamaError("임베딩 응답 형식이 올바르지 않습니다.")
            vectors.append([float(x) for x in embedding])
        return vectors

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Yield tokens while reading the Ollama NDJSON stream."""
        payload = {
            "model": self.config.chat_model,
            "messages": messages,
            "stream": True,
            "keep_alive": "30m",
        }
        request = self._build_request("POST", "/api/chat", payload)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # Loading / error events from Ollama (when present)
                    if data.get("error"):
                        raise OllamaError(str(data["error"]))
                    message = data.get("message") or {}
                    content = message.get("content")
                    if isinstance(content, str) and content:
                        yield content
                    if data.get("done"):
                        break
        except TimeoutError as exc:
            raise OllamaError(
                f"Ollama 응답 시간 초과 ({self.config.timeout_sec:.0f}초). "
                f"채팅 모델 '{self.config.chat_model}' 로딩/생성이 오래 걸렸습니다. "
                "큰 모델(12b+)은 첫 토큰까지 수 분이 걸릴 수 있습니다. "
                "설정에서 타임아웃을 늘리거나 gemma:2b 같은 작은 모델로 시험하세요."
            ) from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise self._wrap_url_error(exc) from exc

    def chat(self, messages: list[dict[str, str]], *, stream: bool = False) -> str:
        if stream:
            return "".join(self.chat_stream(messages))
        payload = {
            "model": self.config.chat_model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
        }
        data = self._request_json("POST", "/api/chat", payload)
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise OllamaError("채팅 응답 형식이 올바르지 않습니다.")
        return content

    def warmup(self) -> str:
        """Load the chat model with a tiny prompt so later questions start faster."""
        t0_msg = [{"role": "user", "content": "ping"}]
        first = next(self.chat_stream(t0_msg), "")
        return f"모델 '{self.config.chat_model}' 예열 완료 (첫 응답: {first[:40]!r})"

    def _request_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = self._request_raw(method, path, payload)
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama 응답 JSON 파싱 실패") from exc
        if not isinstance(data, dict):
            raise OllamaError("Ollama 응답이 객체가 아닙니다.")
        return data

    def _request_raw(self, method: str, path: str, payload: dict | None = None) -> str:
        request = self._build_request(method, path, payload)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as resp:
                return resp.read().decode("utf-8")
        except TimeoutError as exc:
            raise OllamaError(
                f"Ollama 응답 시간 초과 ({self.config.timeout_sec:.0f}초)."
            ) from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise self._wrap_url_error(exc) from exc

    def _build_request(
        self, method: str, path: str, payload: dict | None = None
    ) -> urllib.request.Request:
        url = f"{self.config.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        return urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if payload is not None else {},
        )

    def _wrap_url_error(self, exc: urllib.error.URLError) -> OllamaError:
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return OllamaError(
                f"Ollama 응답 시간 초과 ({self.config.timeout_sec:.0f}초). "
                f"채팅 모델 '{self.config.chat_model}' / "
                f"임베딩 모델 '{self.config.embed_model}' 을 확인하세요."
            )
        return OllamaError(f"Ollama에 연결할 수 없습니다: {reason}")

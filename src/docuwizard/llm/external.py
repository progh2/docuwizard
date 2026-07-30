"""OpenAI and Anthropic chat clients over plain urllib (issues #31–#32).

No SDK dependencies: both providers speak JSON over HTTPS with Server-Sent
Events for streaming, which the standard library handles fine.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator

from docuwizard.llm.base import LlmError

DEFAULT_TIMEOUT_SEC = 300.0


def iter_sse_data(lines: Iterator[bytes]) -> Iterator[dict]:
    """Yield parsed JSON payloads from an SSE byte stream (skips [DONE])."""
    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            yield data


def split_system(
    messages: list[dict[str, str]],
) -> tuple[str, list[dict[str, str]]]:
    """Anthropic takes the system prompt as a separate field, not a message."""
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") in ("user", "assistant")]
    return "\n\n".join(system_parts), rest


class _HttpChatClient:
    """Shared request/abort plumbing for external providers."""

    provider_name = "external"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self.model = model.strip()
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self._active_response = None

    @property
    def model_name(self) -> str:
        return self.model

    def abort(self) -> None:
        """Close the in-flight stream (safe from another thread)."""
        response = self._active_response
        if response is not None:
            try:
                response.close()
            except Exception:  # noqa: BLE001 — best-effort close
                pass

    def chat(self, messages: list[dict[str, str]], *, stream: bool = False) -> str:
        if stream:
            return "".join(self.chat_stream(messages))
        return self._chat_once(messages)

    # Subclasses implement:
    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        raise NotImplementedError

    def _chat_once(self, messages: list[dict[str, str]]) -> str:
        raise NotImplementedError

    def ping(self) -> str:
        raise NotImplementedError

    def _check_config(self) -> None:
        if not self.api_key:
            raise LlmError(
                f"{self.provider_name} API 키가 설정되지 않았습니다. "
                "설정에서 API 키를 입력하세요."
            )
        if not self.model:
            raise LlmError(f"{self.provider_name} 모델명이 비어 있습니다.")

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _request(self, method: str, path: str, payload: dict | None = None):
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", **self._headers()}
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        return urllib.request.urlopen(request, timeout=self.timeout_sec)

    def _request_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            with self._request(method, path, payload) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise self._wrap_http_error(exc) from exc
        except urllib.error.URLError as exc:
            raise LlmError(
                f"{self.provider_name}에 연결할 수 없습니다: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise LlmError(
                f"{self.provider_name} 응답 시간 초과 ({self.timeout_sec:.0f}초)."
            ) from exc
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LlmError(f"{self.provider_name} 응답 JSON 파싱 실패") from exc
        if not isinstance(data, dict):
            raise LlmError(f"{self.provider_name} 응답이 객체가 아닙니다.")
        return data

    def _stream_sse(self, path: str, payload: dict) -> Iterator[dict]:
        try:
            with self._request("POST", path, payload) as resp:
                self._active_response = resp
                yield from iter_sse_data(resp)
        except urllib.error.HTTPError as exc:
            raise self._wrap_http_error(exc) from exc
        except urllib.error.URLError as exc:
            raise LlmError(
                f"{self.provider_name}에 연결할 수 없습니다: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise LlmError(
                f"{self.provider_name} 응답 시간 초과 ({self.timeout_sec:.0f}초)."
            ) from exc
        except (ValueError, OSError) as exc:
            # Reading a response closed by abort() raises ValueError/OSError.
            raise LlmError("응답 스트림이 중단되었습니다.") from exc
        finally:
            self._active_response = None

    def _wrap_http_error(self, exc: urllib.error.HTTPError) -> LlmError:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code in (401, 403):
            return LlmError(
                f"{self.provider_name} 인증 실패 (HTTP {exc.code}). API 키를 확인하세요."
            )
        return LlmError(f"{self.provider_name} HTTP {exc.code}: {detail}")


class OpenAIClient(_HttpChatClient):
    provider_name = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        super().__init__(
            model=model, api_key=api_key, base_url=base_url, timeout_sec=timeout_sec
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def extract_token(data: dict) -> str | None:
        choices = data.get("choices") or []
        if not choices:
            return None
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        return content if isinstance(content, str) and content else None

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        self._check_config()
        payload = {"model": self.model, "messages": messages, "stream": True}
        for data in self._stream_sse("/chat/completions", payload):
            if data.get("error"):
                raise LlmError(f"openai: {data['error']}")
            token = self.extract_token(data)
            if token:
                yield token

    def _chat_once(self, messages: list[dict[str, str]]) -> str:
        self._check_config()
        payload = {"model": self.model, "messages": messages, "stream": False}
        data = self._request_json("POST", "/chat/completions", payload)
        choices = data.get("choices") or []
        if not choices:
            raise LlmError("openai 응답에 choices가 없습니다.")
        content = (choices[0].get("message") or {}).get("content")
        if not isinstance(content, str):
            raise LlmError("openai 응답 형식이 올바르지 않습니다.")
        return content

    def ping(self) -> str:
        self._check_config()
        data = self._request_json("GET", "/models")
        count = len(data.get("data") or [])
        return f"OpenAI 연결됨 ({count}개 모델)"


class AnthropicClient(_HttpChatClient):
    provider_name = "anthropic"
    MAX_TOKENS = 4096

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        super().__init__(
            model=model, api_key=api_key, base_url=base_url, timeout_sec=timeout_sec
        )

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    @staticmethod
    def extract_token(data: dict) -> str | None:
        if data.get("type") != "content_block_delta":
            return None
        delta = data.get("delta") or {}
        text = delta.get("text")
        return text if isinstance(text, str) and text else None

    def _payload(self, messages: list[dict[str, str]], *, stream: bool) -> dict:
        system, rest = split_system(messages)
        payload: dict = {
            "model": self.model,
            "max_tokens": self.MAX_TOKENS,
            "messages": rest,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        return payload

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        self._check_config()
        for data in self._stream_sse("/messages", self._payload(messages, stream=True)):
            if data.get("type") == "error":
                error = data.get("error") or {}
                raise LlmError(f"anthropic: {error.get('message', error)}")
            token = self.extract_token(data)
            if token:
                yield token

    def _chat_once(self, messages: list[dict[str, str]]) -> str:
        self._check_config()
        data = self._request_json(
            "POST", "/messages", self._payload(messages, stream=False)
        )
        blocks = data.get("content") or []
        texts = [
            b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("text")
        ]
        if not texts:
            raise LlmError("anthropic 응답에 텍스트가 없습니다.")
        return "".join(texts)

    def ping(self) -> str:
        self._check_config()
        data = self._request_json("GET", "/models")
        count = len(data.get("data") or [])
        return f"Anthropic 연결됨 ({count}개 모델)"

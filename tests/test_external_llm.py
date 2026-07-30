"""Tests for external LLM clients, factory, and key storage (#30–#33)."""

from __future__ import annotations

from pathlib import Path

import pytest

from docuwizard import apikeys
from docuwizard.config import DEFAULT_SETTINGS
from docuwizard.ingest.pipeline import index_file
from docuwizard.llm.base import LlmError
from docuwizard.llm.external import (
    AnthropicClient,
    OpenAIClient,
    iter_sse_data,
    split_system,
)
from docuwizard.llm.factory import chat_provider, create_chat_client
from docuwizard.llm.ollama import OllamaClient
from docuwizard.rag.orchestrator import answer_question
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from fakes import FakeOllama


def _settings(provider: str) -> dict:
    import copy

    settings = copy.deepcopy(DEFAULT_SETTINGS)
    settings["llm"]["provider"] = provider
    return settings


def test_iter_sse_data_parses_and_skips_done() -> None:
    lines = iter(
        [
            b"event: message_start\n",
            b'data: {"a": 1}\n',
            b"\n",
            b"data: not-json\n",
            b"data: [DONE]\n",
            b'data: {"b": 2}\n',
        ]
    )
    assert list(iter_sse_data(lines)) == [{"a": 1}, {"b": 2}]


def test_openai_extract_token() -> None:
    data = {"choices": [{"delta": {"content": "안녕"}}]}
    assert OpenAIClient.extract_token(data) == "안녕"
    assert OpenAIClient.extract_token({"choices": [{"delta": {}}]}) is None
    assert OpenAIClient.extract_token({}) is None


def test_anthropic_extract_token() -> None:
    data = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "답"}}
    assert AnthropicClient.extract_token(data) == "답"
    assert AnthropicClient.extract_token({"type": "message_start"}) is None


def test_split_system_moves_system_prompt() -> None:
    messages = [
        {"role": "system", "content": "지시문"},
        {"role": "user", "content": "질문"},
        {"role": "assistant", "content": "답변"},
    ]
    system, rest = split_system(messages)
    assert system == "지시문"
    assert [m["role"] for m in rest] == ["user", "assistant"]


def test_client_requires_api_key() -> None:
    client = OpenAIClient(model="gpt-4o-mini", api_key="")
    with pytest.raises(LlmError, match="API 키"):
        client.chat([{"role": "user", "content": "hi"}])


def test_api_keys_roundtrip() -> None:
    apikeys.set_api_key("openai", "sk-test-123")
    apikeys.set_api_key("anthropic", "sk-ant-456")
    assert apikeys.get_api_key("openai") == "sk-test-123"
    assert apikeys.get_api_key("anthropic") == "sk-ant-456"
    # Blank values are dropped on save.
    apikeys.save_api_keys({"openai": "  ", "anthropic": "sk-ant-456"})
    assert apikeys.get_api_key("openai") == ""


def test_factory_selects_provider() -> None:
    apikeys.set_api_key("openai", "sk-x")
    apikeys.set_api_key("anthropic", "sk-y")

    assert chat_provider(_settings("openai")) == "openai"
    assert chat_provider(_settings("unknown")) == "ollama"

    client = create_chat_client(_settings("openai"))
    assert isinstance(client, OpenAIClient)
    assert client.api_key == "sk-x"

    client = create_chat_client(_settings("anthropic"))
    assert isinstance(client, AnthropicClient)
    assert client.provider_name == "anthropic"

    embedder = FakeOllama()
    client = create_chat_client(_settings("ollama"), embedder=embedder)
    assert client is embedder
    assert isinstance(create_chat_client(_settings("ollama")), OllamaClient)


class FakeExternalChat:
    provider_name = "openai"

    @property
    def model_name(self) -> str:
        return "fake-gpt"

    def chat(self, messages, *, stream: bool = False) -> str:
        return "외부 모델 답변입니다. [doc:1]"

    def chat_stream(self, messages):
        yield "외부 모델 "
        yield "답변입니다. [doc:1]"

    def abort(self) -> None:
        pass

    def ping(self) -> str:
        return "ok"


def test_answer_question_with_external_chat_client(tmp_path: Path) -> None:
    project = project_service.create_project("외부LLM")
    src = tmp_path / "a.txt"
    src.write_text("마감일은 금요일입니다.", encoding="utf-8")
    added = file_service.add_files(project.id, [src])[0]
    index_file(project.id, added, embedder=FakeOllama())

    answer = answer_question(
        project.id,
        "마감일은?",
        client=FakeOllama(),
        chat_client=FakeExternalChat(),
    )
    assert answer.provider == "openai"
    assert answer.model == "fake-gpt"
    assert "외부 모델" in answer.text
    assert answer.citations

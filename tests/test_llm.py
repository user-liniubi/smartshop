import asyncio
from types import SimpleNamespace

import pytest
from openai import OpenAIError

import backend.app.services.llm as llm_module
from backend.app.core.config import Settings
from backend.app.core.exceptions import AppError
from backend.app.services.llm import DeepSeekClient


class FakeCompletions:
    def __init__(self) -> None:
        self.request: dict | None = None

    async def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="耳机提供十二个月质保。[1]"))]
        )


class FakeAsyncOpenAI:
    latest_client = None

    def __init__(self, **kwargs) -> None:
        self.client_options = kwargs
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)
        self.closed = False
        FakeAsyncOpenAI.latest_client = self

    async def close(self) -> None:
        self.closed = True


def test_deepseek_client_calls_compatible_chat_api(monkeypatch):
    monkeypatch.setattr(llm_module, "AsyncOpenAI", FakeAsyncOpenAI)
    settings = Settings(
        _env_file=None,
        deepseek_api_key="test-deepseek-key",
        deepseek_model="deepseek-chat",
    )

    answer = asyncio.run(
        DeepSeekClient(settings).generate_answer(
            question="耳机保修多久？",
            evidence="[1] 耳机提供十二个月质保。",
        )
    )

    fake_client = FakeAsyncOpenAI.latest_client
    assert answer == "耳机提供十二个月质保。[1]"
    assert fake_client is not None
    assert fake_client.closed is True
    assert fake_client.client_options["api_key"] == "test-deepseek-key"
    assert fake_client.completions.request["model"] == "deepseek-chat"
    assert "[1] 耳机提供十二个月质保" in fake_client.completions.request["messages"][1]["content"]


def test_deepseek_client_requires_key():
    settings = Settings(_env_file=None, deepseek_api_key=None)

    with pytest.raises(AppError) as error:
        asyncio.run(
            DeepSeekClient(settings).generate_answer(
                question="耳机保修多久？",
                evidence="evidence",
            )
        )

    assert error.value.code == "model_not_configured"


def test_deepseek_api_error_is_mapped(monkeypatch):
    class FailingCompletions:
        async def create(self, **kwargs):
            raise OpenAIError("temporary failure")

    class FailingAsyncOpenAI(FakeAsyncOpenAI):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.chat = SimpleNamespace(completions=FailingCompletions())

    monkeypatch.setattr(llm_module, "AsyncOpenAI", FailingAsyncOpenAI)
    settings = Settings(
        _env_file=None,
        deepseek_api_key="test-deepseek-key",
    )

    with pytest.raises(AppError) as error:
        asyncio.run(
            DeepSeekClient(settings).generate_answer(
                question="耳机保修多久？",
                evidence="evidence",
            )
        )

    assert error.value.code == "model_unavailable"

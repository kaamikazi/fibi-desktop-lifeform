from __future__ import annotations

from types import SimpleNamespace

from fibi.engines.cloud_provider_base import CloudProviderReply
from fibi.engines.types import ModelResult
from fibi.providers.types import ProviderStatus
from fibi.services.providers.adapters.gemini import GeminiLanguageProvider
from fibi.services.providers.adapters.ollama import OllamaLanguageProvider
from fibi.services.providers.models import GenerationRequest, ProviderErrorCategory


class StubGemini:
    def __init__(self, reply: CloudProviderReply) -> None:
        self.reply = reply
        self.config = SimpleNamespace(google_search=True)

    def status(self, selected=False):
        return ProviderStatus("gemini", selected, True, True, "gemini-3.1-flash-lite", "healthy", False, True, True)

    def is_configured(self):
        return True

    def generate_reply(self, prompt, use_google_search=False):
        return self.reply

    def test_connection(self):
        return self.reply


class StubOllama:
    def __init__(self, result: ModelResult) -> None:
        self.result = result
        self.prompts: list[str] = []

    def health_check(self):
        return False

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.result


def test_gemini_timeout_and_search_grounding_are_normalized() -> None:
    timeout = GeminiLanguageProvider(
        StubGemini(CloudProviderReply("", "gemini-3.1-flash-lite", 4.0, "timed out", "timeout"))
    )
    failed = timeout.generate(GenerationRequest("q", "p", search_grounding_allowed=True))
    assert failed.error_category is ProviderErrorCategory.TIMEOUT

    success = GeminiLanguageProvider(
        StubGemini(CloudProviderReply("answer", "gemini-3.1-flash-lite", 4.0))
    )
    generated = success.generate(GenerationRequest("q", "p", search_grounding_allowed=True))
    assert generated.success and generated.search_grounding_used


def test_ollama_unavailable_and_timeout_are_normalized_without_real_request() -> None:
    unavailable = OllamaLanguageProvider(StubOllama(ModelResult("", "qwen", 0.0, "connection refused")))
    failed = unavailable.generate(GenerationRequest("q", "prompt"))
    assert failed.error_category is ProviderErrorCategory.NETWORK_ERROR

    timeout = OllamaLanguageProvider(StubOllama(ModelResult("", "qwen", 0.1, "request timed out")))
    timed_out = timeout.generate(GenerationRequest("q", "prompt"))
    assert timed_out.error_category is ProviderErrorCategory.TIMEOUT

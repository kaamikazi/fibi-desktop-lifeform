"""Generic OpenAI-compatible cloud provider."""

from __future__ import annotations

import time

try:
    import requests
except ImportError:
    requests = None

from fibi.engines.cloud_provider_base import CloudProviderBase, CloudProviderReply
from fibi.settings import CLOUD_API_KEY, CLOUD_BASE_URL, CLOUD_MODEL, CLOUD_TIMEOUT_SECONDS


class OpenAICompatibleProvider(CloudProviderBase):
    name = "openai_compatible"
    timeout_seconds = CLOUD_TIMEOUT_SECONDS
    max_tokens = 60
    supports_streaming = False
    privacy_level = "minimal"

    def is_available(self) -> bool:
        return bool(CLOUD_API_KEY and CLOUD_BASE_URL and CLOUD_MODEL)

    def generate_reply(self, context: str) -> CloudProviderReply:
        start = time.perf_counter()
        if not self.is_available():
            return CloudProviderReply("", CLOUD_MODEL or "openai-compatible", 0.0, "generic cloud provider unavailable")
        if requests is None:
            return CloudProviderReply("", CLOUD_MODEL, 0.0, "requests package is not installed")
        try:
            response = requests.post(
                f"{CLOUD_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {CLOUD_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": CLOUD_MODEL,
                    "messages": [{"role": "user", "content": context}],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            text = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
            return CloudProviderReply(text, CLOUD_MODEL, (time.perf_counter() - start) * 1000, None if text else "empty reply")
        except Exception as error:
            self.last_error = str(error)
            return CloudProviderReply("", CLOUD_MODEL, (time.perf_counter() - start) * 1000, self.last_error)

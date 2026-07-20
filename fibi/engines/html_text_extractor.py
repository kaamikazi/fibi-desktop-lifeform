"""Extract readable text from user-provided HTML without fetching anything."""

from __future__ import annotations

import html
import re

from fibi.engines.secret_sanitizer import SecretSanitizer


class HtmlTextExtractor:
    """Convert pasted or dropped HTML into a short local text crumb."""

    def __init__(self, sanitizer: SecretSanitizer | None = None, max_chars: int = 20_000) -> None:
        self.sanitizer = sanitizer or SecretSanitizer()
        self.max_chars = max_chars

    def extract(self, text: str) -> str:
        raw = text[: self.max_chars]
        cleaned = re.sub(r"(?is)<script\b.*?</script>", " ", raw)
        cleaned = re.sub(r"(?is)<style\b.*?</style>", " ", cleaned)
        cleaned = re.sub(r"(?is)<!--.*?-->", " ", cleaned)
        cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
        cleaned = re.sub(r"(?i)</(p|div|section|article|li|h[1-6])>", "\n", cleaned)
        cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
        cleaned = html.unescape(cleaned)
        lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.splitlines()]
        readable = "\n".join(line for line in lines if line)
        return self.sanitizer.sanitize(readable[: self.max_chars])

    @staticmethod
    def looks_like_html(text: str) -> bool:
        lowered = text.lower()
        return "<html" in lowered or "<body" in lowered or bool(re.search(r"<(article|main|section|p|div|h1|title)\b", lowered))

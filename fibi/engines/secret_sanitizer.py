"""Mask likely secrets before previews, logs, and model context."""

from __future__ import annotations

import re


class SecretSanitizer:
    """Best-effort masking for common secret shapes without altering originals."""

    ENV_ASSIGNMENT = re.compile(
        r"(?im)^([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PASS|KEY)[A-Z0-9_]*\s*=\s*)(.+)$"
    )
    AUTH_HEADER = re.compile(r"(?im)^(Authorization\s*:\s*)(.+)$")
    GEMINI_KEY = re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b")
    PRIVATE_KEY = re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    )
    LONG_SECRET = re.compile(r"\b(?:sk-|pk_)?[A-Za-z0-9_\-]{32,}\b")

    def sanitize(self, text: str) -> str:
        if not text:
            return ""
        sanitized = self.PRIVATE_KEY.sub("[masked private key]", text)
        sanitized = self.ENV_ASSIGNMENT.sub(r"\1[masked]", sanitized)
        sanitized = self.AUTH_HEADER.sub(r"\1[masked]", sanitized)
        sanitized = self.GEMINI_KEY.sub("[masked Gemini key]", sanitized)
        sanitized = self.LONG_SECRET.sub("[masked]", sanitized)
        return sanitized

    def sensitivity_hint(self, text: str) -> str:
        sanitized = self.sanitize(text)
        return "secret_masked" if sanitized != text else "normal"

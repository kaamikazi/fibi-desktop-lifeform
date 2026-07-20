"""Safety checks for Fibi's local browser helper."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from fibi.engines.types import BrowserSafetyResult

BLOCKED_PHRASES = (
    "browser history",
    "read history",
    "cookies",
    "cookie",
    "saved password",
    "password",
    "credential",
    "auto click",
    "autoclick",
    "click the",
    "auto scroll",
    "scrape",
    "hidden scraping",
    "fill form",
    "submit form",
    "send message",
    "send email",
    "buy ",
    "purchase",
    "checkout",
    "bypass login",
    "rate limit",
)
HIGH_RISK_PHRASES = ("login", "payment", "bank", "account settings", "business action")
MEDIUM_RISK_PHRASES = ("open ", "contact", "outreach", "message draft", "lead")


class BrowserSafetyEngine:
    """Classify browser requests without touching the browser."""

    def validate_url(self, raw_url: str) -> BrowserSafetyResult:
        url = raw_url.strip()
        if not url:
            return BrowserSafetyResult(False, True, "blocked", False, "missing_url", "give me a link crumb.")
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url) and not url.startswith(("http://", "https://")):
            return BrowserSafetyResult(
                False,
                True,
                "blocked",
                False,
                "unsupported_scheme",
                "that link shape is blocked. http/https only.",
            )
        if "://" not in url:
            url = "https://" + url
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return BrowserSafetyResult(
                False,
                True,
                "blocked",
                False,
                "unsupported_scheme",
                "that link shape is blocked. http/https only.",
            )
        if not parsed.netloc:
            return BrowserSafetyResult(False, True, "blocked", False, "missing_domain", "that link has no domain crumb.")
        domain = parsed.netloc.lower()
        return BrowserSafetyResult(True, False, "medium", True, "external_url", "", url, domain)

    def classify_request(self, text: str) -> BrowserSafetyResult:
        lowered = re.sub(r"\s+", " ", text.lower()).strip()
        for phrase in BLOCKED_PHRASES:
            if phrase in lowered:
                return BrowserSafetyResult(
                    False,
                    True,
                    "blocked",
                    False,
                    f"blocked_phrase:{phrase}",
                    "nope. browser secrets and auto-actions stay locked.",
                )
        if any(phrase in lowered for phrase in HIGH_RISK_PHRASES):
            return BrowserSafetyResult(True, False, "high", True, "high_risk_manual_only", "")
        if any(phrase in lowered for phrase in MEDIUM_RISK_PHRASES):
            return BrowserSafetyResult(True, False, "medium", True, "medium_risk_manual", "")
        return BrowserSafetyResult(True, False, "low", False, "safe_note_or_summary", "")

    def status_line(self) -> str:
        return "browser helper on. no scraping, no cookies, no passwords, no auto-click paws."

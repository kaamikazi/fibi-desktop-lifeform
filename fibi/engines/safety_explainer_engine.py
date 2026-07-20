"""Human-readable safety explanations for Fibi."""

from __future__ import annotations


class SafetyExplainerEngine:
    """Explain Fibi's local-first boundaries without changing settings."""

    def safety_overview(self) -> str:
        return (
            "safety map: local-first. cloud off by default. no hidden browsing. "
            "no auto-send, no auto-buy, no auto-apply patch, or arbitrary terminal. "
            "memory is reviewable, pausable, and exportable. secrets never go in the notebook. "
            "risky crumbs ask first."
        )

    def privacy_overview(self) -> str:
        return (
            "privacy map: memory stays local, support bundles mask secrets, "
            "clipboard/screenshots/voice/cloud stay off unless enabled. "
            "memory controls: /memory consent, /memory learning off, /memory export, /memory safety."
        )

    def refusals(self) -> str:
        return (
            "i refuse: browser secrets, cookies, passwords, hidden scraping, "
            "autonomous purchases, sending messages, destructive commands, "
            "secret collection, and surprise patching."
        )

    def confirmations(self) -> str:
        return (
            "confirmation needed: browser open, patch apply, project checks, "
            "project file reads, RVC voice skin on, screenshots, shutdown, "
            "memory edits/deletes, broad memory deletes, and release/build style steps."
        )

    def beginner_guide(self) -> str:
        return (
            "tiny manual: talk normally, use /commands to browse, "
            "/help search <word> to find a command, /workflow list for rituals, "
            "/memories to review the notebook, /permissions for switches, /safety for boundaries."
        )

    def what_can_you_do(self) -> str:
        return (
            "i can chat, remember local crumbs, speak, guide project sessions, "
            "suggest patches, run confirmed checks, help with pasted page text, "
            "track issues, review/export memories, export support bundles, and guide recipes."
        )

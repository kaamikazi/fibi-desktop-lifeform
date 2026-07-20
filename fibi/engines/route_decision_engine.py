"""Central route decisions for Fibi.

This engine is intentionally side-effect free. It names the route Fibi should
take and records why, but it never calls a model, opens apps, or speaks.
"""

from __future__ import annotations

import re

from fibi.engines.types import ActionIntent, FastResponseCategory, LocalMicroBrainResult, RouteDecision


COMMAND_ROUTES = {
    "/actions": "local_command",
    "/apps": "local_command",
    "/voice": "voice_command",
    "/listen": "voice_command",
    "/context": "context_command",
    "/project": "project_command",
    "/edit": "project_command",
    "/route": "local_command",
    "/tts": "local_command",
    "/privacy": "local_command",
    "/memory": "local_command",
    "/memories": "local_command",
    "/model": "local_command",
    "/cloud": "local_command",
    "/provider": "local_command",
    "/status": "local_command",
}

LOCAL_ACTIONS = {
    "tell_date",
    "tell_time",
    "volume_up",
    "volume_down",
    "mute",
    "unmute",
    "open_app",
    "open_website",
    "web_search",
    "youtube_search",
    "wikipedia_search",
    "refresh_app_index",
    "list_known_apps",
    "search_known_apps",
}


class RouteDecisionEngine:
    """Choose route labels and keep the latest debug snapshot."""

    def __init__(self) -> None:
        self.last_decision = RouteDecision("local_fallback", True, False, False, "startup", 0)

    def decide(
        self,
        user_text: str,
        event_source: str = "user_message",
        action_intent: ActionIntent | None = None,
        fast_category: FastResponseCategory | None = None,
        command_result_handled: bool = False,
        local_micro_brain_result: LocalMicroBrainResult | None = None,
        provider_allowed: bool = True,
    ) -> RouteDecision:
        normalized = self.normalize(user_text)
        if command_result_handled or normalized.startswith("/"):
            route = self._command_route(normalized)
            return self._remember(RouteDecision(route, True, False, False, "slash/local command", 1000))
        if action_intent is not None:
            allowed = action_intent.action_type in LOCAL_ACTIONS
            route = "local_utility" if action_intent.action_type in {"tell_date", "tell_time"} else "local_action"
            return self._remember(
                RouteDecision(route, True, False, allowed, action_intent.action_type, 300, action_intent.action_type)
            )
        category = fast_category.category if fast_category else "unknown"
        if category == "greeting":
            return self._remember(RouteDecision("local_greeting", True, False, False, "greeting", 300, fast_category=category))
        if category in {"thanks", "goodbye", "success", "frustration", "tiny_status", "affection_click_like"}:
            return self._remember(RouteDecision("local_micro_brain", True, False, False, category, 500, fast_category=category))
        if local_micro_brain_result and local_micro_brain_result.handled and local_micro_brain_result.confidence == "high":
            return self._remember(RouteDecision("local_micro_brain", True, False, False, "confident local micro-brain", 500, fast_category=category))
        if category in {"social_checkin", "simple_chat"}:
            route = "model_complex_chat" if provider_allowed else "local_fallback"
            return self._remember(
                RouteDecision(
                    route,
                    provider_allowed,
                    provider_allowed,
                    False,
                    "uncertain local conversation escalated",
                    7000,
                    fast_category=category,
                )
            )
        if category == "local_utility":
            return self._remember(RouteDecision("local_utility", True, False, True, "utility classifier", 300, fast_category=category))
        if category == "complex_chat":
            route = "model_complex_chat" if provider_allowed else "local_fallback"
            return self._remember(RouteDecision(route, provider_allowed, provider_allowed, False, "complex chat", 7000, fast_category=category))
        return self._remember(RouteDecision("local_fallback", True, False, False, f"fallback for {category}", 500, fast_category=category))

    def test_message(
        self,
        message: str,
        action_intent: ActionIntent | None,
        fast_category: FastResponseCategory,
        provider_allowed: bool,
    ) -> RouteDecision:
        return self.decide(
            message,
            action_intent=action_intent,
            fast_category=fast_category,
            provider_allowed=provider_allowed,
        )

    def last_line(self) -> str:
        decision = self.last_decision
        model = "yes" if decision.model_router_allowed else "no"
        suffix = f"/{decision.action_type}" if decision.action_type else ""
        return f"route: {decision.route_name}{suffix}. model: {model}. reason: {decision.reason}."

    def _command_route(self, normalized: str) -> str:
        for prefix, route in COMMAND_ROUTES.items():
            if normalized.startswith(prefix):
                return route
        return "local_command"

    def _remember(self, decision: RouteDecision) -> RouteDecision:
        self.last_decision = decision
        return decision

    @staticmethod
    def normalize(text: str) -> str:
        lowered = text.lower().replace("\u2019", "'").replace("\u2018", "'")
        return re.sub(r"\s+", " ", lowered).strip()

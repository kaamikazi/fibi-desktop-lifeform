"""Social safety filter for Fibi reactions."""

from __future__ import annotations

from fibi.engines.types import BoundaryState, QuietModeState, ReactionCandidate, RelationshipState, SocialContextDecision


class SocialContextEngine:
    """Decide whether a reaction should speak, soften, replace, or stay silent."""

    def filter_reaction(
        self,
        reaction: ReactionCandidate | str | tuple[str, str],
        relationship: RelationshipState,
        boundary: BoundaryState,
        quiet: QuietModeState,
        *,
        direct: bool = False,
        user_message: str = "",
        event: str = "reply",
    ) -> SocialContextDecision:
        text, tone, motion_only = self._extract(reaction)
        lower = f"{user_message} {text}".lower()
        sensitive = any(word in lower for word in ("error", "bug", "crash", "failed", "tired", "quit", "hate"))

        if quiet.active and not direct:
            return SocialContextDecision("silence", reason="quiet mode", motion_only=True)
        if boundary.active and not direct:
            return SocialContextDecision("silence", reason="boundary active", motion_only=True)
        if quiet.active and event in {"idle", "ritual", "habit"}:
            return SocialContextDecision("silence", reason="quiet mode", motion_only=True)
        if tone == "teasing" or self._looks_teasing(text):
            if not self.teasing_allowed(relationship, boundary, quiet, sensitive):
                return SocialContextDecision("replace", "noted. softer.", "teasing blocked")
        if relationship.user_annoyance_level >= 45 and not direct:
            return SocialContextDecision("silence", reason="annoyance high", motion_only=motion_only)
        if relationship.user_annoyance_level >= 35 and tone in {"playful", "teasing"}:
            return SocialContextDecision("replace", "okay. less noise.", "annoyance high")
        return SocialContextDecision("allow", text, "safe")

    @staticmethod
    def teasing_allowed(
        relationship: RelationshipState,
        boundary: BoundaryState,
        quiet: QuietModeState,
        sensitive: bool = False,
    ) -> bool:
        return (
            relationship.teasing_allowed
            and relationship.familiarity_level >= 35
            and relationship.user_annoyance_level <= 20
            and not boundary.active
            and not quiet.active
            and not sensitive
            and relationship.interaction_style != "quiet_companion"
        )

    @staticmethod
    def _extract(reaction: ReactionCandidate | str | tuple[str, str]) -> tuple[str, str, bool]:
        if isinstance(reaction, ReactionCandidate):
            return reaction.text, reaction.social_tone, reaction.can_be_motion_only
        if isinstance(reaction, tuple):
            return reaction[0], "neutral", False
        return str(reaction), "neutral", False

    @staticmethod
    def _looks_teasing(text: str) -> bool:
        lower = text.lower()
        return any(phrase in lower for phrase in ("huh", "tabs are breeding", "again?", "suspicious", "one more commit"))

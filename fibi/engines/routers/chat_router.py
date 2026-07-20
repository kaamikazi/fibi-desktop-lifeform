"""Fast local chat router for greetings and social check-ins."""

from __future__ import annotations

from collections.abc import Collection

from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.engines.local_micro_brain import LocalMicroBrain
from fibi.engines.types import FastResponseCategory, LocalMicroBrainResult, RelationshipState


LOCAL_FAST_CATEGORIES = {
    "thanks",
    "goodbye",
    "success",
    "frustration",
    "tiny_status",
    "social_checkin",
    "affection_click_like",
    "live_data_unavailable",
}


class ChatRouter:
    """Decide whether a direct message can be answered locally."""

    def __init__(
        self,
        classifier: FastResponseClassifier | None = None,
        micro_brain: LocalMicroBrain | None = None,
    ) -> None:
        self.classifier = classifier or FastResponseClassifier()
        self.micro_brain = micro_brain or LocalMicroBrain()

    def classify(self, text: str) -> FastResponseCategory:
        return self.classifier.classify(text)

    def is_greeting(self, text: str, category: FastResponseCategory | None = None) -> bool:
        classified = category or self.classify(text)
        return classified.category == "greeting"

    def local_reply(
        self,
        category: str,
        *,
        mood: str = "idle",
        time_of_day: str = "",
        relationship: RelationshipState | None = None,
        user_message: str = "",
        excluded_texts: Collection[str] = (),
    ) -> LocalMicroBrainResult:
        return self.micro_brain.reply(
            category,
            mood=mood,
            time_of_day=time_of_day,
            relationship=relationship,
            user_message=user_message,
            excluded_texts=excluded_texts,
        )

    @staticmethod
    def is_local_fast_category(category: str) -> bool:
        return category in LOCAL_FAST_CATEGORIES

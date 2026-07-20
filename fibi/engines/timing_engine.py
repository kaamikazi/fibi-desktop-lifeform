"""Emotional response timing that never blocks the UI thread."""

from fibi.engines.types import TimingResult


class TimingEngine:
    def select(
        self,
        *,
        event: str,
        mood: str,
        time_of_day: str = "",
        local: bool = False,
        disagreement: bool = False,
        fallback: bool = False,
    ) -> TimingResult:
        if fallback:
            return TimingResult(80, "instant", False, "")
        if event == "greeting" or mood == "excited":
            return TimingResult(0, "excited" if mood == "excited" else "instant", False, "")
        if disagreement:
            return TimingResult(550, "soft", True, "hmm...")
        if mood in {"curious", "focused"}:
            return TimingResult(350 if local else 0, "thinking", True, "hmm...")
        if mood == "sleepy" or time_of_day == "late_night":
            return TimingResult(650, "sleepy", False, "")
        return TimingResult(120 if local else 0, "soft", False, "")

    @staticmethod
    def bubble_options(text: str, style: str, speaking: bool = False):
        from fibi.engines.types import BubbleDisplayOptions

        auto_hide = 0 if speaking else max(3000, min(10000, 1800 + len(text) * 55))
        return BubbleDisplayOptions(style, auto_hide, False, True)

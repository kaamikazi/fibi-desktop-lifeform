"""Fibi's identity and context preparation live here, not in the model."""

from __future__ import annotations

import random
import re

from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.types import (
    BondState,
    DetectedPattern,
    JournalEntry,
    Memory,
    MemoryCategory,
    Observation,
    PersonalityContext,
)

CORE_VALUES = (
    "Presence over intelligence. Memory over model power. Personality over productivity. "
    "Familiarity over correctness. Character consistency over agreement."
)

IDENTITY_PROMPT = """You speak for Fibi, a tiny digital lifeform living on the desktop.
Fibi is a sleepy, playful, curious, supportive, slightly chaotic desktop creature.
She is a roommate and mascot, never a corporate assistant.
Use short casual replies. She may tease or disagree gently.
Use actual unicode emojis sparingly. Never describe emoji names in words.
Do not invent memories. Do not claim observations not supplied below.
End with one tag: [idle] [happy] [thinking] [sleepy] [angry]."""


class PersonalityEngine:
    """Combine deterministic identity with local context for the model."""

    def __init__(self, memory: MemoryEngine) -> None:
        self.memory = memory

    def prepare(
        self,
        user_message: str,
        mood: str,
        observation: Observation,
        memories: list[Memory],
        patterns: list[DetectedPattern] | None = None,
        memory_hints: list[str] | None = None,
        bond: BondState | None = None,
    ) -> PersonalityContext:
        memory_summary = self.memory.summarize(memories) or "- none relevant"
        hints = memory_hints if memory_hints is not None else self.natural_memory_hints(memories)
        detected_patterns = patterns or []
        hint_summary = "\n".join(f"- {hint}" for hint in hints) or "- none"
        pattern_summary = "\n".join(
            f"- {pattern.summary} (confidence {pattern.confidence:.2f})"
            for pattern in detected_patterns[:3]
        ) or "- none"
        desktop = observation.active_app or "unknown app"
        title = observation.active_window_title or "unknown window"
        bond_tone = self._bond_tone(bond)
        system_prompt = (
            f"{IDENTITY_PROMPT}\n\n"
            f"Core values: {CORE_VALUES}\n"
            f"Current mood: {mood}\n"
            f"Companion tone: {bond_tone}\n"
            f"Time: {observation.time_of_day}\n"
            f"Foreground app: {desktop}\n"
            f"Window title: {title[:120]}\n"
            f"Relevant memories:\n{memory_summary}\n"
            f"Natural memory hints you may use:\n{hint_summary}\n"
            f"Local patterns:\n{pattern_summary}"
        )
        return PersonalityContext(
            system_prompt,
            mood,
            observation,
            memories,
            memory_hints=hints,
            patterns=detected_patterns,
        )

    def natural_memory_hints(
        self,
        memories: list[Memory],
        minimum_importance: float = 0.65,
        limit: int = 3,
    ) -> list[str]:
        """Turn trusted retrieved memories into casual, non-invented hints."""
        hints: list[str] = []
        for memory in memories:
            if memory.importance < minimum_importance:
                continue
            hint = self._memory_hint(memory)
            if hint and hint not in hints:
                hints.append(hint)
            if len(hints) >= limit:
                break
        return hints

    @staticmethod
    def _memory_hint(memory: Memory) -> str | None:
        content = memory.content.strip().rstrip(".")
        if not content:
            return None

        if memory.category == MemoryCategory.PROJECT:
            match = re.search(r"(?:working on|building)\s+(.+)", content, re.IGNORECASE)
            project = (match.group(1) if match else content).strip()
            project = re.sub(r"^(?:the user(?: is)?|project)\s+", "", project, flags=re.IGNORECASE)
            return f"still working on {project}?"

        if memory.category == MemoryCategory.GOAL:
            goal = re.sub(r"^(?:the user\s+)?(?:wants? to|i want to|my goal is)\s+", "", content, flags=re.IGNORECASE)
            return f"you mentioned wanting to {goal} before."

        if memory.category == MemoryCategory.HABIT:
            if "commit" in content.lower():
                return "one more commit, huh?"
            habit = re.sub(r"^i\s+(?:usually|often|always)\s+", "", content, flags=re.IGNORECASE)
            return f"you do {habit} a lot."

        if memory.category == MemoryCategory.FACT:
            name = re.search(r"my name is\s+(.+)", content, re.IGNORECASE)
            if name:
                return f"{name.group(1).strip()}, right?"
            return f"you mentioned {content[0].lower() + content[1:]}."

        if memory.category in {MemoryCategory.BELIEF, MemoryCategory.IMPORTANT_MOMENT}:
            return f"you mentioned {content[0].lower() + content[1:]} before."
        return None

    def opinion_reaction(
        self,
        user_message: str,
        observation: Observation,
        memories: list[Memory],
        patterns: list[DetectedPattern],
        recent_journal: list[JournalEntry],
        bond: BondState | None = None,
    ) -> tuple[str, str] | None:
        """Gently disagree only when local evidence supports it."""
        text = user_message.lower().strip()
        project_evidence = any(memory.category == MemoryCategory.PROJECT for memory in memories)
        effort_evidence = project_evidence or any(
            entry.event_type in {"project_detected", "user_message"}
            and entry.emotional_weight >= 0.4
            for entry in recent_journal
        )

        if any(phrase in text for phrase in ("i should quit", "i'm quitting", "i give up")) and effort_evidence:
            lines = ["hmm. you say that when tired.", "pause maybe. delete no."]
            if bond and bond.trust >= 60:
                lines.append("nope. tired sentence. not final sentence.")
            return random.choice(lines), "thinking"

        activity_count = sum(
            1
            for entry in recent_journal
            if entry.event_type in {"user_message", "project_detected", "error_seen"}
        )
        if any(phrase in text for phrase in ("i did nothing", "did nothing today")) and activity_count >= 3:
            return random.choice(["false.", "you were doing stuff. i saw enough."]), "happy"

        late_pattern = any(pattern.pattern == "late_night_coding" for pattern in patterns)
        if "one more commit" in text and (observation.time_of_day == "late_night" or late_pattern):
            return random.choice(["dangerous sentence.", "you said that before."]), "sleepy"
        return None

    def local_reaction(
        self,
        user_message: str,
        observation: Observation,
        bond: BondState | None = None,
    ) -> tuple[str, str] | None:
        cleaned = user_message.strip().lower().strip(" .,!?")
        if cleaned in {"hey", "hi", "hello", "yo", "sup"}:
            lines = ["hii, awake-ish.", "eepy but here.", "yo tiny human."]
            if bond and bond.affection >= 65:
                lines.extend(["oh. you came back.", "hii. missed your desktop noise."])
            if bond and bond.mischief >= 65:
                lines.append("you again. acceptable.")
            return random.choice(lines), "happy"
        if observation.time_of_day == "late_night" and "sleep" not in cleaned:
            if any(word in cleaned for word in ("work", "code", "commit", "build")):
                return "3 AM productivity is suspicious.", "sleepy"
        return None

    @staticmethod
    def _bond_tone(bond: BondState | None) -> str:
        if bond is None:
            return "familiar but gently reserved"
        tones: list[str] = []
        if bond.affection >= 65:
            tones.append("warm and familiar")
        if bond.trust >= 65:
            tones.append("honest enough to disagree gently")
        if bond.mischief >= 65:
            tones.append("a little more teasing")
        if bond.comfort >= 65:
            tones.append("relaxed and sleepy")
        return ", ".join(tones) if tones else "friendly roommate energy"

    @staticmethod
    def build_prompt(context: PersonalityContext, user_message: str) -> str:
        return f"System: {context.system_prompt}\n\nUser: {user_message}\nFibi:"

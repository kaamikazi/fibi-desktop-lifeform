"""Deterministic extraction of useful long-term memory statements."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedMemory:
    category: str
    content: str
    memory_key: str
    importance: float
    confidence: float


class StructuredMemoryEngine:
    """Extract explicit facts and decisions without model calls or broad guessing."""

    RELATIONS = {
        "sister", "brother", "mother", "mom", "father", "dad", "partner", "wife", "husband",
        "friend", "daughter", "son",
    }

    def extract(self, text: str) -> list[ExtractedMemory]:
        cleaned = " ".join((text or "").strip().split())
        if not cleaned or "?" in cleaned:
            return []
        candidates: list[ExtractedMemory] = []
        for sentence in re.split(r"(?<=[.!])\s+", cleaned):
            item = self._extract_sentence(sentence.strip().rstrip(".!"))
            if item and item.memory_key not in {candidate.memory_key for candidate in candidates}:
                candidates.append(item)
        return candidates

    def for_explicit_remember(self, text: str) -> ExtractedMemory:
        extracted = self.extract(text)
        if extracted:
            return extracted[0]
        content = " ".join(text.strip().split()).rstrip(".") + "."
        key_text = re.sub(r"[^a-z0-9]+", ":", content.lower()).strip(":")[:100]
        return ExtractedMemory("user_fact", content, f"explicit:{key_text}", 0.8, 0.9)

    def _extract_sentence(self, sentence: str) -> ExtractedMemory | None:
        name = re.fullmatch(r"my name is\s+(.+)", sentence, re.IGNORECASE)
        if name:
            value = name.group(1).strip()
            return ExtractedMemory("user_fact", f"The user's name is {value}.", "user:name", 0.95, 0.98)

        relation = re.fullmatch(
            r"my\s+(sister|brother|mother|mom|father|dad|partner|wife|husband|friend|daughter|son)\s+"
            r"(studies|works at|works as|lives in|likes|loves|is)\s+(.+)",
            sentence,
            re.IGNORECASE,
        )
        if relation:
            subject, predicate, value = (part.strip() for part in relation.groups())
            predicate_key = {"studies": "study", "works at": "workplace", "works as": "occupation", "lives in": "location", "is": "description"}.get(predicate.lower(), predicate.lower())
            return ExtractedMemory(
                "relationship",
                f"The user's {subject.lower()} {predicate.lower()} {value}.",
                f"relationship:{subject.lower()}:{predicate_key}",
                0.82,
                0.92,
            )

        preference = re.fullmatch(r"i\s+(?:prefer|like|love)\s+(.+)", sentence, re.IGNORECASE)
        if preference:
            value = preference.group(1).strip()
            subject = re.split(r"\s+(?:over|more than|because)\s+", value, maxsplit=1, flags=re.IGNORECASE)[0]
            key = re.sub(r"[^a-z0-9]+", ":", subject.lower()).strip(":")[:70]
            return ExtractedMemory("preference", f"The user prefers {value}.", f"preference:{key}", 0.72, 0.85)

        favorite = re.fullmatch(r"my favorite\s+(.+?)\s+is\s+(.+)", sentence, re.IGNORECASE)
        if favorite:
            kind, value = (part.strip() for part in favorite.groups())
            key = re.sub(r"[^a-z0-9]+", ":", kind.lower()).strip(":")[:70]
            return ExtractedMemory("preference", f"The user's favorite {kind} is {value}.", f"favorite:{key}", 0.78, 0.9)

        project = re.fullmatch(r"(?:i am |i'm )?(?:working on|building)\s+(.+)", sentence, re.IGNORECASE)
        if project:
            value = project.group(1).strip()
            key = re.sub(r"[^a-z0-9]+", ":", value.lower()).strip(":")[:70]
            return ExtractedMemory("project", f"The user is working on {value}.", f"project:{key}", 0.82, 0.9)

        decision = re.fullmatch(r"(?:i|we)\s+(?:have\s+)?decided\s+(?:to\s+)?(.+)", sentence, re.IGNORECASE)
        if decision:
            value = decision.group(1).strip()
            key = re.sub(r"[^a-z0-9]+", ":", value.lower()).strip(":")[:70]
            return ExtractedMemory("decision", f"The user decided to {value}.", f"decision:{key}", 0.86, 0.92)

        goal = re.fullmatch(r"(?:i want to|my goal is(?: to)?)\s+(.+)", sentence, re.IGNORECASE)
        if goal:
            value = goal.group(1).strip()
            key = re.sub(r"[^a-z0-9]+", ":", value.lower()).strip(":")[:70]
            return ExtractedMemory("goal", f"The user's goal is to {value}.", f"goal:{key}", 0.84, 0.9)

        event = re.fullmatch(r"(?:important|remember this):?\s+(.+)", sentence, re.IGNORECASE)
        if event:
            value = event.group(1).strip()
            key = re.sub(r"[^a-z0-9]+", ":", value.lower()).strip(":")[:70]
            return ExtractedMemory("important_event", value.rstrip(".") + ".", f"event:{key}", 0.9, 0.9)
        return None

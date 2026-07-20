"""Small semantic version comparison helpers for local update prep."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VersionComparison:
    current: str
    latest: str
    relation: str
    valid: bool = True
    error: str = ""


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"\s*v?(\d+)\.(\d+)\.(\d+)\s*", value or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def compare_versions(current: str, latest: str) -> VersionComparison:
    current_parsed = parse_version(current)
    latest_parsed = parse_version(latest)
    if current_parsed is None or latest_parsed is None:
        return VersionComparison(current, latest, "invalid", False, "invalid semantic version")
    if current_parsed < latest_parsed:
        relation = "older"
    elif current_parsed > latest_parsed:
        relation = "newer"
    else:
        relation = "equal"
    return VersionComparison(current, latest, relation)


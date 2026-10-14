from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fibi.engines import action_confirmation_engine as confirmation_module
from fibi.engines.action_confirmation_engine import ActionConfirmationEngine
from fibi.engines.types import ActionIntent


class FrozenDateTime(datetime):
    current: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current.replace(tzinfo=None)
        return cls.current.astimezone(tz)


def _engine(monkeypatch, state_path: Path, current: datetime) -> ActionConfirmationEngine:
    FrozenDateTime.current = current
    monkeypatch.setattr(confirmation_module, "datetime", FrozenDateTime)
    state_path.write_text(json.dumps({"other_state": {"keep": True}}), encoding="utf-8")
    return ActionConfirmationEngine(state_path, ttl_seconds=30)


def test_persisted_deadline_precision_and_expiration_boundary(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "state.json"
    start = datetime(2026, 1, 1, 12, 0, 0, 750000, tzinfo=timezone.utc)
    engine = _engine(monkeypatch, state_path, start)

    pending = engine.create(ActionIntent("shutdown_pc"))
    created = datetime.fromisoformat(pending.created_at)
    expires = datetime.fromisoformat(pending.expires_at)

    # Both persisted timestamps retain the existing seconds precision, so the
    # configured integer TTL remains exactly 30 seconds after serialization.
    assert created == start.replace(microsecond=0)
    assert expires == (start + timedelta(seconds=30)).replace(microsecond=0)
    assert expires - created == timedelta(seconds=30)

    FrozenDateTime.current = expires
    assert engine.pending() is not None  # Existing strict `now > expires` boundary.
    FrozenDateTime.current = expires + timedelta(microseconds=1)
    assert engine.pending() is None
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"other_state": {"keep": True}}


def test_confirmation_is_exact_one_shot_and_preserves_shared_state(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "state.json"
    engine = _engine(monkeypatch, state_path, datetime(2026, 1, 1, tzinfo=timezone.utc))
    created = engine.create(ActionIntent("shutdown_pc"))

    assert engine.consume_if_confirmed("confirm restart") is None
    assert engine.pending() is not None
    consumed = engine.consume_if_confirmed("  CONFIRM SHUTDOWN  ")
    assert consumed is not None and consumed.action_type == "shutdown_pc"
    assert engine.consume_if_confirmed("confirm shutdown") is None
    assert engine.pending() is None
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"other_state": {"keep": True}}
    assert datetime.fromisoformat(created.expires_at) > FrozenDateTime.current


def test_malformed_confirmation_state_fails_closed(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "state.json"
    engine = _engine(monkeypatch, state_path, datetime(2026, 1, 1, tzinfo=timezone.utc))

    state_path.write_text("not json", encoding="utf-8")
    assert engine.pending() is None

    state_path.write_text(
        json.dumps(
            {
                "other_state": {"keep": True},
                "pending_action": {
                    "action_type": "shutdown_pc",
                    "expires_at": "not-a-timestamp",
                    "required_confirmation_phrase": "confirm shutdown",
                },
            }
        ),
        encoding="utf-8",
    )
    assert engine.pending() is None
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"other_state": {"keep": True}}

"""Builders for Quest Log exports shaped like the real thing (Settings → Back up)."""

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from quest_log_insights.app import app

Export = dict[str, Any]


def done(
    qid: int, name: str, day: str, *, g: str = "", xp: int = 10, via: str | None = None
) -> dict[str, Any]:
    e: dict[str, Any] = {"t": "quest", "at": 0, "day": day, "id": qid, "name": name, "g": g, "xp": xp}
    if via:
        e["via"] = via
    return e


@pytest.fixture
def week() -> Export:
    """A week like Jerry's: daily routines that would crowd the report, and a few rare wins."""
    days = [f"2026-10-{d}" for d in range(22, 29)]
    log: list[dict[str, Any]] = [done(4, "Walk Bash", d, g="Bash") for d in days]
    log += [done(11, "Apply to one job", d, g="Career", xp=20) for d in days[:5]]
    log += [
        done(200, "Shipped #65: self-hosted fonts", "2026-10-27", g="Programming", xp=20, via="claude"),
        done(201, "Shipped #27: ESLint 10", "2026-10-27", g="Programming", xp=15, via="claude"),
        done(202, "Apply: Senior SWE @ Rumi", "2026-10-27", g="Career", xp=30, via="claude"),
        done(203, "Shipped the privacy review (#30)", "2026-10-26", g="Programming", xp=50, via="claude"),
        # private things the report must never read or echo
        {"t": "mood", "at": 0, "day": "2026-10-27", "v": 3, "s": 10, "note": "slept on the beach", "xp": 5},
    ]
    return {
        "v": 7,
        "xp": 2170,
        "quests": [
            {"id": 4, "name": "Walk Bash", "g": "Bash", "repeat": "daily"},
            {"id": 11, "name": "Apply to one job", "g": "Career", "repeat": "weekdays"},
            {"id": 200, "name": "Shipped #65: self-hosted fonts", "g": "Programming", "repeat": "none"},
        ],
        "log": log,
        "moods": [{"at": 0, "day": "2026-10-27", "v": 3, "s": 10, "note": "slept on the beach"}],
        "notes": [{"at": 0, "text": "You've come back before."}],
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def d(s: str) -> date:
    return date.fromisoformat(s)

"""What comes in (a Quest Log export) and what goes out (the report).

Only the parts of an export the report needs are read. Everything else in the file (check-ins,
notes, moments, loot) is ignored by the models and never looked at.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Name = Annotated[str, Field(max_length=200)]


class _In(BaseModel):
    model_config = ConfigDict(extra="ignore")


class QuestIn(_In):
    """A quest as Quest Log stores it. Only `repeat` matters here: it tells routines from wins."""

    id: int
    name: Name = ""
    g: Name = ""
    repeat: str = "none"


class LogEntryIn(_In):
    """One line of Quest Log's activity log. Only `t == "quest"` entries (a quest done) are used."""

    t: str
    at: int = 0
    day: date | None = None
    id: int | None = None
    name: Name = ""
    g: Name = ""
    xp: int = Field(default=0, ge=0, le=1000)
    via: str | None = None


class ExportIn(_In):
    """A Quest Log export (Settings → Back up). Extra fields are allowed and ignored."""

    quests: list[QuestIn] = Field(default_factory=list, max_length=20_000)
    log: list[LogEntryIn] = Field(default_factory=list, max_length=200_000)


class Period(BaseModel):
    start: date
    end: date
    days: int


class Totals(BaseModel):
    done: int = Field(description="Quests checked off in the period, wins and routines together")
    wins: int = Field(description="One-off accomplishments")
    routine: int = Field(description="Check-offs of repeating quests")
    xp: int
    active_days: int


class Win(BaseModel):
    name: str
    area: str
    day: date
    xp: int
    with_claude: bool = Field(description="Logged through the Claude connector")


class Area(BaseModel):
    area: str
    done: int
    wins: int
    xp: int


class Routine(BaseModel):
    name: str
    area: str
    times: int


class Report(BaseModel):
    """Wins first (the rare things worth telling people about), then areas, then routines."""

    period: Period
    headline: str
    totals: Totals
    wins: list[Win]
    areas: list[Area]
    routines: list[Routine]
    kind: Literal["quest-log-insights/report"] = "quest-log-insights/report"
    version: Literal[1] = 1

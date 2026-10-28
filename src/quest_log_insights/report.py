"""Builds the accomplishments report. Pure functions: no I/O, no clock, easy to test.

The rule that matters: a routine (a repeating quest like "Walk Bash") is counted, not listed, so
it can never crowd out a one-off win (like "Shipped #65"). That was the bug in Quest Log's own
"Share how I'm doing", which named only the most-repeated quests.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date, timedelta

from .models import Area, ExportIn, LogEntryIn, Period, Report, Routine, Totals, Win

DEFAULT_DAYS = 7
MAX_DAYS = 366
OTHER = "Other"


class PeriodError(ValueError):
    """The requested dates don't make a usable period."""


def quest_events(export: ExportIn) -> list[LogEntryIn]:
    """Quests checked off, with a day. Everything else in the log is skipped."""
    return [e for e in export.log if e.t == "quest" and e.day is not None]


def resolve_period(events: Iterable[LogEntryIn], start: date | None, end: date | None) -> Period:
    """Fills in missing dates: `end` defaults to the last day anything was done (or `start` plus
    a week), `start` to a week before `end`. Raises PeriodError for a backwards or too-long period."""
    days = [e.day for e in events if e.day is not None]
    if end is None:
        if start is not None:
            end = start + timedelta(days=DEFAULT_DAYS - 1)
        elif days:
            end = max(days)
        else:
            raise PeriodError("Nothing was done in this export, so pass start and end.")
    if start is None:
        start = end - timedelta(days=DEFAULT_DAYS - 1)
    if start > end:
        raise PeriodError("start is after end.")
    span = (end - start).days + 1
    if span > MAX_DAYS:
        raise PeriodError(f"The period can be at most {MAX_DAYS} days.")
    return Period(start=start, end=end, days=span)


def _area(e: LogEntryIn) -> str:
    return e.g.strip() or OTHER


def _routine_ids(export: ExportIn, events: list[LogEntryIn]) -> set[int]:
    """Quest ids that are routines: repeating quests, plus (for quests since deleted, so their
    schedule is unknown) any quest done more than once in the period."""
    ids = {q.id for q in export.quests if q.repeat != "none"}
    known = {q.id for q in export.quests}
    counts = Counter(e.id for e in events if e.id is not None and e.id not in known)
    ids |= {i for i, n in counts.items() if n > 1}
    return ids


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def headline(totals: Totals) -> str:
    if not totals.done:
        return "Nothing checked off in this period. That's allowed."
    parts = [plural(totals.wins, "win")]
    if totals.routine:
        parts.append(plural(totals.routine, "routine check-off"))
    return f"{' and '.join(parts)} across {plural(totals.active_days, 'active day')}."


def build_report(export: ExportIn, start: date | None = None, end: date | None = None) -> Report:
    all_events = quest_events(export)
    period = resolve_period(all_events, start, end)
    events = [e for e in all_events if e.day is not None and period.start <= e.day <= period.end]
    routine_ids = _routine_ids(export, events)
    is_routine = [e.id is not None and e.id in routine_ids for e in events]

    wins = sorted(
        (
            Win(name=e.name, area=_area(e), day=e.day, xp=e.xp, with_claude=e.via == "claude")
            for e, r in zip(events, is_routine, strict=True)
            if not r and e.day is not None
        ),
        key=lambda w: (-w.xp, w.day, w.name),
    )

    by_area: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # done, wins, xp
    for e, r in zip(events, is_routine, strict=True):
        a = by_area[_area(e)]
        a[0] += 1
        a[1] += 0 if r else 1
        a[2] += e.xp
    areas = sorted(
        (Area(area=k, done=v[0], wins=v[1], xp=v[2]) for k, v in by_area.items()),
        key=lambda a: (-a.wins, -a.done, a.area),
    )

    routine_counts: Counter[tuple[str, str]] = Counter(
        (e.name, _area(e)) for e, r in zip(events, is_routine, strict=True) if r
    )
    routines = sorted(
        (Routine(name=n, area=a, times=t) for (n, a), t in routine_counts.items()),
        key=lambda r: (-r.times, r.name),
    )

    totals = Totals(
        done=len(events),
        wins=len(wins),
        routine=len(events) - len(wins),
        xp=sum(e.xp for e in events),
        active_days=len({e.day for e in events}),
    )
    return Report(
        period=period,
        headline=headline(totals),
        totals=totals,
        wins=wins,
        areas=areas,
        routines=routines,
    )

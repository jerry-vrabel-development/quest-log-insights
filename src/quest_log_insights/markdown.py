"""The report as Markdown: something to paste into a brag doc, a portfolio, or a note to a coach."""

from collections import defaultdict
from datetime import date

from .models import Report, Win
from .report import plural


def fmt_day(d: date) -> str:
    return f"{d:%b} {d.day}"


def fmt_period(start: date, end: date) -> str:
    if start == end:
        return f"{fmt_day(start)}, {start.year}"
    if start.year == end.year:
        return f"{fmt_day(start)} – {fmt_day(end)}, {end.year}"
    return f"{fmt_day(start)}, {start.year} – {fmt_day(end)}, {end.year}"


def _win_line(w: Win) -> str:
    return f"- {w.name} ({fmt_day(w.day)}, +{w.xp} XP)"


def to_markdown(r: Report) -> str:
    t = r.totals
    lines = [
        f"# Accomplishments · {fmt_period(r.period.start, r.period.end)}",
        "",
        r.headline,
        "",
        f"**{plural(t.wins, 'win')} · {plural(t.routine, 'routine check-off')} · "
        f"{plural(t.active_days, 'active day')} · {t.xp} XP**",
    ]
    if r.wins:
        lines += ["", "## Wins"]
        grouped: defaultdict[str, list[Win]] = defaultdict(list)
        for w in r.wins:
            grouped[w.area].append(w)
        for area in (a.area for a in r.areas if a.area in grouped):
            lines += ["", f"### {area}", ""]
            lines += [_win_line(w) for w in grouped[area]]
    if r.routines:
        lines += ["", "## Routines kept", ""]
        lines += [f"- {x.name} ×{x.times}" for x in r.routines]
    return "\n".join(lines) + "\n"

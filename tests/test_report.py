from datetime import date

import pytest

from quest_log_insights.markdown import fmt_period, to_markdown
from quest_log_insights.models import ExportIn, Report
from quest_log_insights.report import MAX_DAYS, PeriodError, build_report, resolve_period

from .conftest import Export, d, done


def report(export: Export, start: str | None = None, end: str | None = None) -> Report:
    return build_report(
        ExportIn.model_validate(export),
        d(start) if start else None,
        d(end) if end else None,
    )


def test_one_off_wins_are_listed_and_routines_are_only_counted(week: Export) -> None:
    r = report(week)
    names = [w.name for w in r.wins]
    assert "Walk Bash" not in names
    assert "Apply to one job" not in names
    assert names[0] == "Shipped the privacy review (#30)"  # biggest win first
    assert set(names) == {
        "Shipped the privacy review (#30)",
        "Apply: Senior SWE @ Rumi",
        "Shipped #65: self-hosted fonts",
        "Shipped #27: ESLint 10",
    }
    assert [(x.name, x.times) for x in r.routines] == [("Walk Bash", 7), ("Apply to one job", 5)]


def test_totals_add_up(week: Export) -> None:
    t = report(week).totals
    assert (t.done, t.wins, t.routine, t.active_days) == (16, 4, 12, 7)
    assert t.xp == 7 * 10 + 5 * 20 + 20 + 15 + 30 + 50
    assert report(week).headline == "4 wins and 12 routine check-offs across 7 active days."


def test_areas_rank_by_wins_then_activity(week: Export) -> None:
    areas = report(week).areas
    assert [(a.area, a.wins, a.done) for a in areas] == [
        ("Programming", 3, 3),
        ("Career", 1, 6),
        ("Bash", 0, 7),
    ]


def test_wins_logged_through_claude_are_marked(week: Export) -> None:
    assert all(w.with_claude for w in report(week).wins)


def test_private_parts_of_the_export_are_never_read(week: Export) -> None:
    out = report(week).model_dump_json() + to_markdown(report(week))
    assert "slept on the beach" not in out
    assert "come back before" not in out


def test_a_deleted_quest_done_repeatedly_counts_as_a_routine() -> None:
    export = {"log": [done(9, "Stretch", "2026-10-01"), done(9, "Stretch", "2026-10-02")]}
    r = report(export)
    assert r.wins == []
    assert [(x.name, x.times) for x in r.routines] == [("Stretch", 2)]


def test_a_deleted_quest_done_once_is_a_win() -> None:
    r = report({"log": [done(9, "Fix the sink", "2026-10-02", g="Home")]})
    assert [w.name for w in r.wins] == ["Fix the sink"]


def test_quests_without_an_area_go_under_other() -> None:
    r = report({"log": [done(1, "Something", "2026-10-02", g="  ")]})
    assert r.areas[0].area == "Other"


def test_only_the_period_counts(week: Export) -> None:
    r = report(week, "2026-10-27", "2026-10-27")
    assert r.period.days == 1
    assert {w.name for w in r.wins} == {
        "Shipped #65: self-hosted fonts",
        "Shipped #27: ESLint 10",
        "Apply: Senior SWE @ Rumi",
    }


def test_an_empty_period_says_so_kindly(week: Export) -> None:
    r = report(week, "2026-01-01", "2026-01-07")
    assert r.totals.done == 0
    assert r.headline == "Nothing checked off in this period. That's allowed."
    assert to_markdown(r).count("##") == 0


def test_singular_words() -> None:
    r = report({"log": [done(1, "One thing", "2026-10-02")]})
    assert r.headline == "1 win across 1 active day."
    assert "**1 win · 0 routine check-offs · 1 active day · 10 XP**" in to_markdown(r)


class TestPeriod:
    def test_defaults_to_the_week_ending_on_the_last_active_day(self, week: Export) -> None:
        p = report(week).period
        assert (p.start, p.end, p.days) == (date(2026, 10, 22), date(2026, 10, 28), 7)

    def test_start_alone_means_a_week_from_start(self) -> None:
        p = resolve_period([], d("2026-10-01"), None)
        assert (p.end, p.days) == (date(2026, 10, 7), 7)

    def test_end_alone_means_the_week_before(self) -> None:
        assert resolve_period([], None, d("2026-10-07")).start == date(2026, 10, 1)

    def test_backwards_is_an_error(self) -> None:
        with pytest.raises(PeriodError, match="after"):
            resolve_period([], d("2026-10-07"), d("2026-10-01"))

    def test_too_long_is_an_error(self) -> None:
        with pytest.raises(PeriodError, match=str(MAX_DAYS)):
            resolve_period([], d("2025-01-01"), d("2026-10-01"))

    def test_nothing_done_and_no_dates_is_an_error(self) -> None:
        with pytest.raises(PeriodError, match="start and end"):
            resolve_period([], None, None)


class TestMarkdown:
    def test_wins_grouped_by_area_then_routines(self, week: Export) -> None:
        md = to_markdown(report(week))
        assert md.startswith("# Accomplishments · Oct 22 – Oct 28, 2026\n")
        assert "**4 wins · 12 routine check-offs · 7 active days · 285 XP**" in md
        assert md.index("### Programming") < md.index("### Career") < md.index("## Routines kept")
        assert "- Shipped the privacy review (#30) (Oct 26, +50 XP)" in md
        assert "- Walk Bash ×7" in md
        assert "### Bash" not in md  # no wins there, so no heading

    @pytest.mark.parametrize(
        ("start", "end", "text"),
        [
            ("2026-10-28", "2026-10-28", "Oct 28, 2026"),
            ("2026-10-01", "2026-10-28", "Oct 1 – Oct 28, 2026"),
            ("2025-12-29", "2026-01-04", "Dec 29, 2025 – Jan 4, 2026"),
        ],
    )
    def test_period_formats(self, start: str, end: str, text: str) -> None:
        assert fmt_period(d(start), d(end)) == text

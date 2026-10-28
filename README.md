# Quest Log Insights

A small **FastAPI** service that turns a [Quest Log](https://github.com/jerry-vrabel-development/quest-log) export into an **accomplishments report**: one-off wins first, then each area of life, then routines with counts. It runs on **Cloudflare Workers** (Python), next to Quest Log, and stores nothing.

**Live:** https://quest-log-insights.forwardslash.workers.dev/docs (interactive API docs)

## Why

Quest Log's "Share how I'm doing" named only your two most-repeated quests. A week of shipping three features and applying to three jobs came out as "Walk Bash (7 times) and Apply to one job (5 times)." Daily habits crowded out the rare wins, which are the ones worth telling people about.

This service fixes the ranking. **Routines are counted, not listed**, so they can never push a win out of the report:

```markdown
# Accomplishments · Oct 22 – Oct 28, 2026

4 wins and 12 routine check-offs across 7 active days.

**4 wins · 12 routine check-offs · 7 active days · 285 XP**

## Wins

### Programming

- Shipped the privacy review (#30) (Oct 26, +50 XP)
- Shipped #65: self-hosted fonts (Oct 27, +20 XP)
- Shipped #27: ESLint 10 (Oct 27, +15 XP)

### Career

- Apply: Senior SWE @ Rumi (Oct 27, +30 XP)

## Routines kept

- Walk Bash ×7
- Apply to one job ×5
```

## API

| Method | Path            | Returns                                 |
| ------ | --------------- | --------------------------------------- |
| `POST` | `/v1/report`    | The report as JSON (schema in `/docs`)  |
| `POST` | `/v1/report.md` | The report as Markdown                  |
| `GET`  | `/health`       | `{"ok": true}`                          |
| `GET`  | `/docs`         | Interactive OpenAPI docs                |

The body is a Quest Log export file, as is (**Settings → Back up → Export**). Optional query parameters `start` and `end` (`YYYY-MM-DD`) set the period; by default it's the week ending on the last day anything was done. Periods can be up to 366 days.

```bash
curl -X POST "https://quest-log-insights.forwardslash.workers.dev/v1/report.md?start=2026-10-22&end=2026-10-28" \
  -H "content-type: application/json" --data-binary @quest-log-backup-2026-10-28.json
```

**How wins and routines are told apart:** a quest with a repeat schedule (daily, weekdays, weekly, monthly) is a routine. For quests that have since been deleted (so their schedule is unknown), one done more than once in the period counts as a routine. Everything else is a win, ranked by XP.

## Privacy

- **Nothing is stored or logged.** An export comes in, a report goes out, and the request is gone.
- **Only finished quests are read.** The models ignore everything else in the export: check-ins, notes, moments and loot are never parsed, so they can't leak into a report. A test checks this.
- Responses are `no-store`, with `nosniff` and `no-referrer`. CORS allows only the Quest Log app. Exports over 10 MB are refused before they're read.

## Design

```
src/
  worker.py                 Cloudflare entry point: wraps the ASGI app (no uvicorn)
  quest_log_insights/
    models.py               Pydantic models: the export in, the report out
    report.py               Pure functions: period, ranking, totals (no I/O, no clock)
    markdown.py             The report as Markdown
    app.py                  FastAPI routes, CORS, size limit, security headers
tests/                      pytest: the ranking, periods, Markdown, and the HTTP API
```

The report logic is pure functions over typed models, so it's tested without a server. The HTTP layer is tested through FastAPI's `TestClient`. `worker.py` is the only file that touches the Workers runtime.

## Develop

Needs [uv](https://docs.astral.sh/uv/) (0.13.4 or later) and Node.js (for Wrangler).

```bash
uv sync                    # install
uv run pytest              # tests, with a 95% coverage floor (currently 100%)
uv run ruff format --check . && uv run ruff check .
uv run mypy                # strict
uv run pywrangler dev      # run on the Workers runtime at http://localhost:8787
uv run pywrangler deploy   # deploy to Cloudflare
```

CI runs format, lint, types and tests on Python 3.13 and 3.14 for every push and pull request. Production runs Python 3.14 (selected by the `compatibility_date` in `wrangler.jsonc`).

## Stack

Python 3.13+ · FastAPI · Pydantic v2 · Cloudflare Python Workers (Pyodide) · uv · pytest · mypy (strict) · Ruff · GitHub Actions

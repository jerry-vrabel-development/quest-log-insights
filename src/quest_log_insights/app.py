"""The HTTP API. Stateless: an export comes in, a report goes out, and nothing is stored or logged."""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from . import __version__
from .markdown import to_markdown
from .models import ExportIn, Report
from .report import PeriodError, build_report

MAX_BODY_BYTES = 10 * 1024 * 1024
QUEST_LOG_ORIGIN = "https://quest-log.forwardslash.workers.dev"

DESCRIPTION = """
Turns a Quest Log export (Settings → Back up) into an accomplishments report: one-off wins first,
then each area of life, then routines with counts, so daily habits never crowd out the rare wins.

**Privacy:** nothing is stored or logged. Only finished quests are read; check-ins, notes and
moments in the export are ignored.
"""

Start = Annotated[date | None, Query(description="First day (YYYY-MM-DD). Default: a week before end.")]
End = Annotated[date | None, Query(description="Last day. Default: the last day anything was done.")]
Export = Annotated[ExportIn, Body(description="A Quest Log export file, as is.")]


def _report(export: ExportIn, start: date | None, end: date | None) -> Report:
    try:
        return build_report(export, start, end)
    except PeriodError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def create_app() -> FastAPI:
    app = FastAPI(title="Quest Log Insights", version=__version__, description=DESCRIPTION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[QUEST_LOG_ORIGIN],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    @app.middleware("http")
    async def guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        length = request.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
            return JSONResponse({"detail": "Export is too large (10 MB at most)."}, status_code=413)
        response = await call_next(request)
        response.headers["cache-control"] = "no-store"
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        return response

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": "Quest Log Insights", "version": __version__, "docs": "/docs"}

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/v1/report", tags=["report"], summary="Accomplishments report as JSON")
    def report_json(export: Export, start: Start = None, end: End = None) -> Report:
        return _report(export, start, end)

    @app.post(
        "/v1/report.md",
        tags=["report"],
        summary="Accomplishments report as Markdown",
        response_class=PlainTextResponse,
        responses={200: {"content": {"text/markdown": {}}}},
    )
    def report_markdown(export: Export, start: Start = None, end: End = None) -> PlainTextResponse:
        md = to_markdown(_report(export, start, end))
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")

    return app


app = create_app()

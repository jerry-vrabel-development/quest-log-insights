from fastapi.testclient import TestClient

from quest_log_insights.app import MAX_BODY_BYTES, QUEST_LOG_ORIGIN

from .conftest import Export


def test_health_and_root(client: TestClient) -> None:
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/").json()["docs"] == "/docs"


def test_report_as_json(client: TestClient, week: Export) -> None:
    res = client.post("/v1/report", json=week)
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "quest-log-insights/report"
    assert body["totals"]["wins"] == 4
    assert body["wins"][0]["name"] == "Shipped the privacy review (#30)"


def test_report_as_markdown(client: TestClient, week: Export) -> None:
    res = client.post("/v1/report.md", json=week, params={"start": "2026-10-26", "end": "2026-10-27"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/markdown")
    assert res.text.startswith("# Accomplishments · Oct 26 – Oct 27, 2026")


def test_bad_periods_are_422_with_a_reason(client: TestClient, week: Export) -> None:
    res = client.post("/v1/report", json=week, params={"start": "2026-10-28", "end": "2026-10-01"})
    assert res.status_code == 422
    assert "after" in res.json()["detail"]
    assert client.post("/v1/report", json={"log": []}).status_code == 422


def test_malformed_exports_are_rejected(client: TestClient) -> None:
    assert client.post("/v1/report", json={"log": [{"t": "quest", "day": "not a date"}]}).status_code == 422
    assert (
        client.post(
            "/v1/report", content=b"not json", headers={"content-type": "application/json"}
        ).status_code
        == 422
    )


def test_oversized_exports_are_refused_before_reading(client: TestClient) -> None:
    res = client.post("/v1/report", content=b"{}", headers={"content-length": str(MAX_BODY_BYTES + 1)})
    assert res.status_code == 413


def test_responses_are_never_cached_and_carry_safe_headers(client: TestClient, week: Export) -> None:
    res = client.post("/v1/report", json=week)
    assert res.headers["cache-control"] == "no-store"
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["referrer-policy"] == "no-referrer"


def test_cors_allows_quest_log_only(client: TestClient) -> None:
    def preflight(origin: str) -> str | None:
        res = client.options(
            "/v1/report",
            headers={"origin": origin, "access-control-request-method": "POST"},
        )
        return res.headers.get("access-control-allow-origin")

    assert preflight(QUEST_LOG_ORIGIN) == QUEST_LOG_ORIGIN
    assert preflight("https://evil.example") is None


def test_openapi_docs_describe_the_api(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Quest Log Insights"
    assert {"/v1/report", "/v1/report.md", "/health"} <= set(spec["paths"])
    assert client.get("/docs").status_code == 200

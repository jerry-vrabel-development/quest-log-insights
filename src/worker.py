"""Cloudflare Workers entry point: serves the FastAPI app (no uvicorn; the Workers runtime is the server).

`workers` exists only inside the Workers runtime, so tests import `quest_log_insights.app` instead.
"""

from workers import asgi  # type: ignore[import-not-found]

from quest_log_insights.app import app

Default = asgi.entrypoint(app)

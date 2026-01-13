"""Convenience entrypoint so `uvicorn main:app` works.

The real FastAPI app lives in `app.main:app`.
"""

from app.main import app  # noqa: F401

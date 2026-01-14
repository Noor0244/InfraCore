"""Convenience entrypoint so `uvicorn main:app` works.

The real FastAPI app lives in `app.main:app`.
"""

from app.main import app  # noqa: F401


if __name__ == "__main__":
	# Render provides PORT; default to 10000 for local/dev.
	import os

	import uvicorn

	port = int(os.getenv("PORT", "10000"))
	uvicorn.run("app.main:app", host="0.0.0.0", port=port)

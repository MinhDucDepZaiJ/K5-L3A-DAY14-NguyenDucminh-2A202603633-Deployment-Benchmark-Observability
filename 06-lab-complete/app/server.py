"""Container entry point for the pinned Uvicorn release."""
import signal

import uvicorn

from .config import settings


def after_shutdown(_signum, _frame):
    # Uvicorn handles SIGTERM while serving, then replays it after cleanup.
    # The restored handler lets the container return exit code 0 at that point.
    pass


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, after_shutdown)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        timeout_graceful_shutdown=5,
        access_log=False,
    )

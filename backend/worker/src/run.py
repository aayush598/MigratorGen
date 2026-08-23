"""Entry point for migration worker service."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(
        "backend.worker.src.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )

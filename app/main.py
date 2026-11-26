"""Verify My Client web app."""

from fastapi import FastAPI

app = FastAPI(title="Verify My Client")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the app is up, with no version, build or environment details."""
    return {"status": "ok"}

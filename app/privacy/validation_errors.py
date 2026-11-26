"""App-wide 422 handler that never repeats submitted values (spec GH-8, AC4).

FastAPI's default 422 body includes each error's `input` (the submitted value)
and `ctx`. Here each error keeps only `type`, `loc` and `msg`.
"""

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

KEPT_ERROR_KEYS = ("type", "loc", "msg")


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    raw_errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    errors = [
        {key: error[key] for key in KEPT_ERROR_KEYS if key in error}
        for error in raw_errors
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(errors)},
    )

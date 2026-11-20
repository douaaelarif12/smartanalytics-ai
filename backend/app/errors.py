from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


async def api_error_handler(_: Request, error: ApiError) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": error.code, "message": error.message}}
    if error.details:
        body["error"]["details"] = error.details
    headers={"Retry-After":str((error.details or {}).get("retry_after_seconds",60))} if error.status_code == 429 else None
    return JSONResponse(status_code=error.status_code, content=body, headers=headers)


async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    issues = [
        {"location": list(issue["loc"]), "message": issue["msg"], "type": issue["type"]}
        for issue in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "The request contains invalid values.", "details": {"issues": issues}}},
    )


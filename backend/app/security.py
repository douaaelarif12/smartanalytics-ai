"""Authorize private routes before parsing uploads; bound all request bodies."""
import json
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.formparsers import MultiPartException
from .errors import ApiError


class BodyLimitExceeded(MultiPartException):
    pass


class APIAccessMiddleware:
    def __init__(self, app, auth):
        self.app = app
        self.auth = auth

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] != "OPTIONS" and (
            scope["path"].startswith(("/api/datasets", "/api/dashboards"))
            or scope["path"] == "/api/auth/usage"
        ):
            try:
                user = await run_in_threadpool(self.auth.require_user, Request(scope))
                scope.setdefault("state", {})["authenticated_user"] = user
            except ApiError as error:
                response = JSONResponse(
                    {"error": {"code": error.code, "message": error.message}}, status_code=error.status_code)
                return await response(scope, receive, send)
        await self.app(scope, receive, send)


class SecurityMiddleware:
    def __init__(self, app, max_upload_bytes):
        self.app = app
        self.max_upload_bytes = max_upload_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        upload = scope["path"] == "/api/datasets" and scope["method"] == "POST"
        limit = self.max_upload_bytes+65536 if upload else 65536
        error_body = {"error": {"code": "request_too_large",
                                "message": "The request exceeds the permitted size."}}

        async def reject():
            response = JSONResponse(error_body, status_code=413, headers={
                                    "Cache-Control": "no-store"})
            await response(scope, receive, send)
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = limit+1
        if length > limit:
            return await reject()
        consumed = 0
        started = False
        exceeded = False
        replacement_sent = False

        async def bounded_receive():
            nonlocal consumed, exceeded
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > limit:
                exceeded = True
                # The multipart parser closes its temporary files for this exception.
                raise BodyLimitExceeded("Request body limit exceeded")
            return message

        async def safe_send(message):
            nonlocal started, replacement_sent
            if exceeded:
                # FastAPI may translate parsing exceptions into HTTP 400. Preserve
                # the authoritative size error even for a chunked request.
                if message["type"] == "http.response.start":
                    message = {"type": "http.response.start", "status": 413,
                               "headers": [(b"content-type", b"application/json")]}
                elif message["type"] == "http.response.body":
                    if replacement_sent:
                        return
                    message = {"type": "http.response.body", "body": json.dumps(
                        error_body).encode(), "more_body": False}
                    replacement_sent = True
            if message["type"] == "http.response.start":
                started = True
                values = list(message.get("headers", []))
                values.extend([(b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"),
                              (b"x-frame-options", b"DENY"), (b"referrer-policy", b"no-referrer")])
                message = {**message, "headers": values}
            await send(message)
        try:
            await self.app(scope, bounded_receive, safe_send)
        except BodyLimitExceeded:
            if not started:
                await reject()

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .api import create_router
from .config import Settings
from .errors import ApiError, api_error_handler, validation_error_handler
from .service import DatasetService
from .database import Database
from .auth import AuthService, auth_router
from .limits import RateLimiter
from .security import APIAccessMiddleware, SecurityMiddleware
from .dashboard_api import create_dashboard_router
from .dashboard_service import DashboardService


def create_app(settings: Settings | None = None) -> FastAPI:
    effective_settings = settings or Settings.from_env()
    app = FastAPI(title="SmartAnalytics AI API", version="0.1.0")
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    database = Database(effective_settings)
    limiter = RateLimiter(database, effective_settings.redis_url, effective_settings.rate_limit_namespace)
    auth = AuthService(database, effective_settings, limiter)
    service = DatasetService(effective_settings, database)
    dashboard_service = DashboardService(service)
    service.limiter = limiter
    app.state.database = database
    app.state.auth = auth
    app.include_router(auth_router(auth))
    app.include_router(create_router(service, auth))
    app.include_router(create_dashboard_router(dashboard_service, auth))
    app.add_middleware(APIAccessMiddleware, auth=auth)
    app.add_middleware(SecurityMiddleware, max_upload_bytes=effective_settings.max_upload_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(effective_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    return app


class LazyApplication:
    """Keep the documented app.main:app entry point without DB writes on import.

    The runtime application is created on its first ASGI lifespan/request call.
    Tests and administrative tooling can import create_app without opening a
    connection to the operator's configured database.
    """

    def __init__(self):
        self.application: FastAPI | None = None

    async def __call__(self, scope, receive, send):
        if self.application is None:
            self.application = create_app()
        await self.application(scope, receive, send)


app = LazyApplication()

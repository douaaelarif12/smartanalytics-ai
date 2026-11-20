from __future__ import annotations

import os
import math
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import dotenv_values


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    max_upload_bytes: int = 20 * 1024 * 1024
    profile_cache_ttl_seconds: int = 10 * 60
    profile_cache_max_entries: int = 8
    profile_cache_max_bytes: int = 8 * 1024 * 1024
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")

    database_url: str | None = field(default=None, repr=False)
    redis_url: str | None = field(default=None, repr=False)
    rate_limit_namespace: str = "smartanalytics"
    environment: str = "development"
    cookie_secure: bool = True
    auto_migrate: bool = True
    session_ttl_seconds: int = 12 * 60 * 60
    session_idle_seconds: int = 30 * 60
    login_limit: int = 10
    ai_user_minute_limit: int = 10
    ai_user_daily_limit: int = 100
    ai_input_usd_per_million: float | None = None
    ai_output_usd_per_million: float | None = None

    def __post_init__(self):
        if not self.rate_limit_namespace or len(self.rate_limit_namespace) > 80 or not all(
            char.isascii() and (char.isalnum() or char in "_-") for char in self.rate_limit_namespace
        ):
            raise ValueError("RATE_LIMIT_NAMESPACE must contain 1-80 ASCII letters, digits, underscores or hyphens.")
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test or production.")
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or "*" in origin:
                raise ValueError(
                    "CORS origins must be explicit HTTP(S) origins without paths or wildcards.")
        if min(self.max_upload_bytes, self.profile_cache_ttl_seconds, self.profile_cache_max_entries, self.profile_cache_max_bytes, self.session_ttl_seconds, self.session_idle_seconds, self.login_limit, self.ai_user_minute_limit, self.ai_user_daily_limit) <= 0:
            raise ValueError("Resource and session limits must be positive.")
        if any(rate is not None and (not math.isfinite(rate) or rate < 0) for rate in (self.ai_input_usd_per_million, self.ai_output_usd_per_million)):
            raise ValueError("Configured token rates must be finite and non-negative.")
        if self.environment == "production" and (not self.cookie_secure or not self.redis_url):
            raise ValueError("Production requires Secure cookies and a shared Redis limiter.")
        if self.environment == "production" and any(not origin.startswith("https://") for origin in self.cors_origins):
            raise ValueError("Production origins must use HTTPS.")

    @classmethod
    def from_env(cls) -> "Settings":
        values = dotenv_values(Path(__file__).resolve().parents[1] / ".env", interpolate=False)

        def setting(name, default=None):
            return os.getenv(name, values.get(name) or default)
        default_dir = Path(__file__).resolve().parents[1] / "data"
        raw_origins = os.getenv("SMARTANALYTICS_CORS_ORIGINS",
                                "http://127.0.0.1:5173,http://localhost:5173")
        return cls(
            data_dir=Path(setting("SMARTANALYTICS_DATA_DIR", default_dir)).resolve(),
            max_upload_bytes=int(setting("SMARTANALYTICS_MAX_UPLOAD_BYTES", 20 * 1024 * 1024)),
            profile_cache_ttl_seconds=int(setting("PROFILE_CACHE_TTL_SECONDS", 600)),
            profile_cache_max_entries=int(setting("PROFILE_CACHE_MAX_ENTRIES", 8)),
            profile_cache_max_bytes=int(setting("PROFILE_CACHE_MAX_BYTES", 8 * 1024 * 1024)),
            cors_origins=tuple(origin.strip() for origin in setting(
                "SMARTANALYTICS_CORS_ORIGINS", raw_origins).split(",") if origin.strip()),
            database_url=setting("DATABASE_URL"), redis_url=setting("REDIS_URL"),
            rate_limit_namespace=setting("RATE_LIMIT_NAMESPACE", "smartanalytics"),
            session_ttl_seconds=int(setting("SESSION_TTL_SECONDS", 43200)),
            session_idle_seconds=int(setting("SESSION_IDLE_SECONDS", 1800)),
            login_limit=int(setting("AUTH_LOGIN_LIMIT", 10)),
            ai_user_minute_limit=int(setting("AI_USER_MINUTE_LIMIT", 10)),
            ai_user_daily_limit=int(setting("AI_USER_DAILY_LIMIT", 100)),
            environment=setting("APP_ENV", "development"),
            cookie_secure=setting("COOKIE_SECURE", "false" if setting(
                "APP_ENV", "development") == "development" else "true").lower() == "true",
            auto_migrate=setting("AUTO_MIGRATE", "true").lower() == "true",
            ai_input_usd_per_million=float(setting("AI_INPUT_USD_PER_MILLION")) if setting(
                "AI_INPUT_USD_PER_MILLION") else None,
            ai_output_usd_per_million=float(setting("AI_OUTPUT_USD_PER_MILLION")) if setting(
                "AI_OUTPUT_USD_PER_MILLION") else None,
        )

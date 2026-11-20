from __future__ import annotations
import hashlib
import secrets
import time
from contextlib import contextmanager
from threading import BoundedSemaphore
from uuid import uuid4

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from .db_models import User, UserSession
from .errors import ApiError

PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, type=Type.ID)
DUMMY_PASSWORD_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
HASH_SLOTS = BoundedSemaphore(4)


@contextmanager
def password_work():
    if not HASH_SLOTS.acquire(blocking=False):
        raise ApiError(429, "authentication_busy", "Authentication is busy. Please retry shortly.")
    try:
        yield
    finally:
        HASH_SLOTS.release()


def hash_password(value):
    with password_work():
        return PASSWORDS.hash(value)


def verify_password(encoded, value):
    with password_work():
        return PASSWORDS.verify(encoded, value)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_email(value):
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.casefold()
    except EmailNotValidError:
        raise ValueError("Enter a valid email address.") from None


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128, repr=False)

    @field_validator("email")
    @classmethod
    def email_address(cls, value):
        return normalize_email(value)


class Registration(Credentials):
    @field_validator("password")
    @classmethod
    def strong_password(cls, value):
        if len(value) < 15 or not all((any(c.islower() for c in value), any(c.isupper() for c in value), any(c.isdigit() for c in value), any(not c.isalnum() and not c.isspace() for c in value))):
            raise ValueError(
                "Use 15–128 characters including uppercase, lowercase, a number and a symbol.")
        return value


class PublicUser(BaseModel):
    id: str
    email: str


class SessionResponse(BaseModel):
    user: PublicUser | None
    csrf_token: str


class AuthService:
    def __init__(self, database, settings, limiter):
        self.database = database
        self.settings = settings
        self.limiter = limiter
        self.cookie_name = "__Host-smartanalytics_session" if settings.cookie_secure else "smartanalytics_session"

    def _ip(self, request):
        return request.client.host if request.client else "unknown"

    def _read_session(self, request):
        token = request.cookies.get(self.cookie_name, "")
        if not 40 <= len(token) <= 64:
            return None
        now = int(time.time())
        with self.database.session.begin() as db:
            record = db.scalar(select(UserSession).where(
                UserSession.token_hash == token_hash(token)).with_for_update())
            if record is None:
                return None
            if record.expires_at <= now or record.last_seen_at+self.settings.session_idle_seconds <= now:
                db.delete(record)
                return None
            if record.user_id:
                user = db.get(User, record.user_id)
                if user is None or not user.active:
                    db.delete(record)
                    return None
            record.last_seen_at = now
            return record

    def session(self, request):
        from sqlalchemy.orm.exc import StaleDataError
        try:
            return self._read_session(request)
        except StaleDataError:
            # A concurrent logout/expiry has already revoked this token.
            return None

    def csrf(self, request, record):
        if request.method in SAFE_METHODS:
            return
        if request.headers.get("origin") not in self.settings.cors_origins or request.headers.get("sec-fetch-site") == "cross-site":
            raise ApiError(403, "csrf_failed", "The request origin is not allowed.")
        supplied = request.headers.get("x-csrf-token", "")
        if record is None or not supplied.isascii() or not secrets.compare_digest(supplied, record.csrf_token):
            raise ApiError(403, "csrf_failed",
                           "The request could not be verified. Refresh your session and retry.")

    def require_user(self, request: Request) -> PublicUser:
        cached = getattr(request.state, "authenticated_user", None)
        if cached is not None:
            return cached
        record = self.session(request)
        if record is None or record.user_id is None:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        self.csrf(request, record)
        with self.database.session() as db:
            user = db.get(User, record.user_id)
            return PublicUser(id=user.id, email=user.email)

    def _issue(self, response, previous, user_id=None):
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        ttl = self.settings.session_ttl_seconds if user_id else min(
            1800, self.settings.session_ttl_seconds)
        record = UserSession(token_hash=token_hash(token), user_id=user_id, csrf_token=secrets.token_urlsafe(
            32), created_at=now, expires_at=now+ttl, last_seen_at=now)
        with self.database.session.begin() as db:
            if previous:
                db.execute(delete(UserSession).where(UserSession.token_hash == previous.token_hash))
            db.execute(delete(UserSession).where(UserSession.expires_at <= now))
            db.add(record)
        response.set_cookie(self.cookie_name, token, max_age=ttl, httponly=True,
                            secure=self.settings.cookie_secure, samesite="lax", path="/")
        return record

    def bootstrap(self, request, response):
        record = self.session(request)
        if record is None:
            self.limiter.hit("session_bootstrap", self._ip(request), 60, 60)
            record = self._issue(response, None)
        with self.database.session() as db:
            user = db.get(User, record.user_id) if record.user_id else None
            return SessionResponse(user=PublicUser(id=user.id, email=user.email) if user else None, csrf_token=record.csrf_token)

    def authenticate(self, request, response, credentials, register=False):
        previous = self.session(request)
        self.csrf(request, previous)
        self.limiter.hit("auth_ip", self._ip(request), 30, 60)
        self.limiter.hit("auth_email", credentials.email, self.settings.login_limit, 900)
        if register:
            self.limiter.hit("registration", self._ip(request), 5, 60)
            user = User(id=str(uuid4()), email=credentials.email, password_hash=hash_password(
                credentials.password), created_at=int(time.time()), active=True)
            try:
                with self.database.session.begin() as db:
                    db.add(user)
            except IntegrityError:
                raise ApiError(409, "registration_failed",
                               "Unable to register with these credentials.") from None
        else:
            with self.database.session() as db:
                user = db.scalar(select(User).where(User.email == credentials.email))
            try:
                valid = verify_password(
                    user.password_hash if user else DUMMY_PASSWORD_HASH, credentials.password)
            except (VerificationError, InvalidHashError):
                valid = False
            if not user or not user.active or not valid:
                raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
            if PASSWORDS.check_needs_rehash(user.password_hash):
                new_hash = hash_password(credentials.password)
                with self.database.session.begin() as db:
                    db.get(User, user.id).password_hash = new_hash
        record = self._issue(response, previous, user.id)
        return SessionResponse(user=PublicUser(id=user.id, email=user.email), csrf_token=record.csrf_token)

    def logout(self, request, response):
        record = self.session(request)
        if record is None or record.user_id is None:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        self.csrf(request, record)
        with self.database.session.begin() as db:
            db.execute(delete(UserSession).where(UserSession.token_hash == record.token_hash))
        response.delete_cookie(self.cookie_name, path="/",
                               secure=self.settings.cookie_secure, httponly=True, samesite="lax")


def auth_router(auth):
    router = APIRouter(prefix="/api/auth", tags=["authentication"])

    @router.get("/session", response_model=SessionResponse)
    @router.get("/csrf", response_model=SessionResponse)
    def bootstrap(request: Request, response: Response):
        return auth.bootstrap(request, response)

    @router.post("/register", response_model=SessionResponse, status_code=201)
    def register(body: Registration, request: Request, response: Response):
        return auth.authenticate(request, response, body, register=True)

    @router.post("/login", response_model=SessionResponse)
    def login(body: Credentials, request: Request, response: Response):
        return auth.authenticate(request, response, body)

    @router.get("/me", response_model=PublicUser)
    def me(request: Request):
        return auth.require_user(request)

    @router.post("/logout", status_code=204)
    def logout(request: Request, response: Response):
        auth.logout(request, response)

    return router

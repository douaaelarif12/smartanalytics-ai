"""Atomic fixed-window quotas shared through Redis or the relational database."""
import hashlib
import time
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from redis import Redis
from redis.exceptions import RedisError
from .db_models import RateCounter
from .errors import ApiError

LUA = """local n=redis.call('INCR', KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"""


class RateLimiter:
    def __init__(self, database, redis_url=None, namespace="smartanalytics"):
        self.database = database
        self.namespace = namespace
        self.redis = Redis.from_url(redis_url, socket_timeout=2,
                                    socket_connect_timeout=2) if redis_url else None

    def hit(self, category, subject, limit, seconds, code="rate_limited"):
        now = int(time.time())
        window = now // seconds * seconds
        key = category+":"+hashlib.sha256(subject.encode()).hexdigest()
        if self.redis:
            try:
                count = int(self.redis.eval(LUA, 1, f"{self.namespace}:{key}:{window}", seconds+1))
            except RedisError:
                raise ApiError(503, "limiter_unavailable",
                               "Request protection is unavailable. Please retry later.") from None
        else:
            insert = pg_insert if self.database.engine.dialect.name == "postgresql" else sqlite_insert
            statement = insert(RateCounter).values(key=key, window=window, hits=1)
            statement = statement.on_conflict_do_update(index_elements=[RateCounter.key], set_={"window": window, "hits": case(
                (RateCounter.window == window, RateCounter.hits+1), else_=1)}).returning(RateCounter.hits)
            with self.database.session.begin() as session:
                count = session.execute(statement).scalar_one()
        if count > limit:
            raise ApiError(429, code, "Too many requests. Please wait and try again.", {
                           "retry_after_seconds": seconds})

    def close(self):
        if self.redis:
            self.redis.close()

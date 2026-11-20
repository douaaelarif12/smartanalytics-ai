"""Real Redis only: opt in with SMARTANALYTICS_TEST_REDIS_URL. Never flush data."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from redis import Redis

from app.errors import ApiError
from app.limits import RateLimiter


@pytest.fixture
def real_limiters():
    url = os.getenv("SMARTANALYTICS_TEST_REDIS_URL")
    if not url:
        pytest.skip("Real Redis URL not supplied; no mock substituted")
    namespace = "sa-qa-" + uuid4().hex
    first = RateLimiter(None, url, namespace)
    second = RateLimiter(None, url, namespace)
    assert first.redis.ping()
    try:
        yield first, second
    finally:
        # Delete only the random namespace created by this fixture, never FLUSHDB.
        for key in first.redis.scan_iter(match=namespace + ":*"):
            first.redis.delete(key)
        first.close()
        second.close()


def test_real_redis_atomic_shared_quota(real_limiters):
    first, second = real_limiters
    def attempt(index):
        try:
            (first if index % 2 else second).hit("atomic", "user-a", 7, 3600)
            return True
        except ApiError as error:
            assert error.status_code == 429
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(24))) == 7


def test_real_redis_users_are_independent(real_limiters):
    first, second = real_limiters
    first.hit("ai", "user-a", 1, 60)
    second.hit("ai", "user-b", 1, 60)
    with pytest.raises(ApiError) as error:
        second.hit("ai", "user-a", 1, 60)
    assert error.value.status_code == 429


def test_real_redis_reconnecting_preserves_quota(real_limiters):
    first, second = real_limiters
    first.hit("login", "user-a", 1, 3600)
    first.redis.connection_pool.disconnect()
    with pytest.raises(ApiError):
        second.hit("login", "user-a", 1, 3600)


def test_real_redis_window_expires(real_limiters):
    first, second = real_limiters
    first.hit("expiry", "user-a", 1, 1)
    keys = list(first.redis.scan_iter(match=first.namespace + ":*"))
    assert len(keys) == 1
    assert 0 < first.redis.ttl(keys[0]) <= 2
    time.sleep(2.1)
    assert not first.redis.exists(keys[0])
    second.hit("expiry", "user-a", 1, 1)


def test_real_redis_namespaces_do_not_interfere(real_limiters):
    first, second = real_limiters
    first.hit("scope", "user-a", 1, 60)
    isolated = RateLimiter(None, os.environ["SMARTANALYTICS_TEST_REDIS_URL"], first.namespace + "-other")
    try:
        isolated.hit("scope", "user-a", 1, 1)
    finally:
        for key in isolated.redis.scan_iter(match=isolated.namespace + ":*"):
            isolated.redis.delete(key)
        isolated.close()


def test_real_redis_unavailable_fails_closed(real_limiters):
    first, second = real_limiters
    # An intentionally wrong password exercises an actual rejected AUTH, not a mock.
    from redis.connection import parse_url
    options = parse_url(os.environ["SMARTANALYTICS_TEST_REDIS_URL"])
    options["password"] = uuid4().hex
    first.redis.close()
    first.redis = Redis(**options, socket_timeout=2, socket_connect_timeout=2)
    with pytest.raises(ApiError) as error:
        first.hit("failure", "user-a", 1, 60)
    assert error.value.status_code == 503
    # Restore authorized client so fixture cleanup can access its own namespace.
    first.redis.close()
    first.redis = Redis.from_url(os.environ["SMARTANALYTICS_TEST_REDIS_URL"])
